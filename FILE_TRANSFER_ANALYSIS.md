# 文件上传和下载传输方式分析

## 一、文件上传方式

### 1. 翻译任务文件上传

#### 前端实现
- **位置**: `collabtrans/static/index.html` (第4014-4022行)
- **传输方式**: `multipart/form-data`
- **实现代码**:
```javascript
const formData = new FormData();
formData.append('file', state.file);  // 文件二进制内容
formData.append('payload', JSON.stringify(payload));  // JSON字符串格式的工作流参数

const response = await fetch('/service/translate', {
    method: 'POST',
    // 不设置Content-Type头，浏览器会自动设置multipart/form-data和boundary
    body: formData
});
```

#### 后端实现
- **位置**: `collabtrans/app.py` (第1975-1989行)
- **接收方式**: FastAPI的`multipart/form-data`解析
- **处理流程**:
  1. 检测Content-Type是否为`multipart/form-data`
  2. 使用`await request.form()`解析表单数据
  3. 从表单中提取`file`和`payload`字段
  4. 使用`await file.read()`读取文件二进制内容
  5. 解析JSON格式的`payload`字符串

#### 兼容性支持
- **Legacy格式**: 支持`application/json`格式（Base64编码）
  - 位置: `collabtrans/app.py` (第2042-2054行)
  - 格式: `{"file_name": "...", "file_content": "base64...", "payload": {...}}`

### 2. 词汇表上传

#### 前端实现
- **位置**: `collabtrans/static/settings/glossary.js` (第203-216行)
- **传输方式**: `multipart/form-data`
- **字段**:
  - `name`: 词汇表名称
  - `file`: CSV文件
  - `description`: 描述（可选）
  - `is_global`: 是否全局词汇表

#### 后端实现
- **位置**: `collabtrans/auth/routes.py` (第872-886行)
- **处理**: 读取文件内容，解析CSV格式

### 3. 提示词上传

#### 前端实现
- **位置**: `collabtrans/static/index.html` (第5652-5663行, 第5693-5703行)
- **传输方式**: `multipart/form-data`
- **字段**:
  - `name`: 提示词名称
  - `file`: JSON文件
  - `description`: 描述（可选）
  - `is_global`: 是否全局提示词

#### 后端实现
- **位置**: `collabtrans/auth/routes.py` (第1159-1174行)
- **处理**: 读取文件内容，解析JSON格式

## 二、文件下载方式

### 1. 翻译结果文件下载

#### 方式一：直接文件流下载（推荐）

**前端实现**:
- **位置**: `collabtrans/static/index.html` (第4252行)
- **方式**: 使用`<a>`标签的`href`属性直接链接到下载端点
- **实现**:
```javascript
a.href = downloads[key];  // 例如: /service/download/{task_id}/{file_type}
```

**后端实现**:
- **位置**: `collabtrans/app.py` (第2326-2345行)
- **端点**: `GET /service/download/{task_id}/{file_type}`
- **返回类型**: `FileResponse`
- **Content-Type**: `application/octet-stream`
- **特点**:
  - 使用FastAPI的`FileResponse`类
  - 自动设置`Content-Disposition`头指定文件名
  - 支持流式传输，适合大文件
  - 直接从临时文件系统读取文件

#### 方式二：Base64编码JSON返回

**前端实现**:
- **位置**: 通过API调用获取内容
- **端点**: `/service/content/{task_id}/{file_type}`

**后端实现**:
- **位置**: `collabtrans/app.py` (第2427-2454行)
- **返回格式**: JSON
```json
{
    "file_type": "html",
    "filename": "my_doc_translated.html",
    "content": "PGh0bWw+PGhlYWQ+..."  // Base64编码的文件内容
}
```
- **特点**:
  - 适合需要在前端处理文件内容的场景
  - 需要客户端进行Base64解码
  - 不适合大文件（内存占用高）

### 2. 附件文件下载

**后端实现**:
- **位置**: `collabtrans/app.py` (第2362-2381行)
- **端点**: `GET /service/attachment/{task_id}/{identifier}`
- **返回类型**: `FileResponse`
- **Content-Type**: `application/octet-stream`
- **用途**: 下载翻译过程中生成的附件（如自动生成的词汇表）

### 3. 词汇表下载

**后端实现**:
- **位置**: `collabtrans/auth/routes.py` (第934-976行)
- **端点**: `GET /auth/glossaries/download/{glossary_id}`
- **返回类型**: `FileResponse`
- **Content-Type**: `text/csv` 或 `application/octet-stream`

### 4. 提示词下载

**后端实现**:
- **位置**: `collabtrans/auth/routes.py` (第1216-1266行)
- **端点**: `GET /auth/prompts/download/{prompt_id}`
- **返回类型**: `FileResponse`
- **Content-Type**: `application/json` 或 `application/octet-stream`

## 三、传输方式总结

### 上传方式
| 功能 | 传输方式 | Content-Type | 数据格式 |
|------|---------|--------------|----------|
| 翻译任务文件 | multipart/form-data | 自动设置（含boundary） | 二进制文件 + JSON字符串 |
| 词汇表上传 | multipart/form-data | 自动设置 | CSV文件 + 表单字段 |
| 提示词上传 | multipart/form-data | 自动设置 | JSON文件 + 表单字段 |
| Legacy格式 | application/json | application/json | Base64编码的文件内容 |

### 下载方式
| 功能 | 传输方式 | Content-Type | 数据格式 |
|------|---------|--------------|----------|
| 翻译结果文件（流式） | HTTP GET | application/octet-stream | 二进制文件流 |
| 翻译结果内容（JSON） | HTTP GET | application/json | Base64编码的JSON |
| 附件文件 | HTTP GET | application/octet-stream | 二进制文件流 |
| 词汇表下载 | HTTP GET | text/csv 或 application/octet-stream | CSV文件流 |
| 提示词下载 | HTTP GET | application/json 或 application/octet-stream | JSON文件流 |

## 四、技术特点

### 上传特点
1. **multipart/form-data优势**:
   - 支持大文件上传
   - 浏览器自动处理boundary
   - 无需手动编码
   - 内存效率高（流式处理）

2. **文件存储**:
   - 上传后立即写入临时目录
   - 临时目录路径: `tempfile.mkdtemp(prefix=f"collabtrans_{task_id}_")`
   - 文件路径: `{temp_dir}/{original_filename}`

### 下载特点
1. **FileResponse优势**:
   - 自动处理文件流
   - 支持大文件下载
   - 自动设置HTTP头（Content-Disposition, Content-Length等）
   - 内存效率高（流式传输）

2. **Base64 JSON方式**:
   - 适合小文件
   - 便于前端直接处理
   - 不适合大文件（内存占用高）

## 五、性能考虑

### 上传性能
- ✅ 使用multipart/form-data，支持流式处理
- ✅ 文件直接写入磁盘，不占用大量内存
- ✅ 支持异步处理（FastAPI async）

### 下载性能
- ✅ 使用FileResponse流式传输，适合大文件
- ✅ 直接从文件系统读取，无需加载到内存
- ⚠️ Base64 JSON方式仅适合小文件

## 六、安全性

### 上传安全
- ✅ 文件类型验证（通过workflow_type）
- ✅ 文件大小限制（可通过Web服务器配置）
- ✅ 临时文件自动清理

### 下载安全
- ✅ 任务ID验证
- ✅ 文件存在性检查
- ✅ 临时文件自动清理

## 七、改进建议

1. **大文件上传**:
   - 考虑添加分块上传支持
   - 添加上传进度显示

2. **下载优化**:
   - 考虑添加断点续传支持
   - 添加下载进度显示

3. **错误处理**:
   - 增强文件大小限制的错误提示
   - 增强文件类型验证的错误提示

