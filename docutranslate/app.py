import asyncio
import base64
import binascii
import io
import logging
import os
import socket
import time
import uuid
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import List, Dict, Any, Optional, Literal, Union
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, APIRouter, Body, Path as FastApiPath
from fastapi.openapi.docs import (
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html, get_redoc_html,
)
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# --- 核心代码重构后的新 Imports ---
from docutranslate.manager.base_manager import BaseManager
from docutranslate.manager.md_based_manager import MarkdownBasedManager
from docutranslate.manager.txt_manager import TXTManager
from docutranslate.manager.interfaces import HTMLExportable, MDFormatsExportable, TXTExportable
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.exporter.md2x.md2html_exporter import MD2HTMLExportConfig
from docutranslate.exporter.txt2x.txt2html_exporter import TXT2HTMLExportConfig
from docutranslate.translater.base import AiTranslateConfig
from docutranslate.translater.md_translator import MDTranslateConfig
from docutranslate.translater.txt_translator import TXTTranslateConfig
# ------------------------------------

from docutranslate import __version__
from docutranslate.global_values import available_packages
from docutranslate.logger import global_logger
from docutranslate.translater import default_params
from docutranslate.utils.resource_utils import resource_path

# --- 全局配置 (MODIFIED) ---
tasks_state: Dict[str, Dict[str, Any]] = {}
tasks_log_queues: Dict[str, asyncio.Queue] = {}
tasks_log_histories: Dict[str, List[str]] = {}
MAX_LOG_HISTORY = 200
httpx_client: httpx.AsyncClient


# --- 辅助函数 (MODIFIED) ---
def _create_default_task_state() -> Dict[str, Any]:
    """创建新的默认任务状态，存储 manager 实例而不是具体内容"""
    return {
        "is_processing": False, "status_message": "空闲", "error_flag": False,
        "download_ready": False,
        "manager_instance": None,  # <--- 核心改动：存储翻译后的 Manager 实例
        "original_filename_stem": None, "task_start_time": 0,
        "task_end_time": 0, "current_task_ref": None,
        "original_filename": None,
    }


# --- Manager 工厂函数 (NEW) ---
def _get_manager_for_file(filename: str, logger: logging.Logger) -> BaseManager:
    """根据文件名后缀选择并返回合适的 Manager 实例。这是扩展点。"""
    suffix = Path(filename).suffix.lower()
    if suffix == '.txt':
        logger.info("检测到 .txt 文件，使用 TXTManager。")
        return TXTManager(logger=logger)
    else:
        # 默认为基于 Markdown 的流程（处理 .pdf, .docx, .md 等）
        logger.info(f"检测到 {suffix} 文件，使用 MarkdownBasedManager。")
        return MarkdownBasedManager(logger=logger)


# --- 日志处理器 (保持不变) ---
class QueueAndHistoryHandler(logging.Handler):
    def __init__(self, queue_ref: asyncio.Queue, history_list_ref: List[str], max_history_items: int, task_id: str):
        super().__init__()
        self.queue = queue_ref
        self.history_list = history_list_ref
        self.max_history = max_history_items
        self.task_id = task_id

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        print(f"[{self.task_id}] {log_entry}")
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
                print(f"[{self.task_id}] Log queue is full. Log dropped: {log_entry}")
            except Exception as e:
                print(f"[{self.task_id}] Error putting log to queue: {e}. Log: {log_entry}")


# --- 应用生命周期事件 (保持不变) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global httpx_client
    app.state.main_event_loop = asyncio.get_running_loop()
    httpx_client = httpx.AsyncClient()
    tasks_state.clear()
    tasks_log_queues.clear()
    tasks_log_histories.clear()
    global_logger.propagate = False
    global_logger.setLevel(logging.INFO)
    print("应用启动完成，多任务状态已初始化。")
    yield
    await httpx_client.aclose()
    print("应用关闭，资源已清理。")


# --- Background Task Logic (核心业务逻辑, 已重构) ---
async def _perform_translation(task_id: str, params: Dict[str, Any], file_contents: bytes, original_filename: str):
    task_state = tasks_state[task_id]
    log_queue = tasks_log_queues[task_id]
    log_history = tasks_log_histories[task_id]

    task_logger = logging.getLogger(f"task.{task_id}")
    task_logger.setLevel(logging.INFO)
    task_logger.propagate = False
    if task_logger.hasHandlers():
        task_logger.handlers.clear()
    task_handler = QueueAndHistoryHandler(log_queue, log_history, MAX_LOG_HISTORY, task_id=task_id)
    task_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    task_logger.addHandler(task_handler)

    task_logger.info(f"后台翻译任务开始: 文件 '{original_filename}'")
    task_state["status_message"] = f"正在处理 '{original_filename}'..."

    try:
        # 1. 选择合适的 Manager
        manager = _get_manager_for_file(original_filename, task_logger)

        # 2. 从扁平化的 params 构建结构化的 Config 对象
        ai_config = AiTranslateConfig(
            base_url=params['base_url'],
            api_key=params['apikey'],
            model_id=params['model_id'],
            to_lang=params['to_lang'],
            custom_prompt=params['custom_prompt_translate'],
            temperature=params['temperature'],
            timeout=2000,  # 保持默认或从params获取
            chunk_size=params['chunk_size'],
            concurrent=params['concurrent'],
            logger=task_logger
        )

        # 3. 读取文件内容
        file_stem = Path(original_filename).stem
        file_suffix = Path(original_filename).suffix
        manager.read_bytes(content=file_contents, stem=file_stem, suffix=file_suffix)

        # 4. 根据 Manager 类型执行不同的翻译流程
        if isinstance(manager, MarkdownBasedManager):
            task_logger.info("使用 Markdown 翻译流程。")
            translate_config = MDTranslateConfig(**ai_config.__dict__)
            convert_engin = params['convert_engin']
            convert_config = None
            if convert_engin == 'mineru':
                if not params.get('mineru_token'):
                    raise ValueError("使用 'mineru' 引擎需要提供 'mineru_token'。")
                convert_config = ConverterMineruConfig(
                    mineru_token=params['mineru_token'],
                    formula=params['formula_ocr']
                )
            elif convert_engin == 'docling':
                convert_config = ConverterDoclingConfig(
                    code=params['code_ocr'],
                    formula=params['formula_ocr']
                )

            await manager.translate_async(
                convert_engin=convert_engin,
                convert_config=convert_config,
                translate_config=translate_config
            )

        elif isinstance(manager, TXTManager):
            task_logger.info("使用 TXT 翻译流程。")
            translate_config = TXTTranslateConfig(**ai_config.__dict__)
            await manager.translate_async(translate_config=translate_config)

        else:
            raise TypeError(f"不支持的 Manager 类型: {type(manager).__name__}")

        # 5. 任务成功，存储 manager 实例并更新状态
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        task_state.update({
            "manager_instance": manager,  # <--- 存储实例
            "status_message": f"翻译成功！用时 {duration:.2f} 秒。",
            "download_ready": True,
            "error_flag": False,
            "task_end_time": end_time,
        })
        task_logger.info(f"翻译成功完成，用时 {duration:.2f} 秒。")

    except asyncio.CancelledError:
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        task_logger.info(f"翻译任务 '{original_filename}' 已被取消 (用时 {duration:.2f} 秒).")
        task_state.update({
            "status_message": f"翻译任务已取消 (用时 {duration:.2f} 秒).",
            "error_flag": False,
            "download_ready": False,
            "manager_instance": None,
            "task_end_time": end_time,
        })

    except Exception as e:
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        error_message = f"翻译失败: {e}"
        task_logger.error(error_message, exc_info=True)
        task_state.update({
            "status_message": f"翻译过程中发生错误 (用时 {duration:.2f} 秒): {e}",
            "error_flag": True,
            "download_ready": False,
            "manager_instance": None,
            "task_end_time": end_time,
        })

    finally:
        task_state["is_processing"] = False
        task_state["current_task_ref"] = None
        task_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")
        task_logger.removeHandler(task_handler)


# --- 核心任务启动与取消逻辑 (保持不变) ---
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
        "manager_instance": None,  # 重置
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
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")
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


# --- FastAPI 应用和路由设置 (保持不变) ---
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
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    title="DocuTranslate API",
    description=f"""
DocuTranslate 后端服务 API，提供文档翻译、状态查询、结果下载等功能。

**注意**: 所有任务状态都保存在服务进程的内存中，服务重启将导致所有任务信息丢失。

### 主要工作流程:
1.  **`POST /service/translate`**: 提交文件和翻译参数，启动一个后台任务。服务会自动生成并返回一个唯一的 `task_id`。
2.  **`GET /service/status/{{task_id}}`**: 使用获取到的 `task_id` 轮询此端点，获取任务的实时状态。
3.  **`GET /service/logs/{{task_id}}`**: (可选) 获取实时的翻译日志。
4.  **`GET /service/download/{{task_id}}/{{file_type}}`**: 任务完成后 (当 `download_ready` 为 `true` 时)，通过此端点下载结果文件。
5.  **`GET /service/content/{{task_id}}/{{file_type}}`**: 任务完成后(当 `download_ready` 为 `true` 时)，以JSON格式获取文件内容。
6.  **`POST /service/cancel/{{task_id}}`**: (可选) 取消一个正在进行的任务。
7.  **`POST /service/release/{{task_id}}`**: (可选) 当任务不再需要时，释放其在服务器上占用的所有资源。

**版本**: {__version__}
""",
    version=__version__,
    openapi_tags=tags_metadata,
)

service_router = APIRouter(prefix="/service", tags=["Service API"])
STATIC_DIR = resource_path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ===================================================================
# --- Pydantic Models for Service API (MODIFIED) ---
# ===================================================================
class TranslateServiceRequest(BaseModel):
    base_url: str = Field(..., description="LLM API的基础URL。", examples=["https://api.openai.com/v1"])
    apikey: str = Field(..., description="LLM API的密钥。", examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"])
    model_id: str = Field(..., description="要使用的LLM模型ID。", examples=["gpt-4o"])
    to_lang: str = Field(default="中文", description="目标翻译语言。", examples=["简体中文", "English"])

    # --- Converter Params ---
    convert_engin: Literal["mineru", "docling", "auto"] = Field(
        "auto",
        description="文档解析引擎。`mineru`在线服务, `docling`本地引擎, `auto`自动选择(优先mineru)。",
        examples=["mineru", "docling", "auto"]
    )
    mineru_token: Optional[str] = Field(None, description="当 `convert_engin` 为 'mineru' 时必填的API令牌。")
    formula_ocr: bool = Field(True, description="是否对公式进行OCR识别。对 `mineru` 和 `docling` 均有效。")
    code_ocr: bool = Field(True, description="是否对代码块进行OCR识别。仅 `docling` 引擎有效。")

    # --- Translator Params ---
    chunk_size: int = Field(default_params["chunk_size"], description="文本分割的块大小（字符）。")
    concurrent: int = Field(default_params["concurrent"], description="并发请求数。")
    temperature: float = Field(default_params["temperature"], description="LLM温度参数。")
    custom_prompt_translate: Optional[str] = Field(None, description="用户自定义的翻译Prompt。")

    # --- File Info ---
    file_name: str = Field(..., description="上传的原始文件名，含扩展名。", examples=["my_paper.pdf"])
    file_content: str = Field(..., description="Base64编码的文件内容。", examples=["JVBERi0xLjQK..."])

    # refine_markdown: bool = Field(False, description="[已废弃] 此功能在新版中已移除。")

    class Config:
        json_schema_extra = {
            "example": {
                "base_url": "https://api.openai.com/v1",
                "apikey": "sk-your-api-key-here",
                "model_id": "gpt-4o",
                "to_lang": "简体中文",
                "convert_engin": "mineru",
                "mineru_token": "your-mineru-token-if-any",
                "formula_ocr": True,
                "code_ocr": True,
                "chunk_size": 3000,
                "concurrent": 10,
                "temperature": 0.1,
                "custom_prompt_translate": "将所有技术术语翻译为业界公认的中文对应词汇。",
                "file_name": "annual_report_2023.pdf",
                "file_content": "JVBERi0xLjcKJeLjz9MKMSAwIG9iago8PC9..."
            }
        }


# ===================================================================
# --- Service Endpoints (/service) (部分已重构) ---
# ===================================================================

@service_router.post(
    "/translate",
    summary="提交翻译任务 (Base64)",
    description="""
接收一个包含文件内容（Base64编码）和翻译参数的JSON请求，启动一个后台翻译任务。

- **异步处理**: 此端点会立即返回，不会等待翻译完成。
- **任务ID**: 成功启动后，服务会自动生成并返回任务ID (`task_id`)。
- **后续步骤**: 客户端应使用返回的 `task_id` 轮询 `/service/status/{task_id}` 接口来获取任务进度和结果。
""",
    responses={
        200: {
            "description": "翻译任务成功启动。",
            "content": {"application/json": {"example": {"task_started": True, "task_id": "b2865b93",
                                                         "message": "翻译任务已成功启动，请稍候..."}}}
        },
        400: {"description": "请求体中的Base64文件内容无效。",
              "content": {"application/json": {"example": {"detail": "无效的Base64文件内容: Incorrect padding"}}}},
        429: {"description": "服务器内部任务冲突，请重试。", "content": {
            "application/json": {
                "example": {"task_started": False, "message": "任务ID 'b2865b93' 正在进行中，请稍后再试。"}}}},
        500: {"description": "服务器内部错误，导致任务启动失败。",
              "content": {
                  "application/json": {
                      "example": {"task_started": False, "message": "启动翻译任务时出错: [具体错误信息]"}}}},
    }
)
async def service_translate(request: TranslateServiceRequest = Body(..., description="翻译任务的详细参数和文件内容。")):
    """
    提交一个文件进行翻译，并启动一个后台任务。
    文件内容需以Base64编码，任务ID将由后端自动生成并返回。
    后续可凭此ID查询状态和下载结果。
    """
    task_id = uuid.uuid4().hex[:8]

    try:
        file_contents = base64.b64decode(request.file_content)
    except (binascii.Error, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"无效的Base64文件内容: {e}")

    params = request.model_dump(exclude={'file_name', 'file_content'})

    # 自动选择引擎逻辑
    if params['convert_engin'] == 'auto':
        params['convert_engin'] = 'mineru' if params.get('mineru_token') else 'docling'
        print(f"[{task_id}] 自动选择解析引擎: {params['convert_engin']}")

    try:
        response_data = await _start_translation_task(
            task_id=task_id,
            params=params,
            file_contents=file_contents,
            original_filename=request.file_name
        )
        return JSONResponse(content=response_data)
    except HTTPException as e:
        if e.status_code == 429:
            return JSONResponse(status_code=e.status_code, content={"task_started": False, "message": e.detail})
        if e.status_code == 500:
            return JSONResponse(status_code=e.status_code, content={"task_started": False, "message": e.detail})
        raise e


@service_router.post(
    "/cancel/{task_id}",
    summary="取消翻译任务",
    description="根据任务ID取消一个正在进行的翻译任务。这是一个异步操作，发送取消请求后，任务不会立即停止，需要通过状态接口确认最终状态。",
    responses={
        200: {
            "description": "取消请求已成功发送。",
            "content": {
                "application/json": {"example": {"cancelled": True, "message": "取消请求已发送。请等待状态更新。"}}}
        },
        400: {
            "description": "任务未在进行、已完成或已被取消，无法执行取消操作。",
            "content": {"application/json": {"example": {"cancelled": False, "message": "任务已完成或已被取消。"}}}
        },
        404: {
            "description": "指定的任务ID不存在。",
            "content": {
                "application/json": {"example": {"cancelled": False, "message": "找不到任务ID 'task-not-exist'。"}}}
        },
    }
)
async def service_cancel_translate(
        task_id: str = FastApiPath(..., description="要取消的任务的ID", examples=["b2865b93"])):
    """根据任务ID取消一个正在进行的翻译任务。"""
    try:
        response_data = _cancel_translation_logic(task_id)
        return JSONResponse(content=response_data)
    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"cancelled": False, "message": e.detail})


@service_router.post(
    "/release/{task_id}",
    summary="释放任务资源",
    description="""
根据任务ID释放其占用的所有服务器资源（状态、日志、结果等）。

- **自动取消**: 如果任务正在进行中，此接口会先尝试取消该任务，然后再释放资源。
- **资源清理**: 此操作会从服务器内存中彻底删除任务的所有信息。操作不可逆。
- **使用场景**: 当一个任务完成、失败或不再需要时，调用此接口可以清理内存，避免不必要的资源占用，尤其是在多任务场景下。
""",
    responses={
        200: {
            "description": "任务资源已成功释放。",
            "content": {
                "application/json": {"example": {"released": True, "message": "任务 'b2865b93' 的资源已释放。"}}
            }
        },
        404: {
            "description": "指定的任务ID不存在。",
            "content": {
                "application/json": {"example": {"released": False, "message": "找不到任务ID 'task-not-exist'。"}}}
        },
    }
)
async def service_release_task(
        task_id: str = FastApiPath(..., description="要释放资源的任务的ID", examples=["b2865b93"])
):
    """根据任务ID释放其占用的所有服务器资源。"""
    if task_id not in tasks_state:
        return JSONResponse(
            status_code=404,
            content={"released": False, "message": f"找不到任务ID '{task_id}'。"}
        )

    task_state = tasks_state.get(task_id)
    message_parts = []

    if task_state and task_state.get("is_processing") and task_state.get("current_task_ref"):
        try:
            print(f"[{task_id}] 任务正在进行中，将在释放前尝试取消。")
            _cancel_translation_logic(task_id)
            message_parts.append("任务已被取消。")
        except HTTPException as e:
            print(f"[{task_id}] 取消任务时出现预期中的情况（可能已完成）: {e.detail}")
            message_parts.append(f"任务取消步骤已跳过（可能已完成或取消）。")

    tasks_state.pop(task_id, None)
    tasks_log_queues.pop(task_id, None)
    tasks_log_histories.pop(task_id, None)

    print(f"[{task_id}] 资源已成功释放。")
    message_parts.append(f"任务 '{task_id}' 的资源已释放。")

    final_message = " ".join(message_parts)
    return JSONResponse(content={"released": True, "message": final_message})


@service_router.get(
    "/status/{task_id}",
    summary="获取任务状态",
    description="""
根据任务ID获取任务的当前状态。

- **轮询**: 此端点设计用于被客户端轮询，以监控后台任务进度。
- **结果下载**: 当 `download_ready` 字段为 `true` 时，`downloads` 对象中会包含可用的下载链接。
""",
    responses={
        200: {
            "description": "成功获取任务状态。",
            "content": {
                "application/json": {
                    "examples": {
                        "processing": {
                            "summary": "处理中",
                            "value": {
                                "task_id": "b2865b93",
                                "is_processing": True,
                                "status_message": "正在翻译: 15/50 块",
                                "error_flag": False,
                                "download_ready": False,
                                "original_filename_stem": "annual_report_2023",
                                "original_filename": "annual_report_2023.pdf",
                                "task_start_time": 1678886400.123,
                                "task_end_time": 0,
                                "downloads": {}
                            }
                        },
                        "completed": {
                            "summary": "已完成",
                            "value": {
                                "task_id": "b2865b93",
                                "is_processing": False,
                                "status_message": "翻译成功！用时 123.45 秒。",
                                "error_flag": False,
                                "download_ready": True,
                                "original_filename_stem": "annual_report_2023",
                                "original_filename": "annual_report_2023.pdf",
                                "task_start_time": 1678886400.123,
                                "task_end_time": 1678886523.573,
                                "downloads": {
                                    "markdown": "/service/download/b2865b93/markdown",
                                    "markdown_zip": "/service/download/b2865b93/markdown_zip",
                                    "html": "/service/download/b2865b93/html"
                                }
                            }
                        },
                        "error": {
                            "summary": "出错",
                            "value": {
                                "task_id": "b2865b93",
                                "is_processing": False,
                                "status_message": "翻译过程中发生错误 (用时 45.67 秒): APIConnectionError(...)",
                                "error_flag": True,
                                "download_ready": False,
                                "original_filename_stem": "annual_report_2023",
                                "original_filename": "annual_report_2023.pdf",
                                "task_start_time": 1678886400.123,
                                "task_end_time": 1678886445.793,
                                "downloads": {}
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "指定的任务ID不存在。",
            "content": {"application/json": {"example": {"detail": "找不到任务ID 'task-not-exist'。"}}}
        },
    }
)
async def service_get_status(
        task_id: str = FastApiPath(..., description="要查询状态的任务的ID", examples=["b2865b93"])):
    """根据任务ID获取任务的当前状态和结果下载链接。"""
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    # (MODIFIED) 动态生成可用的下载链接
    downloads = {}
    if task_state.get("download_ready") and task_state.get("manager_instance"):
        manager = task_state["manager_instance"]
        if isinstance(manager, HTMLExportable):
            downloads["html"] = f"/service/download/{task_id}/html"
        if isinstance(manager, MDFormatsExportable):
            downloads["markdown"] = f"/service/download/{task_id}/markdown"
            downloads["markdown_zip"] = f"/service/download/{task_id}/markdown_zip"
        if isinstance(manager, TXTExportable):
            downloads["txt"] = f"/service/download/{task_id}/txt"

    return JSONResponse(content={
        "task_id": task_id,
        "is_processing": task_state["is_processing"],
        "status_message": task_state["status_message"],
        "error_flag": task_state["error_flag"],
        "download_ready": task_state["download_ready"],
        "original_filename_stem": task_state["original_filename_stem"],
        "original_filename": task_state.get("original_filename"),
        "task_start_time": task_state["task_start_time"],
        "task_end_time": task_state["task_end_time"],
        "downloads": downloads
    })


@service_router.get(
    "/logs/{task_id}",
    summary="获取任务增量日志",
    description="获取指定任务ID自上次查询以来的新日志。这是一个非阻塞的轮询接口，用于实时显示后台任务的日志输出。",
    responses={
        200: {
            "description": "成功获取新的日志条目。如果没有新日志，将返回一个空列表。",
            "content": {"application/json": {
                "example": {
                    "logs": [
                        "2023-10-27 10:30:05 - INFO - 后台翻译任务开始: 文件 'annual_report_2023.pdf'",
                        "2023-10-27 10:30:05 - INFO - 使用 Base URL: https://api.openai.com/v1, Model: gpt-4o",
                        "2023-10-27 10:30:15 - INFO - 正在转化为markdown",
                        "2023-10-27 10:30:25 - INFO - markdown分为50块",
                        "2023-10-27 10:30:30 - INFO - 正在翻译markdown"
                    ]
                }}}
        },
        404: {
            "description": "指定的任务ID不存在。",
            "content": {"application/json": {"example": {"detail": "找不到任务ID 'task-not-exist' 的日志队列。"}}}
        },
    }
)
async def service_get_logs(
        task_id: str = FastApiPath(..., description="要获取日志的任务的ID", examples=["b2865b93"])):
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


FileType = Literal["markdown", "markdown_zip", "html", "txt"]


async def _get_content_from_manager(task_id: str, file_type: FileType) -> tuple[bytes | str, str, str]:
    """辅助函数，从 manager 获取内容、媒体类型和文件名"""
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")
    if not task_state.get("download_ready") or not task_state.get("manager_instance"):
        raise HTTPException(status_code=404, detail="内容尚未准备好。")

    manager: BaseManager = task_state["manager_instance"]
    filename_stem = task_state['original_filename_stem']

    try:
        if file_type == 'html' and isinstance(manager, HTMLExportable):
            # 自动判断使用哪种 HTML Export Config
            config = MD2HTMLExportConfig(cdn=True) if isinstance(manager, MarkdownBasedManager) else TXT2HTMLExportConfig(cdn=True)
            try:
                # 尝试连接CDN，失败则回退
                await httpx_client.head("https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js", timeout=3)
            except (httpx.TimeoutException, httpx.RequestError):
                manager.logger.info("CDN连接失败，使用本地JS进行渲染。")
                if hasattr(config, 'cdn'):
                    config.cdn = False
            content = manager.export_to_html(config)
            return content.encode('utf-8'), "text/html; charset=utf-8", f"{filename_stem}_translated.html"

        if file_type == 'markdown' and isinstance(manager, MDFormatsExportable):
            md_content = manager.export_to_markdown()
            return md_content.encode('utf-8'), "text/markdown; charset=utf-8", f"{filename_stem}_translated.md"

        if file_type == 'markdown_zip' and isinstance(manager, MDFormatsExportable):
            return manager.export_to_markdown_zip(), "application/zip", f"{filename_stem}_translated.zip"

        if file_type == 'txt' and isinstance(manager, TXTExportable):
            txt_content = manager.export_to_txt()
            return txt_content.encode('utf-8'), "text/plain; charset=utf-8", f"{filename_stem}_translated.txt"

    except Exception as e:
        manager.logger.error(f"导出 {file_type} 时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出 {file_type} 时发生内部错误: {e}")

    raise HTTPException(status_code=404, detail=f"此任务不支持导出 '{file_type}' 类型的文件。")


@service_router.get(
    "/download/{task_id}/{file_type}",
    summary="下载翻译结果文件",
    description="根据任务ID和文件类型下载翻译结果。下载前请先通过状态接口确认 `download_ready` 为 `true`。",
    responses={
        200: {
            "description": "成功返回文件流。响应头 `Content-Disposition` 会指定文件名。",
            "content": {
                "text/markdown": {"schema": {"type": "string", "format": "binary"}},
                "application/zip": {"schema": {"type": "string", "format": "binary"}},
                "text/html": {"schema": {"type": "string", "format": "binary"}},
                "text/plain": {"schema": {"type": "string", "format": "binary"}},
            }
        },
        404: {
            "description": "资源未找到。可能的原因包括：任务ID不存在、任务结果尚未就绪、或请求了无效的文件类型。",
            "content": {"application/json": {"example": {"detail": "内容尚未准备好。"}}}
        },
    }
)
async def service_download_file(
        task_id: str = FastApiPath(..., description="已完成任务的ID", examples=["b2865b93"]),
        file_type: FileType = FastApiPath(..., description="要下载的文件类型。", examples=["html"])
):
    """根据任务ID和文件类型下载翻译结果。"""
    content, media_type, filename = await _get_content_from_manager(task_id, file_type)

    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='', encoding='utf-8')}"}
    return StreamingResponse(io.BytesIO(content), media_type=media_type, headers=headers)


@service_router.get(
    "/content/{task_id}/{file_type}",
    summary="下载翻译结果内容 (JSON)",
    description="""
根据任务ID和文件类型，以JSON格式返回翻译结果的内容。该接口总是返回一个JSON对象。

- **返回结构**: JSON对象包含 `file_type`, `filename`, 和 `content` 三个字段。
- **内容编码**:
  - 对于 `html`, `markdown`, `txt` 类型, `content` 字段包含原始的文本内容。
  - 对于 `markdown_zip` 类型, `content` 字段包含Base64编码后的字符串。
- **使用场景**: 适用于需要以编程方式处理文件内容及其元数据（如建议的文件名）的客户端。
- **下载就绪**: 调用前请通过状态接口确认 `download_ready` 为 `true`。
""",
    responses={
        200: {
            "description": "成功返回文件内容。",
            "content": {
                "application/json": {
                    "examples": {
                        "html": {
                            "summary": "HTML 内容",
                            "value": {
                                "file_type": "html",
                                "original_filename": "my_doc_translated.html",
                                "content": "<h1>标题</h1><p>这是翻译后的HTML内容...</p>"
                            }
                        },
                        "markdown_zip_base64": {
                            "summary": "ZIP 内容 (Base64)",
                            "value": {
                                "file_type": "markdown_zip",
                                "filename": "my_doc_translated.zip",
                                "content": "UEsDBBQAAAAIA... (base64-encoded string)"
                            }
                        }
                    }
                }
            }
        },
        404: {
            "description": "资源未找到。",
            "content": {"application/json": {"example": {"detail": "内容尚未准备好。"}}}
        },
    }
)
async def service_content(
        task_id: str = FastApiPath(..., description="已完成任务的ID", examples=["b2865b93"]),
        file_type: FileType = FastApiPath(..., description="要获取内容的文件类型。", examples=["html"])
):
    """根据任务ID和文件类型，以JSON格式返回内容。zip文件会进行Base64编码。"""
    content, _, filename = await _get_content_from_manager(task_id, file_type)

    if isinstance(content, bytes):
        try:
            # For text-based formats, decode to string
            final_content = content.decode('utf-8')
        except UnicodeDecodeError:
            # For binary formats (like zip), encode to Base64
            final_content = base64.b64encode(content).decode('utf-8')
    else: # Should not happen with current _get_content_from_manager, but for safety
        final_content = content


    return JSONResponse(content={
        "file_type": file_type,
        "filename": filename,
        "content": final_content
    })


@service_router.get(
    "/engin-list",
    summary="获取可用解析引擎",
    tags=["Application"],
    description="返回当前后端环境支持的文档解析引擎列表。前端可以根据此列表动态展示选项。",
    response_model=List[str],
    responses={
        200: {
            "description": "成功返回可用引擎列表。",
            "content": {"application/json": {"example": ["auto", "mineru", "docling"]}}
        }
    }
)
async def service_get_engin_list():
    """返回可用的文档解析引擎列表。"""
    engin_list = ["auto", "mineru"]
    if available_packages.get("docling"):
        engin_list.append("docling")
    return JSONResponse(content=engin_list)


@service_router.get(
    "/task-list",
    summary="获取所有任务ID列表",
    tags=["Application"],
    description="返回当前服务实例中存在的所有任务ID的列表。可用于管理或概览所有已创建的任务。",
    response_model=List[str],
    responses={
        200: {
            "description": "成功返回任务ID列表。",
            "content": {"application/json": {"example": ["b2865b93", "f4e2a1c8"]}}
        }
    }
)
async def service_get_task_list():
    """返回当前服务中所有任务的ID列表。"""
    return JSONResponse(content=list(tasks_state.keys()))


@service_router.get(
    "/default-params",
    summary="获取默认翻译参数",
    tags=["Application"],
    description="返回一套默认的翻译参数，可用于填充前端表单的初始值。",
    response_model=Dict[str, Union[str, int, float, bool]],
    responses={
        200: {
            "description": "成功返回默认参数。",
            "content": {"application/json": {"example": default_params}}
        }
    }
)
def service_get_default_params():
    """返回一套默认的翻译参数。"""
    return JSONResponse(content=default_params)


@service_router.get(
    "/meta",
    summary="获取应用元信息",
    tags=["Application"],
    description="返回应用程序的元数据，例如当前版本号。",
    response_model=Dict[str, str],
    responses={
        200: {
            "description": "成功返回元信息。",
            "content": {"application/json": {"example": {"version": "0.1.0"}}}
        }
    }
)
async def service_get_app_version():
    """返回应用版本号等元信息。"""
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


###文档服务
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger/swagger.js",
        swagger_css_url="/static/swagger/swagger.css",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/redoc/redoc.js",
    )


###

@app.post("/temp/translate",
          summary="[临时]同步翻译接口 (已重构)",
          description="一个简单的、同步的翻译接口，用于快速测试。不涉及后台任务、状态管理或多格式输出。**不建议在生产环境中使用。**",
          tags=["Temp"],
          responses={
              200: {
                  "description": "翻译成功或失败。",
                  "content": {"application/json": {
                      "examples": {
                          "success": {
                              "summary": "成功示例",
                              "value": {"success": True, "content": "# 翻译后的标题\n\n这是翻译后的内容..."}
                          },
                          "failure": {
                              "summary": "失败示例",
                              "value": {"success": False, "reason": "Exception('API call failed with status 401')"}
                          }
                      }
                  }}
              }
          })
async def temp_translate(
        base_url: str = Body(..., description="LLM API的基础URL。", examples=["https://api.openai.com/v1"]),
        api_key: str = Body(..., description="LLM API的密钥。", examples=["sk-xxxxxxxxxx"]),
        model_id: str = Body(..., description="使用的模型ID。", examples=["gpt-4-turbo"]),
        mineru_token: Optional[str] = Body(None, description="Mineru引擎的Token。"),
        file_name: str = Body(...,
                              description="文件名，用以判断文件类型。当后缀为txt时该接口返回普通文本，为其他后缀时返回翻译后的markdown文本",
                              examples=["test.txt", "test.md", "test.pdf"]),
        file_content: str = Body(..., description="文件内容，可以是纯文本或Base64编码的字符串。"),
        to_lang: str = Body("中文", description="目标语言。", examples=["中文", "英文", "English"]),
        concurrent: int = Body(default_params["concurrent"], description="ai翻译请求并发数"),
        temperature: float = Body(default_params["temperature"], description="ai翻译请求温度"),
        chunk_size: int = Body(default_params["chunk_size"], description="文本分块大小（bytes）"),
        custom_prompt_translate: Optional[str] = Body(None, description="翻译自定义提示词",
                                                   examples=["人名保持原文不翻译"]),
):
    """一个用于快速测试的同步翻译接口。"""
    try:
        decoded_content = base64.b64decode(file_content)
    except (ValueError, binascii.Error):
        decoded_content = file_content.encode('utf-8')

    try:
        manager = _get_manager_for_file(file_name, global_logger)

        ai_config = AiTranslateConfig(
            base_url=base_url, api_key=api_key, model_id=model_id, to_lang=to_lang,
            custom_prompt=custom_prompt_translate, temperature=temperature,
            chunk_size=chunk_size, concurrent=concurrent, logger=global_logger, timeout=2000
        )

        manager.read_bytes(decoded_content, Path(file_name).stem, Path(file_name).suffix)

        if isinstance(manager, MarkdownBasedManager):
            translate_config = MDTranslateConfig(**ai_config.__dict__)
            convert_config = ConverterMineruConfig(mineru_token=mineru_token) if mineru_token else None
            convert_engin = 'mineru' if mineru_token else None
            await manager.translate_async(convert_engin, convert_config, translate_config)
            return {"success": True, "content": manager.document_translated.get_text()}

        elif isinstance(manager, TXTManager):
            translate_config = TXTTranslateConfig(**ai_config.__dict__)
            await manager.translate_async(translate_config)
            return {"success": True, "content": manager.export_to_txt()}

    except Exception as e:
        print(f"临时翻译接口出现错误：{e.__repr__()}")
        return {"success": False, "reason": e.__repr__()}


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
        print(f"正在启动 DocuTranslate WebUI 版本号：{__version__}\n")
        print(f"服务接口文档: http://127.0.0.1:{port_to_use}/docs\n")
        print(f"请用浏览器访问 http://127.0.0.1:{port_to_use}\n")
        uvicorn.run(app, host="0.0.0.0", port=port_to_use, workers=1)
    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    run_app()