## XLSX 翻译内存优化方案（方案 A 实现说明）

### 1. 背景问题

- 原实现中，`XlsxTranslator._pre_translate` 使用：
  - `openpyxl.load_workbook(BytesIO(document.content))` 以可写模式完整载入工作簿；
  - 遍历所有单元格（或区域）时，openpyxl 会在内存中构建完整 DOM，并在访问 `cell.value` 时进一步展开内部结构。
- 对于一个约 10MB 的 `.xlsx` 文件（约 13140 个可翻译单元格），在调试日志中观测到：
  - `app: after read_bytes`：约 126.9 MB（含进程基础占用 + 原始文件）；
  - `xlsx: after load_workbook`：约 1.5 GB；
  - `xlsx: after collecting cells`：约 27 GB；
  - 进程随后被 OOM killer 杀死。

问题本质：**单次任务在“载入 + 收集单元格”阶段就产生了约 27GB 峰值内存**。

### 2. 目标

1. 降低「收集单元格」阶段的内存占用，从几十 GB 降到百 MB 级；
2. 保持现有接口不变（调用者仍通过 `translate` / `translate_async` 使用）；
3. 尽量不牺牲写回阶段的正确性（仍使用 openpyxl 写回，以保留原有格式和公式）。

### 3. 核心思路（方案 A）

**读写分离**：

1. **读阶段（低内存）**：
   - 使用 `openpyxl.load_workbook(..., read_only=True, data_only=True)` 打开工作簿；
   - 仅用于 **一次性扫描**，收集需要翻译的单元格坐标和原文；
   - 扫描完成后立刻 `close()`，不持有 workbook 对象。
2. **翻译阶段**：
   - 在内存中只保留：
     - `cells_to_translate`: `{"sheet_name": str, "coordinate": str}` 列表；
     - `original_texts`: 原文字段列表（与 `cells_to_translate` 一一对应）；
     - 翻译过程中产生的 prompt、结果等。
3. **写回阶段（可写一次）**：
   - 使用 `openpyxl.load_workbook(BytesIO(document.content))` 再次以可写模式打开原始文档；
   - 根据 `cells_to_translate` 和 `translated_texts` 定位并写回翻译结果；
   - 保存到临时 `.xlsx` 文件，再读回 bytes，最后关闭 workbook 并删除临时文件。

这样：

- 读阶段的峰值内存主要由 `document.content` + 两个 Python 列表决定，量级在几十 MB；
- 写回阶段峰值主要是一次完整的 workbook 对象（对 10MB 文件约 1.5GB）+ 结果 bytes；
- 相比原来的 27GB 峰值，**整体峰值约为 1.5–2GB**。

### 4. 代码实现要点

#### 4.1 `_pre_translate`：仅返回坐标和原文（使用 read_only）

文件：`collabtrans/translator/ai_translator/xlsx_translator.py`

- 旧签名：
  - `def _pre_translate(self, document: Document): -> (workbook, cells_to_translate, original_texts)`
- 新签名：
  - `def _pre_translate(self, document: Document): -> (cells_to_translate, original_texts)`

关键变化：

- 使用 `read_only=True, data_only=True`：
  - 避免构建完整 DOM；
  - 访问 `cell.value` 时，对内存的影响远小于可写模式。
- 收集逻辑保持不变：
  - 无 `translate_regions` 时：扫描所有 sheet 的所有字符串单元格；
  - 有 `translate_regions` 时：仅按照指定区域扫描，并通过 `processed_coordinates` 去重。
- 立即 `workbook.close()` 并返回 `cells_to_translate` 与 `original_texts`。

#### 4.2 `_after_translate`：写回时重新打开 workbook

- 新签名：
  - `def _after_translate(self, document: Document, cells_to_translate, translated_texts, original_texts) -> bytes`
- 实现：
  1. 使用 `openpyxl.load_workbook(BytesIO(document.content))` 打开原始 xlsx（可写模式）；
  2. 根据 `cells_to_translate` 中的 `sheet_name` 和 `coordinate` 定位单元格；
  3. 按 `insert_mode` 写回翻译结果（替换 / 追加 / 前置）；
  4. 保存到 `tempfile.mkstemp(suffix=".xlsx")` 创建的临时文件；
  5. 读回该文件的 bytes 作为结果，关闭 workbook 并删除临时文件。

#### 4.3 `translate` / `translate_async`：调用方式调整

- 调用 `_pre_translate` 时只拿到 `(cells_to_translate, original_texts)`；
- 翻译逻辑（glossary、send_segments 等）保持不变；
- 写回时调用：
  - 同步：`document.content = self._after_translate(document, cells_to_translate, translated_texts, original_texts)`
  - 异步：`document.content = await asyncio.to_thread(self._after_translate, document, cells_to_translate, translated_texts, original_texts)`

注意：为保证写回时能重新打开 workbook，**不再在 `_pre_translate` 后清空 `document.content`**。

### 5. 内存日志与验证

为便于后续分析内存使用情况，在关键步骤添加了 INFO 级别的内存日志（使用 `log_memory`）：

- `app: after read_bytes`：读入原始文件后；
- `xlsx: after load_workbook (read_only)`：读阶段打开 read_only workbook 后；
- `xlsx: after collecting cells (read_only)`：完成单元格收集后；
- `xlsx: before/after send_segments_async`：翻译前后；
- `xlsx: _after_translate load_workbook (writable)` / `xlsx: after _after_translate`：写回阶段加载和保存后。

