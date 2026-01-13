# DOCX 格式感知分片方案

## 概述

本方案旨在在 DOCX 翻译流程中实现格式感知的精细分片，确保翻译后能够保留原始文本的格式属性（字号、颜色、粗体、斜体等）。

## 设计目标

1. **精细分片**：根据格式差异（字号、颜色、粗体/常规等）进行分片
2. **格式记录**：完整记录每个分片的格式信息
3. **格式保留**：翻译后导出时，将格式属性应用到译文

## 技术方案

### 1. 格式信息数据结构

```python
@dataclass
class RunFormatInfo:
    """Run 格式信息"""
    font_name: str | None = None
    font_size: int | None = None  # 单位：磅 (Pt)
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    color_rgb: str | None = None  # RGB 颜色值，格式："RRGGBB"
    highlight_color: str | None = None  # 高亮颜色
    strikethrough: bool | None = None
    
    def __eq__(self, other) -> bool:
        """比较两个格式信息是否相同（用于分片判断）"""
        if not isinstance(other, RunFormatInfo):
            return False
        return (
            self.font_name == other.font_name and
            self.font_size == other.font_size and
            self.bold == other.bold and
            self.italic == other.italic and
            self.underline == other.underline and
            self.color_rgb == other.color_rgb and
            self.highlight_color == other.highlight_color and
            self.strikethrough == other.strikethrough
        )
    
    def __hash__(self) -> int:
        """用于字典键"""
        return hash((
            self.font_name, self.font_size, self.bold, self.italic,
            self.underline, self.color_rgb, self.highlight_color, self.strikethrough
        ))
```

### 2. 格式提取函数

```python
def extract_run_format(run: Run) -> RunFormatInfo:
    """从 Run 对象提取格式信息"""
    font = run.font
    
    # 提取颜色（RGB）
    color_rgb = None
    if font.color and font.color.rgb:
        color_rgb = str(font.color.rgb)
    
    # 提取高亮颜色（对不被 python-docx 支持的值做兼容处理，例如 w:val="none"）
    highlight_color = None
    if hasattr(font, 'highlight_color'):
        try:
            if font.highlight_color:
                highlight_color = str(font.highlight_color)
        except ValueError as e:
            # 例如：WD_COLOR_INDEX has no XML mapping for 'none'
            # 这类问题只影响高亮效果，不影响正文内容，安全忽略
            pass
    
    return RunFormatInfo(
        font_name=font.name,
        font_size=font.size.pt if font.size else None,
        bold=font.bold,
        italic=font.italic,
        underline=font.underline,
        color_rgb=color_rgb,
        highlight_color=highlight_color,
        strikethrough=font.strike if hasattr(font, 'strike') else None
    )
```

### 3. 格式感知分片逻辑

```python
def process_paragraph_format_aware(para: Paragraph):
    """格式感知的段落处理"""
    elements_to_translate = []
    original_texts = []
    
    current_text_segment = ""
    current_runs = []
    current_format: RunFormatInfo | None = None
    
    for run in para.runs:
        if is_image_run(run):
            # 遇到图片，结束当前分片
            if current_text_segment.strip():
                elements_to_translate.append({
                    "type": "text_runs",
                    "runs": current_runs,
                    "format": current_format  # 记录格式信息
                })
                original_texts.append(current_text_segment)
            # 重置
            current_text_segment = ""
            current_runs = []
            current_format = None
        else:
            # 提取当前 run 的格式
            run_format = extract_run_format(run)
            
            # 判断是否需要分片
            # 条件：格式发生变化 或 当前分片为空
            if current_format is None:
                # 第一个 run，开始新分片
                current_format = run_format
                current_runs.append(run)
                current_text_segment += run.text
            elif current_format == run_format:
                # 格式相同，继续累积
                current_runs.append(run)
                current_text_segment += run.text
            else:
                # 格式不同，结束当前分片，开始新分片
                if current_text_segment.strip():
                    elements_to_translate.append({
                        "type": "text_runs",
                        "runs": current_runs,
                        "format": current_format
                    })
                    original_texts.append(current_text_segment)
                
                # 开始新分片
                current_format = run_format
                current_runs = [run]
                current_text_segment = run.text
    
    # 处理最后一个分片
    if current_text_segment.strip():
        elements_to_translate.append({
            "type": "text_runs",
            "runs": current_runs,
            "format": current_format
        })
        original_texts.append(current_text_segment)
    
    return elements_to_translate, original_texts
```

### 4. 格式应用函数

```python
def apply_format_to_run(run: Run, format_info: RunFormatInfo, target_font_name: str | None = None):
    """将格式信息应用到 Run 对象"""
    font = run.font
    
    # 应用字体名称（优先使用目标语言字体，如果未指定则使用原始字体）
    if target_font_name:
        font.name = target_font_name
    elif format_info.font_name:
        font.name = format_info.font_name
    
    # 应用字号
    if format_info.font_size:
        from docx.shared import Pt
        font.size = Pt(format_info.font_size)
    
    # 应用粗体
    if format_info.bold is not None:
        font.bold = format_info.bold
    
    # 应用斜体
    if format_info.italic is not None:
        font.italic = format_info.italic
    
    # 应用下划线
    if format_info.underline is not None:
        font.underline = format_info.underline
    
    # 应用颜色
    if format_info.color_rgb:
        from docx.shared import RGBColor
        try:
            # 解析 RGB 颜色字符串（格式："RRGGBB" 或 "RGBColor(r, g, b)"）
            if format_info.color_rgb.startswith("RGBColor"):
                # 从 "RGBColor(r, g, b)" 提取
                import re
                match = re.search(r'RGBColor\((\d+),\s*(\d+),\s*(\d+)\)', format_info.color_rgb)
                if match:
                    r, g, b = map(int, match.groups())
                    font.color.rgb = RGBColor(r, g, b)
            else:
                # 从 "RRGGBB" 格式提取
                if len(format_info.color_rgb) == 6:
                    r = int(format_info.color_rgb[0:2], 16)
                    g = int(format_info.color_rgb[2:4], 16)
                    b = int(format_info.color_rgb[4:6], 16)
                    font.color.rgb = RGBColor(r, g, b)
        except Exception as e:
            logger.warning(f"Failed to apply color {format_info.color_rgb}: {e}")
    
    # 应用高亮颜色
    if format_info.highlight_color:
        try:
            from docx.enum.text import WD_COLOR_INDEX
            # 尝试解析高亮颜色
            if hasattr(font, 'highlight_color'):
                # 这里需要根据实际的高亮颜色格式进行解析
                pass
        except Exception as e:
            logger.warning(f"Failed to apply highlight color: {e}")
    
    # 应用删除线
    if format_info.strikethrough is not None:
        if hasattr(font, 'strike'):
            font.strike = format_info.strikethrough
```

### 5. 导出阶段格式应用

```python
def _after_translate_format_aware(
    self, 
    doc: DocumentObject, 
    elements_to_translate: List[Dict[str, Any]],
    translated_texts: List[str], 
    original_texts: List[str]
) -> bytes:
    """格式感知的导出函数"""
    translation_map = dict(zip(original_texts, translated_texts))
    
    # 获取目标语言字体（用于字体兼容性）
    target_font_name = get_font_for_language(self.config.to_lang)
    
    for i, element_info in enumerate(elements_to_translate):
        runs = element_info["runs"]
        format_info: RunFormatInfo = element_info.get("format")
        original_text = original_texts[i]
        translated_text = translated_texts[i]
        
        # 确定最终文本（根据 insert_mode）
        if self.insert_mode == "replace":
            final_text = translated_text
        elif self.insert_mode == "append":
            final_text = original_text + self.separator + translated_text
        elif self.insert_mode == "prepend":
            final_text = translated_text + self.separator + original_text
        else:
            final_text = translated_text
        
        if not runs:
            continue
        
        # 策略：将翻译文本分配到各个 run，保持格式
        # 如果只有一个 run，直接替换
        if len(runs) == 1:
            first_run = runs[0]
            preserve_page_breaks_in_run(first_run, final_text)
            if format_info:
                apply_format_to_run(first_run, format_info, target_font_name)
        else:
            # 多个 run 的情况：需要智能分配文本
            # 方案1：将文本全部放入第一个 run，其他 run 清空
            first_run = runs[0]
            preserve_page_breaks_in_run(first_run, final_text)
            if format_info:
                apply_format_to_run(first_run, format_info, target_font_name)
            
            # 清空其他 run（保留结构）
            for run in runs[1:]:
                run.text = ""
                # 可选：也应用格式（保持一致性）
                if format_info:
                    apply_format_to_run(run, format_info, target_font_name)
    
    # 保存文档
    doc_output_stream = BytesIO()
    doc.save(doc_output_stream)
    return doc_output_stream.getvalue()
```

## 实现步骤

### 阶段 1：数据结构定义
1. 创建 `RunFormatInfo` 数据类
2. 实现格式比较和哈希方法

### 阶段 2：格式提取
1. 实现 `extract_run_format()` 函数
2. 处理各种格式属性的提取（包括 None 值处理）

### 阶段 3：格式感知分片
1. 修改 `_pre_translate()` 方法
2. 使用 `process_paragraph_format_aware()` 替代原有的段落处理逻辑
3. 在 `elements_to_translate` 中存储格式信息

### 阶段 4：格式应用
1. 实现 `apply_format_to_run()` 函数
2. 修改 `_after_translate()` 方法，使用格式感知的导出逻辑
3. 处理字体兼容性（目标语言字体 + 原始格式）

### 阶段 5：测试和优化
1. 测试各种格式组合（字号、颜色、粗体等）
2. 测试边界情况（None 值、默认格式等）
3. 性能优化（避免不必要的格式比较）

## 注意事项

### 1. 字体兼容性
- 优先使用目标语言字体（`get_font_for_language()`）
- 如果目标字体不支持某些字符，保留原始字体作为备选
- 考虑字体回退机制

### 2. 颜色格式
- RGB 颜色可能有多种表示格式，需要统一处理
- 处理颜色为 None 的情况（使用默认颜色）

### 3. 格式继承
- 某些格式可能从段落样式继承，需要检查段落级别的格式
- 考虑处理格式冲突（如粗体和斜体同时存在）

### 4. 性能考虑
- 格式比较可能影响性能，考虑缓存格式信息
- 对于大量相同格式的 run，可以批量处理

### 5. 向后兼容
- 保持与现有代码的兼容性
- 如果格式信息缺失，使用默认行为（当前逻辑）

## 扩展功能（可选）

### 1. 段落级别格式
- 记录段落对齐方式、缩进等
- 在导出时应用段落格式

### 2. 表格单元格格式
- 扩展格式提取到表格单元格
- 保留单元格背景色、边框等

### 3. 样式映射
- 支持自定义格式映射规则
- 例如：将特定颜色映射到目标语言的对应颜色

## 文件修改清单

1. **`collabtrans/translator/ai_translator/docx_translator.py`**
   - 添加 `RunFormatInfo` 数据类
   - 添加 `extract_run_format()` 函数
   - 修改 `_pre_translate()` 方法
   - 添加 `apply_format_to_run()` 函数
   - 修改 `_after_translate()` 方法

2. **测试文件**（新建）
   - `tests/test_docx_format_aware.py`
   - 测试各种格式组合
   - 测试格式保留功能

## 预期效果

实现后，翻译 DOCX 文件时：
- ✅ 不同格式的文本会被分到不同的分片
- ✅ 格式信息（字号、颜色、粗体等）会被完整记录
- ✅ 翻译后的文本会保留原始格式属性
- ✅ 字体会根据目标语言自动调整，同时保留其他格式属性
