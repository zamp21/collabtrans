import asyncio
import base64
import io
import logging
import os
import socket
import time
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, APIRouter, Body, Path as FastApiPath
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from docutranslate import FileTranslater, __version__
from docutranslate.global_values import available_packages
from docutranslate.logger import translater_logger
from docutranslate.translater import default_params
from docutranslate.utils.resource_utils import resource_path

# --- 全局配置 ---
tasks_state: Dict[str, Dict[str, Any]] = {}
tasks_log_queues: Dict[str, asyncio.Queue] = {}
tasks_log_histories: Dict[str, List[str]] = {}
MAX_LOG_HISTORY = 200
httpx_client: httpx.AsyncClient


# --- 辅助函数 ---
def _create_default_task_state() -> Dict[str, Any]:
    return {
        "is_processing": False, "status_message": "空闲", "error_flag": False,
        "download_ready": False, "markdown_content": None, "markdown_zip_content": None,
        "html_content": None, "original_filename_stem": None, "task_start_time": 0,
        "task_end_time": 0, "current_task_ref": None,
        "original_filename": None,
    }


# --- 日志处理器 (无修改) ---
class QueueAndHistoryHandler(logging.Handler):
    def __init__(self, queue_ref: asyncio.Queue, history_list_ref: List[str], max_history_items: int):
        super().__init__()
        self.queue = queue_ref
        self.history_list = history_list_ref
        self.max_history = max_history_items

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        task_id_prefix = f"[{record.task_id}] " if hasattr(record, 'task_id') else ""
        print(f"{task_id_prefix}{log_entry}")
        self.history_list.append(log_entry)
        if len(self.history_list) > self.max_history:
            del self.history_list[:len(self.history_list) - self.max_history]
        if self.queue is not None:
            try:
                main_loop = getattr(app.state, "main_event_loop", None)
                if main_loop and main_loop.is_running():
                    main_loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
                else:
                    self.queue.put_nowait(log_entry)
            except asyncio.QueueFull:
                print(f"Log queue is full for task. Log dropped: {log_entry}")
            except Exception as e:
                print(f"Error putting log to queue for task: {e}. Log: {log_entry}")


# --- 应用生命周期事件 ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global httpx_client
    app.state.main_event_loop = asyncio.get_running_loop()
    httpx_client = httpx.AsyncClient()
    tasks_state.clear()
    tasks_log_queues.clear()
    tasks_log_histories.clear()
    for handler in translater_logger.handlers[:]:
        translater_logger.removeHandler(handler)
    translater_logger.propagate = False
    translater_logger.setLevel(logging.INFO)
    print("应用启动完成，多任务状态已初始化。")
    yield
    await httpx_client.aclose()
    print("应用关闭，资源已清理。")


# --- Background Task Logic (核心业务逻辑, 仅由服务层调用) ---
async def _perform_translation(task_id: str, params: Dict[str, Any], file_contents: bytes, original_filename: str):
    task_state = tasks_state[task_id]
    log_queue = tasks_log_queues[task_id]
    log_history = tasks_log_histories[task_id]
    task_handler = QueueAndHistoryHandler(log_queue, log_history, MAX_LOG_HISTORY)
    task_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    log_filter = logging.Filter()
    log_filter.task_id = task_id
    task_handler.addFilter(log_filter)
    translater_logger.addHandler(task_handler)

    translater_logger.info(f"后台翻译任务开始: 文件 '{original_filename}'")
    task_state["status_message"] = f"正在处理 '{original_filename}'..."
    try:
        translater_logger.info(f"使用 Base URL: {params['base_url']}, Model: {params['model_id']}")
        ft = FileTranslater(
            base_url=params['base_url'], key=params['apikey'], model_id=params['model_id'],
            chunk_size=params['chunk_size'], concurrent=params['concurrent'],
            temperature=params['temperature'], convert_engin=params['convert_engin'],
            mineru_token=params['mineru_token'],
        )
        await ft.translate_bytes_async(
            name=original_filename, file=file_contents, to_lang=params['to_lang'],
            formula=params['formula_ocr'], code=params['code_ocr'],
            custom_prompt_translate=params['custom_prompt_translate'],
            refine=params['refine_markdown'], save=False
        )
        md_content = ft.export_to_markdown()
        md_zip_content = ft.export_to_unembed_markdown()
        try:
            await httpx_client.head("https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js",
                                    timeout=3)
            html_content = ft.export_to_html(title=task_state["original_filename_stem"], cdn=True)
        except (httpx.TimeoutException, httpx.RequestError):
            translater_logger.info("CDN连接失败，使用本地JS进行渲染。")
            html_content = ft.export_to_html(title=task_state["original_filename_stem"], cdn=False)
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        task_state.update({
            "markdown_content": md_content, "markdown_zip_content": md_zip_content,
            "html_content": html_content, "status_message": f"翻译成功！用时 {duration:.2f} 秒。",
            "download_ready": True, "error_flag": False, "task_end_time": end_time,
        })
        translater_logger.info(f"翻译成功完成，用时 {duration:.2f} 秒。")
    except asyncio.CancelledError:
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        translater_logger.info(f"翻译任务 '{original_filename}' 已被取消 (用时 {duration:.2f} 秒).")
        task_state.update({
            "status_message": f"翻译任务已取消 (用时 {duration:.2f} 秒).", "error_flag": False,
            "download_ready": False, "markdown_content": None, "md_zip_content": None,
            "html_content": None, "task_end_time": end_time,
        })
    except Exception as e:
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        error_message = f"翻译失败: {e}"
        translater_logger.error(error_message, exc_info=True)
        task_state.update({
            "status_message": f"翻译过程中发生错误 (用时 {duration:.2f} 秒): {e}",
            "error_flag": True, "download_ready": False, "markdown_content": None,
            "md_zip_content": None, "html_content": None, "task_end_time": end_time,
        })
    finally:
        task_state["is_processing"] = False
        task_state["current_task_ref"] = None
        translater_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")
        translater_logger.removeHandler(task_handler)


# --- 核心任务启动与取消逻辑 (仅由服务层调用) ---
async def _start_translation_task(
        task_id: str,
        params: Dict[str, Any],
        file_contents: bytes,
        original_filename: str
):
    if task_id not in tasks_state:
        tasks_state[task_id] = _create_default_task_state()
        tasks_log_queues[task_id] = asyncio.Queue()
        tasks_log_histories[task_id] = []
    task_state = tasks_state[task_id]

    if task_state["is_processing"] and task_state["current_task_ref"] and not task_state["current_task_ref"].done():
        raise HTTPException(status_code=429, detail=f"任务ID '{task_id}' 正在进行中，请稍后再试。")

    task_state["is_processing"] = True
    task_state.update({
        "status_message": "任务初始化中...", "error_flag": False, "download_ready": False,
        "markdown_content": None, "md_zip_content": None, "html_content": None,
        "original_filename_stem": Path(original_filename).stem,
        "original_filename": original_filename,
        "task_start_time": time.time(), "task_end_time": 0, "current_task_ref": None,
    })

    log_history = tasks_log_histories[task_id]
    log_queue = tasks_log_queues[task_id]
    log_history.clear()
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    initial_log_msg = f"收到新的翻译请求: {original_filename}"
    print(f"[{task_id}] {initial_log_msg}")
    log_history.append(initial_log_msg)
    await log_queue.put(initial_log_msg)

    try:
        loop = asyncio.get_running_loop()
        task = loop.create_task(_perform_translation(task_id, params, file_contents, original_filename))
        task_state["current_task_ref"] = task
        return {"task_started": True, "task_id": task_id, "message": "翻译任务已成功启动，请稍候..."}
    except Exception as e:
        task_state.update({"is_processing": False, "status_message": f"启动任务失败: {e}", "error_flag": True,
                           "current_task_ref": None})
        raise HTTPException(status_code=500, detail=f"启动翻译任务时出错: {e}")


def _cancel_translation_logic(task_id: str):
    task_state = tasks_state.get(task_id)
    if not task_state or not task_state["is_processing"] or not task_state["current_task_ref"]:
        raise HTTPException(status_code=400, detail=f"任务ID '{task_id}' 没有正在进行的翻译任务可取消。")

    task_to_cancel: Optional[asyncio.Task] = task_state["current_task_ref"]
    if not task_to_cancel or task_to_cancel.done():
        task_state["is_processing"] = False
        task_state["current_task_ref"] = None
        raise HTTPException(status_code=400, detail="任务已完成或已被取消。")

    print(f"[{task_id}] 收到取消翻译任务的请求。")
    task_to_cancel.cancel()
    task_state["status_message"] = "正在取消任务..."
    return {"cancelled": True, "message": "取消请求已发送。请等待状态更新。"}


# --- FastAPI 应用和路由设置 ---
tags_metadata = [
    {
        "name": "Service API",
        "description": "核心的服务API，用于提交、管理和下载翻译任务。",
    },
    {
        "name": "Application",
        "description": "应用本身的相关端点，如元信息和默认参数。",
    },
    {
        "name": "Temp",
        "description": "测试用接口。",
    },
]

app = FastAPI(
    lifespan=lifespan,
    title="DocuTranslate API",
    description=f"""
DocuTranslate 后端服务 API，提供文档翻译、状态查询、结果下载等功能。

### 主要工作流程:
1.  **POST /service/translate**: 提交文件和翻译参数，启动一个后台任务，并获取 `task_id`。
2.  **GET /service/status/{{task_id}}**: 使用 `task_id` 轮询此端点，获取任务的实时状态。
3.  **GET /service/logs/{{task_id}}**: (可选) 获取实时的翻译日志。
4.  **GET /service/download/{{task_id}}/{{file_type}}**: 任务完成后 (当 `download_ready` 为 `true` 时)，通过此端点下载结果文件。

**版本**: {__version__}
""",
    version=__version__,
    openapi_tags=tags_metadata,
)

service_router = APIRouter(prefix="/service", tags=["Service API"])

STATIC_DIR = resource_path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===================================================================
# --- Pydantic Models for Service API ---
# ===================================================================
class TranslateServiceRequest(BaseModel):
    task_id: str = Field(
        "0",
        description="任务的唯一标识符。用于后续跟踪任务状态和结果。默认为 '0'，表示单个任务模式。建议为每个任务提供唯一的ID，例如UUID。",
        examples=["task-12345"]
    )
    base_url: str = Field(..., description="LLM API的基础URL。", examples=["https://api.openai.com/v1"])
    apikey: str = Field(..., description="LLM API的密钥。注意：请勿在不安全的环境中暴露此密钥。",
                        examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"])
    model_id: str = Field(..., description="使用的模型ID。", examples=["gpt-4-turbo"])
    to_lang: str = Field("中文", description="目标翻译语言。", examples=["中文", "英文", "English"])
    formula_ocr: bool = Field(False, description="是否对公式进行OCR识别。")
    code_ocr: bool = Field(False, description="是否对代码块进行OCR识别。")
    refine_markdown: bool = Field(False, description="是否使用ai对解析后的文档进行一遍优化（现不推荐使用）")
    convert_engin: str = Field(..., description="文档解析和转换引擎，可选 'mineru' 或 'docling'。", examples=["mineru"])
    mineru_token: Optional[str] = Field(None, description="当使用 'mineru' 是必填。", examples=["token-abcdefg"])
    chunk_size: int = Field(..., description="文本分块的大小。", examples=[2048])
    concurrent: int = Field(..., description="并发请求的数量。", examples=[5])
    temperature: float = Field(..., description="LLM的温度参数，控制生成文本的随机性。", examples=[0.7])
    custom_prompt_translate: Optional[str] = Field(None, description="用户自定义的翻译Prompt。",
                                                   examples=["人名保持原文不翻译。"])
    file_name: str = Field(..., description="上传的原始文件名，包含扩展名。", examples=["my_document.pdf"])
    file_content: str = Field(..., description="Base64编码的文件内容。",
                              examples=["JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PAovVHlwZS..."])

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "task-abc-123",
                "base_url": "https://api.openai.com/v1",
                "apikey": "sk-your-api-key",
                "model_id": "gpt-4o",
                "to_lang": "简体中文",
                "formula_ocr": True,
                "code_ocr": True,
                "refine_markdown": False,
                "convert_engin": "mineru",
                "mineru_token": "your-mineru-token",
                "chunk_size": 2048,
                "concurrent": 5,
                "temperature": 0.1,
                "custom_prompt_translate": "Translate the following technical document into professional Chinese.",
                "file_name": "example.pdf",
                "file_content": "JVBERi0xLjQKJ..."
            }
        }


# ===================================================================
# --- Service Endpoints (/service) ---
# ===================================================================

@service_router.post(
    "/translate",
    summary="提交翻译任务 (Base64)",
    description="""
接收一个包含文件内容（Base64编码）和翻译参数的JSON请求，启动一个后台翻译任务。

- **异步处理**: 此端点会立即返回，不会等待翻译完成。
- **任务ID**: 成功启动后，会返回任务ID (`task_id`)。
- **后续步骤**: 客户端应使用返回的 `task_id` 轮询 `/service/status/{task_id}` 接口来获取任务进度和结果。
"""
)
async def service_translate(request: TranslateServiceRequest = Body(..., description="翻译任务的详细参数和文件内容。")):
    """
    提交一个文件进行翻译，并启动一个后台任务。
    文件内容需以Base64编码。
    返回任务ID，后续可凭此ID查询状态和下载结果。
    """
    try:
        file_contents = base64.b64decode(request.file_content)
    except (base64.binascii.Error, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"无效的Base64文件内容: {e}")

    params = request.model_dump(exclude={'file_name', 'file_content', 'task_id'})
    try:
        response_data = await _start_translation_task(
            task_id=request.task_id,
            params=params,
            file_contents=file_contents,
            original_filename=request.file_name
        )
        return JSONResponse(content=response_data)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"task_started": False, "message": e.detail})


@service_router.post(
    "/cancel/{task_id}",
    summary="取消翻译任务",
    description="根据任务ID取消一个正在进行的翻译任务。这是一个异步操作，发送取消请求后，任务不会立即停止，需要通过状态接口确认最终状态。"
)
async def service_cancel_translate(
        task_id: str = FastApiPath(..., description="要取消的任务的ID", example="task-12345")):
    """根据任务ID取消一个正在进行的翻译任务。"""
    try:
        response_data = _cancel_translation_logic(task_id)
        return JSONResponse(content=response_data)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"cancelled": False, "message": e.detail})


@service_router.get(
    "/status/{task_id}",
    summary="获取任务状态",
    description="""
根据任务ID获取任务的当前状态。

- **轮询**: 此端点设计用于被客户端轮询，以监控后台任务进度。
- **结果下载**: 当 `download_ready` 字段为 `true` 时，`downloads` 对象中会包含可用的下载链接。
"""
)
async def service_get_status(task_id: str = FastApiPath(..., description="要查询状态的任务的ID", example="task-12345")):
    """根据任务ID获取任务的当前状态和结果下载链接。"""
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    def generate_service_url(file_type):
        return f"/service/download/{task_id}/{file_type}" if task_state["download_ready"] else None

    return JSONResponse(content={
        "task_id": task_id,
        "is_processing": task_state["is_processing"],
        "status_message": task_state["status_message"],
        "error_flag": task_state["error_flag"],
        "download_ready": task_state["download_ready"],
        "original_filename_stem": task_state["original_filename_stem"],
        "original_filename": task_state.get("original_filename"),  # <--- MODIFIED
        "task_start_time": task_state["task_start_time"],
        "task_end_time": task_state["task_end_time"],
        "downloads": {
            "markdown": generate_service_url("markdown"),
            "markdown_zip": generate_service_url("markdown_zip"),
            "html": generate_service_url("html"),
        }
    })


@service_router.get(
    "/logs/{task_id}",
    summary="获取任务增量日志",
    description="获取指定任务ID自上次查询以来的新日志。这是一个非阻塞的轮询接口，用于实时显示后台任务的日志输出。"
)
async def service_get_logs(task_id: str = FastApiPath(..., description="要获取日志的任务的ID", example="task-12345")):
    """获取指定任务ID自上次查询以来的新日志。"""
    if task_id not in tasks_log_queues:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}' 的日志队列。")
    log_queue = tasks_log_queues[task_id]
    new_logs = []
    while not log_queue.empty():
        try:
            new_logs.append(log_queue.get_nowait())
            log_queue.task_done()
        except asyncio.QueueEmpty:
            break
    return JSONResponse(content={"logs": new_logs})


FileType = Literal["markdown", "markdown_zip", "html"]


@service_router.get(
    "/download/{task_id}/{file_type}",
    summary="下载翻译结果文件",
    description="根据任务ID和文件类型下载翻译结果。下载前请先通过状态接口确认 `download_ready` 为 `true`。"
)
async def service_download_file(
        task_id: str = FastApiPath(..., description="已完成任务的ID", example="task-12345"),
        file_type: FileType = FastApiPath(..., description="要下载的文件类型。", example="html")
):
    """根据任务ID和文件类型下载翻译结果。"""
    task_state = tasks_state.get(task_id)
    if not task_state: raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")
    if not task_state["download_ready"]: raise HTTPException(status_code=404, detail="内容尚未准备好。")

    content_map = {
        "markdown": (task_state["markdown_content"], "text/markdown",
                     f"{task_state['original_filename_stem']}_translated.md"),
        "markdown_zip": (task_state["markdown_zip_content"], "application/zip",
                         f"{task_state['original_filename_stem']}_translated.zip"),
        "html": (task_state["html_content"], "text/html", f"{task_state['original_filename_stem']}_translated.html"),
    }
    if file_type not in content_map: raise HTTPException(status_code=404, detail="无效的文件类型。")

    content, media_type, filename = content_map[file_type]
    if content is None: raise HTTPException(status_code=404, detail=f"{file_type.capitalize()} 内容不可用。")

    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='', encoding='utf-8')}"}
    if isinstance(content, str): return StreamingResponse(io.StringIO(content), media_type=media_type, headers=headers)
    return StreamingResponse(io.BytesIO(content), media_type=media_type, headers=headers)


@service_router.get("/engin-list", summary="获取可用解析引擎", tags=["Application"],
                    description="返回当前后端环境支持的文档解析引擎列表。前端可以根据此列表动态展示选项。")
async def service_get_engin_list():
    engin_list = ["mineru"]
    if available_packages.get("docling"): engin_list.append("docling")
    return JSONResponse(content=engin_list)


@service_router.get("/task-list", summary="获取所有任务ID列表", tags=["Application"],
                    description="返回当前服务实例中存在的所有任务ID的列表。可用于管理或概览所有已创建的任务。")
async def service_get_task_list():
    return JSONResponse(content=list(tasks_state.keys()))


@service_router.get("/default-params", summary="获取默认翻译参数", tags=["Application"],
                    description="返回一套默认的翻译参数，可用于填充前端表单的初始值。")
def service_get_default_params():
    return JSONResponse(content=default_params)


@service_router.get("/meta", summary="获取应用元信息", tags=["Application"],
                    description="返回应用程序的元数据，例如当前版本号。")
async def service_get_app_version():
    return JSONResponse(content={"version": __version__})


# ===================================================================
# --- 应用主路由和启动 ---
# ===================================================================

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def main_page():
    index_path = Path(STATIC_DIR) / "index.html"
    if not index_path.exists(): raise HTTPException(status_code=404, detail="index.html not found")
    no_cache_headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache",
                        "Expires": "0"}
    return FileResponse(index_path, headers=no_cache_headers)


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def main_page_admin():
    index_path = Path(STATIC_DIR) / "index.html"
    if not index_path.exists(): raise HTTPException(status_code=404, detail="index.html not found")
    no_cache_headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache",
                        "Expires": "0"}
    return FileResponse(index_path, headers=no_cache_headers)


@app.post("/temp/translate",
          summary="[内部] 临时同步翻译接口",
          description="一个简单的、同步的翻译接口，用于快速测试。不涉及后台任务、状态管理或多格式输出。**不建议在生产环境中使用。**",
          tags=["Internal / UI"])
async def temp_translate(
        base_url: str = Body(..., description="LLM API的基础URL。", example="https://api.openai.com/v1"),
        api_key: str = Body(..., description="LLM API的密钥。", example="sk-xxxxxxxxxx"),
        model_id: str = Body(..., description="使用的模型ID。", example="gpt-4-turbo"),
        mineru_token: str = Body(..., description="Mineru引擎的Token。"),
        file_name: str = Body(..., description="原始文件名。", example="test.txt"),
        file_content: str = Body(..., description="文件内容，可以是纯文本或Base64编码的字符串。"),
        to_lang: str = Body("中文", description="目标语言。"),
        concurrent: int = Body(30, description="ai翻译并发数")
        ):
    def is_base64(s):
        try:
            base64.b64decode(s)
            return True
        except Exception:
            return False

    ft = FileTranslater(base_url=base_url,
                        key=api_key,
                        model_id=model_id,
                        mineru_token=mineru_token,
                        concurrent=concurrent
                        )

    try:
        if is_base64(file_content):
            await ft.translate_bytes_async(name=file_name, file=base64.b64decode(file_content), to_lang=to_lang,
                                           save=False)
        else:
            await ft.translate_bytes_async(name=file_name, file=file_content.encode(), to_lang=to_lang, save=False)
        return {"success": True, "content": ft.export_to_markdown()}
    except Exception as e:
        print(f"翻译出现错误：{e.__repr__()}")
        return {"success": False, "reason": {e.__repr__()}}


app.include_router(service_router)


# --- 启动逻辑 (无修改) ---
def find_free_port(start_port):
    port = start_port
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(('127.0.0.1', port)) != 0: return port
            port += 1


def run_app(port: int | None = None):
    initial_port = port or int(os.environ.get("DOCUTRANSLATE_PORT", 8010))
    try:
        port_to_use = find_free_port(initial_port)
        if port_to_use != initial_port: print(f"端口 {initial_port} 被占用，将使用端口 {port_to_use} 代替")
        print(f"正在启动 DocuTranslate WebUI 版本号：{__version__}")
        print(f"请用浏览器访问 http://127.0.0.1:{port_to_use}")
        uvicorn.run(app, host=None, port=port_to_use, workers=1)
    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    run_app()
