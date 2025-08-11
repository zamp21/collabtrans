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
from typing import List, Dict, Any, Optional, Literal, Union, Annotated, TYPE_CHECKING, Type
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, APIRouter, Body, Path as FastApiPath
from fastapi.openapi.docs import get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html, get_redoc_html
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from docutranslate import __version__
from docutranslate.agents.agent import ThinkingMode
from docutranslate.cacher import md_based_convert_cacher
from docutranslate.exporter.md.types import ConvertEngineType
# --- 核心代码 Imports ---
from docutranslate.global_values.conditional_import import DOCLING_EXIST
from docutranslate.workflow.base import Workflow
from docutranslate.workflow.docx_workflow import DocxWorkflow, DocxWorkflowConfig
from docutranslate.workflow.epub_workflow import EpubWorkflow, EpubWorkflowConfig
from docutranslate.workflow.interfaces import DocxExportable, EpubExportable
from docutranslate.workflow.interfaces import HTMLExportable, MDFormatsExportable, TXTExportable, JsonExportable, \
    XlsxExportable, SrtExportable
from docutranslate.workflow.json_workflow import JsonWorkflow, JsonWorkflowConfig
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.workflow.srt_workflow import SrtWorkflow, SrtWorkflowConfig
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflow, XlsxWorkflowConfig

if DOCLING_EXIST or TYPE_CHECKING:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.srt_translator import SrtTranslatorConfig
from docutranslate.exporter.srt.srt2html_exporter import Srt2HTMLExporterConfig
from docutranslate.translator.ai_translator.epub_translator import EpubTranslatorConfig
from docutranslate.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig
# ------------------------------------

from docutranslate.logger import global_logger
from docutranslate.translator import default_params
from docutranslate.utils.resource_utils import resource_path

# --- 全局配置 ---
tasks_state: Dict[str, Dict[str, Any]] = {}
tasks_log_queues: Dict[str, asyncio.Queue] = {}
tasks_log_histories: Dict[str, List[str]] = {}
MAX_LOG_HISTORY = 200
httpx_client: httpx.AsyncClient

# --- Workflow字典 ---
WORKFLOW_DICT: Dict[str, Type[Workflow]] = {
    "markdown_based": MarkdownBasedWorkflow,
    "txt": TXTWorkflow,
    "json": JsonWorkflow,
    "xlsx": XlsxWorkflow,
    "docx": DocxWorkflow,
    "srt": SrtWorkflow,
    "epub": EpubWorkflow,
}


# --- 辅助函数 ---
def _create_default_task_state() -> Dict[str, Any]:
    """创建新的默认任务状态，存储 workflow 实例而不是具体内容"""
    return {
        "is_processing": False, "status_message": "空闲", "error_flag": False,
        "download_ready": False,
        "workflow_instance": None,
        "original_filename_stem": None, "task_start_time": 0,
        "task_end_time": 0, "current_task_ref": None,
        "original_filename": None,
    }


# --- 日志处理器 ---
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


# --- 应用生命周期事件 ---
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
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
    title="DocuTranslate API",
    description=f"""
DocuTranslate 后端服务 API，提供文档翻译、状态查询、结果下载等功能。

**注意**: 所有任务状态都保存在服务进程的内存中，服务重启将导致所有任务信息丢失。

### 主要工作流程:
1.  **`POST /service/translate`**: 提交文件和包含`workflow_type`的翻译参数，启动一个后台任务。服务会自动生成并返回一个唯一的 `task_id`。
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
# --- Pydantic Models for Service API ---
# ===================================================================

# 1. 定义所有工作流共享的基础参数
class BaseWorkflowParams(BaseModel):
    base_url: str = Field(..., description="LLM API的基础URL。", examples=["https://api.openai.com/v1"])
    api_key: str = Field(..., description="LLM API的密钥。", examples=["sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx"])
    model_id: str = Field(..., description="要使用的LLM模型ID。", examples=["gpt-4o"])
    to_lang: str = Field(default="中文", description="目标翻译语言。", examples=["简体中文", "English"])
    chunk_size: int = Field(default=default_params["chunk_size"], description="文本分割的块大小（字符）。")
    concurrent: int = Field(default=default_params["concurrent"], description="并发请求数。")
    temperature: float = Field(default=default_params["temperature"], description="LLM温度参数。")
    thinking: ThinkingMode = Field(default=default_params["thinking"], description="是否启用深度思考",
                                   examples=["default", "enable", "disable"]),
    custom_prompt: Optional[str] = Field(None, description="用户自定义的翻译Prompt。", alias="custom_prompt")


# 2. 为每个工作流创建独立的参数模型
class MarkdownWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal['markdown_based'] = Field(..., description="指定使用基于Markdown的翻译工作流。")
    convert_engine: ConvertEngineType = Field(
        "identity",
        description="选择将文件解析为markdown的引擎。如果输入文件是.md，此项可为`null`或不传。",
        examples=["identity", "mineru", "docling"]
    )
    mineru_token: Optional[str] = Field(None, description="当 `convert_engine` 为 'mineru' 时必填的API令牌。")
    formula_ocr: bool = Field(True, description="是否对公式进行OCR识别。对 `mineru` 和 `docling` 均有效。")
    code_ocr: bool = Field(True, description="是否对代码块进行OCR识别。仅 `docling` 引擎有效。")

    @field_validator('mineru_token')
    def check_mineru_token(cls, v, values):
        if values.data.get('convert_engine') == 'mineru' and not v:
            raise ValueError("当 `convert_engine` 为 'mineru' 时，`mineru_token` 字段是必须的。")
        return v


class TextWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal['txt'] = Field(..., description="指定使用纯文本的翻译工作流。")


class JsonWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal['json'] = Field(..., description="指定使用JSON的翻译工作流。")
    json_paths: List[str] = Field(
        ...,
        description="一个jsonpath-ng表达式列表，用于指定需要翻译的JSON字段。",
        examples=[["$..description", "$.items[0].name", "$.*"]]
    )


class XlsxWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal['xlsx'] = Field(..., description="指定使用XLSX的翻译工作流。")
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。"
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。"
    )


class DocxWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal['docx'] = Field(..., description="指定使用DOCX的翻译工作流。")
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。"
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。"
    )


class SrtWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal['srt'] = Field(..., description="指定使用SRT字幕的翻译工作流。")
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。"
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。"
    )


class EpubWorkflowParams(BaseWorkflowParams):
    workflow_type: Literal['epub'] = Field(..., description="指定使用EPUB的翻译工作流。")
    insert_mode: Literal["replace", "append", "prepend"] = Field(
        "replace",
        description="翻译文本的插入模式。'replace'：替换原文，'append'：附加到原文后，'prepend'：附加到原文前。"
    )
    separator: str = Field(
        "\n",
        description="当 insert_mode 为 'append' 或 'prepend' 时，用于分隔原文和译文的分隔符。"
    )


# 3. 使用可辨识联合类型（Discriminated Union）将它们组合起来
TranslatePayload = Annotated[
    Union[
        MarkdownWorkflowParams, TextWorkflowParams, JsonWorkflowParams, XlsxWorkflowParams, DocxWorkflowParams, SrtWorkflowParams, EpubWorkflowParams],
    Field(discriminator='workflow_type')
]


# 4. 创建最终的请求体模型
class TranslateServiceRequest(BaseModel):
    file_name: str = Field(..., description="上传的原始文件名，含扩展名。",
                           examples=["my_paper.pdf", "chapter1.txt", "data.xlsx", "video.srt", "my_book.epub"])
    file_content: str = Field(..., description="Base64编码的文件内容。", examples=["JVBERi0xLjQK..."])
    payload: TranslatePayload = Field(..., description="包含工作流类型和相应参数的载荷。")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "summary": "Markdown 工作流示例",
                    "value": {
                        "file_name": "annual_report_2023.pdf",
                        "file_content": "JVBERi0xLjcKJeLjz9MKMSAwIG9iago8PC9...",
                        "payload": {
                            "workflow_type": "markdown_based",
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "sk-your-api-key-here",
                            "model_id": "gpt-4o",
                            "to_lang": "简体中文",
                            "convert_engine": "mineru",
                            "mineru_token": "your-mineru-token-if-any",
                        }
                    }
                },
                {
                    "summary": "JSON 工作流示例",
                    "value": {
                        "file_name": "product_info.json",
                        "file_content": "ewogICAgImlkIjogIjEyMzQ1IiwK...",
                        "payload": {
                            "workflow_type": "json",
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "sk-your-api-key-here",
                            "model_id": "gpt-4o",
                            "to_lang": "日本語",
                            "json_paths": ["productName", "description.long", "features[*]"],
                        }
                    }
                },
                {
                    "summary": "XLSX 工作流示例",
                    "value": {
                        "file_name": "product_list.xlsx",
                        "file_content": "UEsDBBQAAAAIA... (base64-encoded xlsx)",
                        "payload": {
                            "workflow_type": "xlsx",
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "sk-your-api-key-here",
                            "model_id": "gpt-4o",
                            "to_lang": "简体中文",
                            "insert_mode": "append",
                            "separator": " \n---翻译---\n ",
                            "chunk_size": 2000,
                            "concurrent": 5
                        }
                    }
                },
                {
                    "summary": "DOCX 工作流示例",
                    "value": {
                        "file_name": "contract.docx",
                        "file_content": "UEsDBBQAAAAIA... (base64-encoded docx)",
                        "payload": {
                            "workflow_type": "docx",
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "sk-your-api-key-here",
                            "model_id": "gpt-4o",
                            "to_lang": "English",
                            "insert_mode": "replace",
                        }
                    }
                },
                {
                    "summary": "SRT 工作流示例",
                    "value": {
                        "file_name": "movie.srt",
                        "file_content": "MSAKMDA6MDA6MDEsMjAwIC0tPiAwMDowMD...",
                        "payload": {
                            "workflow_type": "srt",
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "sk-your-api-key-here",
                            "model_id": "gpt-4o",
                            "to_lang": "English",
                            "insert_mode": "replace",
                        }
                    }
                },
                {
                    "summary": "EPUB 工作流示例",
                    "value": {
                        "file_name": "my_book.epub",
                        "file_content": "UEsDBBQAAAAIA... (base64-encoded epub)",
                        "payload": {
                            "workflow_type": "epub",
                            "base_url": "https://api.openai.com/v1",
                            "api_key": "sk-your-api-key-here",
                            "model_id": "gpt-4o",
                            "to_lang": "简体中文",
                            "insert_mode": "replace",
                        }
                    }
                }
            ]
        }


# --- Background Task Logic ---
async def _perform_translation(
        task_id: str,
        payload: TranslatePayload,
        file_contents: bytes,
        original_filename: str
):
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

    task_logger.info(f"后台翻译任务开始: 文件 '{original_filename}', 工作流: '{payload.workflow_type}'")
    task_state["status_message"] = f"正在处理 '{original_filename}'..."

    try:
        # 1. 根据工作流类型选择合适的 Workflow Class
        workflow_class = WORKFLOW_DICT.get(payload.workflow_type)
        if not workflow_class:
            raise ValueError(f"不支持的工作流类型: '{payload.workflow_type}'")

        workflow: Workflow

        # 2. 根据 payload 的具体类型构建配置并实例化 workflow
        if isinstance(payload, MarkdownWorkflowParams):
            task_logger.info("构建 MarkdownBasedWorkflow 配置。")
            translator_config = MDTranslatorConfig(
                **payload.model_dump(include={
                    'base_url', 'api_key', 'model_id', 'to_lang', 'custom_prompt',
                    'temperature', 'thinking', 'chunk_size', 'concurrent'
                }, exclude_none=True)
            )
            converter_config = None
            if payload.convert_engine == 'mineru':
                converter_config = ConverterMineruConfig(logger=task_logger, mineru_token=payload.mineru_token,
                                                         formula_ocr=payload.formula_ocr)
            elif payload.convert_engine == 'docling' and DOCLING_EXIST:
                converter_config = ConverterDoclingConfig(logger=task_logger, code_ocr=payload.code_ocr,
                                                          formula_ocr=payload.formula_ocr)
            html_exporter_config = MD2HTMLExporterConfig(cdn=True)
            workflow_config = MarkdownBasedWorkflowConfig(
                convert_engine=payload.convert_engine, converter_config=converter_config,
                translator_config=translator_config, html_exporter_config=html_exporter_config,
                logger=task_logger
            )
            workflow = MarkdownBasedWorkflow(config=workflow_config)

        elif isinstance(payload, TextWorkflowParams):
            task_logger.info("构建 TXTWorkflow 配置。")
            translator_config = TXTTranslatorConfig(
                **payload.model_dump(include={
                    'base_url', 'api_key', 'model_id', 'to_lang', 'custom_prompt',
                    'temperature', 'thinking', 'chunk_size', 'concurrent'
                }, exclude_none=True)
            )
            html_exporter_config = TXT2HTMLExporterConfig(cdn=True)
            workflow_config = TXTWorkflowConfig(
                translator_config=translator_config, html_exporter_config=html_exporter_config,
                logger=task_logger
            )
            workflow = TXTWorkflow(config=workflow_config)

        elif isinstance(payload, JsonWorkflowParams):
            task_logger.info("构建 JsonWorkflow 配置。")
            translator_config = JsonTranslatorConfig(
                json_paths=payload.json_paths,
                **payload.model_dump(include={
                    'base_url', 'api_key', 'model_id', 'to_lang', 'custom_prompt',
                    'temperature', 'thinking', 'chunk_size', 'concurrent'
                }, exclude_none=True)
            )
            html_exporter_config = Json2HTMLExporterConfig(cdn=True)
            workflow_config = JsonWorkflowConfig(
                translator_config=translator_config, html_exporter_config=html_exporter_config,
                logger=task_logger
            )
            workflow = JsonWorkflow(config=workflow_config)

        elif isinstance(payload, XlsxWorkflowParams):
            task_logger.info("构建 XlsxWorkflow 配置。")
            translator_config = XlsxTranslatorConfig(
                **payload.model_dump(include={
                    'base_url', 'api_key', 'model_id', 'to_lang', 'custom_prompt',
                    'temperature', 'thinking', 'chunk_size', 'concurrent',
                    'insert_mode', 'separator'
                }, exclude_none=True)
            )
            html_exporter_config = Xlsx2HTMLExporterConfig(cdn=True)
            workflow_config = XlsxWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger
            )
            workflow = XlsxWorkflow(config=workflow_config)

        elif isinstance(payload, DocxWorkflowParams):
            task_logger.info("构建 DocxWorkflow 配置。")
            translator_config = DocxTranslatorConfig(
                **payload.model_dump(include={
                    'base_url', 'api_key', 'model_id', 'to_lang', 'custom_prompt',
                    'temperature', 'thinking', 'chunk_size', 'concurrent',
                    'insert_mode', 'separator'
                }, exclude_none=True)
            )
            html_exporter_config = Docx2HTMLExporterConfig(cdn=True)
            workflow_config = DocxWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger
            )
            workflow = DocxWorkflow(config=workflow_config)

        elif isinstance(payload, SrtWorkflowParams):
            task_logger.info("构建 SrtWorkflow 配置。")
            translator_config = SrtTranslatorConfig(
                **payload.model_dump(include={
                    'base_url', 'api_key', 'model_id', 'to_lang', 'custom_prompt',
                    'temperature', 'thinking', 'chunk_size', 'concurrent',
                    'insert_mode', 'separator'
                }, exclude_none=True)
            )
            html_exporter_config = Srt2HTMLExporterConfig(cdn=True)
            workflow_config = SrtWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger
            )
            workflow = SrtWorkflow(config=workflow_config)

        elif isinstance(payload, EpubWorkflowParams):
            task_logger.info("构建 EpubWorkflow 配置。")
            translator_config = EpubTranslatorConfig(
                **payload.model_dump(include={
                    'base_url', 'api_key', 'model_id', 'to_lang', 'custom_prompt',
                    'temperature', 'thinking', 'chunk_size', 'concurrent',
                    'insert_mode', 'separator'
                }, exclude_none=True)
            )
            html_exporter_config = Epub2HTMLExporterConfig(cdn=True)
            workflow_config = EpubWorkflowConfig(
                translator_config=translator_config,
                html_exporter_config=html_exporter_config,
                logger=task_logger
            )
            workflow = EpubWorkflow(config=workflow_config)

        else:
            raise TypeError(f"工作流类型 '{payload.workflow_type}' 的处理逻辑未实现。")

        # 3. 读取文件内容并执行翻译
        file_stem = Path(original_filename).stem
        file_suffix = Path(original_filename).suffix
        workflow.read_bytes(content=file_contents, stem=file_stem, suffix=file_suffix)
        await workflow.translate_async()

        # 4. 任务成功，存储 workflow 实例并更新状态
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        task_state.update({
            "workflow_instance": workflow,
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
            "status_message": f"翻译任务已取消 (用时 {duration:.2f} 秒).", "error_flag": False, "download_ready": False,
            "workflow_instance": None, "task_end_time": end_time,
        })
    except Exception as e:
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        error_message = f"翻译失败: {e}"
        task_logger.error(error_message, exc_info=True)
        task_state.update({
            "status_message": f"翻译过程中发生错误 (用时 {duration:.2f} 秒): {e}", "error_flag": True,
            "download_ready": False,
            "workflow_instance": None, "task_end_time": end_time,
        })
    finally:
        task_state["is_processing"] = False
        task_state["current_task_ref"] = None
        task_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")
        task_logger.removeHandler(task_handler)
        md_based_convert_cacher.clear()


# --- 核心任务启动逻辑 ---
async def _start_translation_task(
        task_id: str,
        payload: TranslatePayload,
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
        "workflow_instance": None,
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
        task = loop.create_task(_perform_translation(task_id, payload, file_contents, original_filename))
        task_state["current_task_ref"] = task
        return {"task_started": True, "task_id": task_id, "message": "翻译任务已成功启动，请稍候..."}
    except Exception as e:
        task_state.update({"is_processing": False, "status_message": f"启动任务失败: {e}", "error_flag": True,
                           "current_task_ref": None})
        raise HTTPException(status_code=500, detail=f"启动翻译任务时出错: {e}")


# --- 取消任务逻辑 ---
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


# ===================================================================
# --- Service Endpoints (/service) ---
# ===================================================================

@service_router.post(
    "/translate",
    summary="提交翻译任务 (统一入口)",
    description="""
接收一个包含文件内容（Base64编码）和工作流参数的JSON请求，启动一个后台翻译任务。

- **工作流选择**: 请求体中的 `payload.workflow_type` 字段决定了本次任务的类型（如 `markdown_based`, `txt`, `json`, `xlsx`, `docx`, `srt`, `epub`）。
- **动态参数**: 根据所选工作流，API需要不同的参数集。请参考下面的Schema或示例。
- **异步处理**: 此端点会立即返回任务ID，客户端需轮询状态接口获取进度。
""",
    responses={
        200: {
            "description": "翻译任务已成功启动。",
            "content": {"application/json": {
                "example": {"task_started": True, "task_id": "a1b2c3d4", "message": "翻译任务已成功启动，请稍候..."}}}
        },
        400: {"description": "请求体无效，例如Base64解码失败。"},
        429: {"description": "服务器已有一个同ID的任务在处理中（理论上不应发生，因为ID是新生成的）。"},
        500: {"description": "启动后台任务时发生未知错误。"},
    }
)
async def service_translate(request: TranslateServiceRequest = Body(..., description="翻译任务的详细参数和文件内容。")):
    task_id = uuid.uuid4().hex[:8]

    try:
        file_contents = base64.b64decode(request.file_content)
    except (binascii.Error, TypeError) as e:
        raise HTTPException(status_code=400, detail=f"无效的Base64文件内容: {e}")

    try:
        response_data = await _start_translation_task(
            task_id=task_id,
            payload=request.payload,
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
    description="""根据任务ID取消一个正在进行中的翻译任务。如果任务已经完成、失败或已经被取消，则会返回错误。"""
)
async def service_cancel_translate(task_id: str):
    return _cancel_translation_logic(task_id)


@service_router.post(
    "/release/{task_id}",
    summary="释放任务资源",
    description="""根据任务ID释放其在服务器上占用的所有资源，包括状态、日志和缓存的翻译结果。如果任务正在进行，会先尝试取消该任务。此操作不可逆。"""
)
async def service_release_task(task_id: str):
    if task_id not in tasks_state:
        return JSONResponse(status_code=404, content={"released": False, "message": f"找不到任务ID '{task_id}'。"})
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
    tasks_state.pop(task_id, None);
    tasks_log_queues.pop(task_id, None);
    tasks_log_histories.pop(task_id, None)
    print(f"[{task_id}] 资源已成功释放。")
    message_parts.append(f"任务 '{task_id}' 的资源已释放。")
    return JSONResponse(content={"released": True, "message": " ".join(message_parts)})


@service_router.get(
    "/status/{task_id}",
    summary="获取任务状态",
    description="根据任务ID获取任务的当前状态。当 `download_ready` 为 `true` 时，`downloads` 对象中会包含可用的下载链接。",
    responses={
        200: {
            "description": "成功获取任务状态。",
            "content": {
                "application/json": {
                    "examples": {
                        "processing": {
                            "summary": "进行中",
                            "value": {
                                "task_id": "a1b2c3d4", "is_processing": True,
                                "status_message": "正在处理 'annual_report.pdf'...",
                                "error_flag": False, "download_ready": False, "original_filename_stem": "annual_report",
                                "original_filename": "annual_report.pdf", "task_start_time": 1678889400.0,
                                "task_end_time": 0, "downloads": {}
                            }
                        },
                        "completed_markdown": {
                            "summary": "已完成 (Markdown)",
                            "value": {
                                "task_id": "b2865b93", "is_processing": False,
                                "status_message": "翻译成功！用时 123.45 秒。",
                                "error_flag": False, "download_ready": True, "original_filename_stem": "my_paper",
                                "original_filename": "my_paper.pdf", "task_start_time": 1678889400.123,
                                "task_end_time": 1678889523.573,
                                "downloads": {
                                    "html": "/service/download/b2865b93/html",
                                    "markdown": "/service/download/b2865b93/markdown",
                                    "markdown_zip": "/service/download/b2865b93/markdown_zip"
                                }
                            }
                        },
                        "completed_docx": {
                            "summary": "已完成 (DOCX)",
                            "value": {
                                "task_id": "f8a9c1b2", "is_processing": False,
                                "status_message": "翻译成功！用时 25.10 秒。",
                                "error_flag": False, "download_ready": True, "original_filename_stem": "contract",
                                "original_filename": "contract.docx", "task_start_time": 1678889500.123,
                                "task_end_time": 1678889525.223,
                                "downloads": {
                                    "docx": "/service/download/f8a9c1b2/docx",
                                    "html": "/service/download/f8a9c1b2/html"
                                }
                            }
                        },
                        "completed_epub": {
                            "summary": "已完成 (EPUB)",
                            "value": {
                                "task_id": "e9b8d7c6", "is_processing": False,
                                "status_message": "翻译成功！用时 45.32 秒。",
                                "error_flag": False, "download_ready": True, "original_filename_stem": "my_book",
                                "original_filename": "my_book.epub", "task_start_time": 1678890000.0,
                                "task_end_time": 1678890045.32,
                                "downloads": {
                                    "epub": "/service/download/e9b8d7c6/epub",
                                    "html": "/service/download/e9b8d7c6/html"
                                }
                            }
                        },
                        "error": {
                            "summary": "失败",
                            "value": {
                                "task_id": "c3d4e5f6", "is_processing": False,
                                "status_message": "翻译过程中发生错误: LLM API key is invalid",
                                "error_flag": True, "download_ready": False, "original_filename_stem": "bad_config",
                                "original_filename": "bad_config.json", "task_start_time": 1678889600.0,
                                "task_end_time": 1678889610.0, "downloads": {}
                            }
                        }
                    }
                }
            }
        },
        404: {"description": "指定的任务ID不存在。"},
    }
)
async def service_get_status(
        task_id: str = FastApiPath(..., description="要查询状态的任务的ID", examples=["b2865b93"])):
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    downloads = {}
    if task_state.get("download_ready") and task_state.get("workflow_instance"):
        workflow = task_state["workflow_instance"]
        if isinstance(workflow, HTMLExportable):
            downloads["html"] = f"/service/download/{task_id}/html"
        if isinstance(workflow, MDFormatsExportable):
            downloads["markdown"] = f"/service/download/{task_id}/markdown"
            downloads["markdown_zip"] = f"/service/download/{task_id}/markdown_zip"
        if isinstance(workflow, TXTExportable):
            downloads["txt"] = f"/service/download/{task_id}/txt"
        if isinstance(workflow, JsonExportable):
            downloads["json"] = f"/service/download/{task_id}/json"
        if isinstance(workflow, XlsxExportable):
            downloads["xlsx"] = f"/service/download/{task_id}/xlsx"
        if isinstance(workflow, DocxExportable):
            downloads["docx"] = f"/service/download/{task_id}/docx"
        if isinstance(workflow, SrtExportable):
            downloads["srt"] = f"/service/download/{task_id}/srt"
        if isinstance(workflow, EpubExportable):
            downloads["epub"] = f"/service/download/{task_id}/epub"

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
    description="""以流式方式获取任务的增量日志。客户端每次调用此接口，都会返回自上次调用以来产生的新日志行。这对于实时展示翻译进度非常有用。如果任务ID不存在，则返回404。"""
)
async def service_get_logs(task_id: str):
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


FileType = Literal["markdown", "markdown_zip", "html", "txt", "json", "xlsx", "docx", "srt", "epub"]


async def _get_content_from_workflow(task_id: str, file_type: FileType) -> tuple[bytes, str, str]:
    """辅助函数，从 workflow 获取内容、媒体类型和文件名"""
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")
    if not task_state.get("download_ready") or not task_state.get("workflow_instance"):
        raise HTTPException(status_code=404, detail="内容尚未准备好。")

    workflow: Workflow = task_state["workflow_instance"]
    filename_stem = task_state['original_filename_stem']

    try:
        content_bytes: bytes
        media_type: str
        filename: str

        html_config = None
        if file_type == 'html':
            is_cdn_available = True
            try:
                await httpx_client.head("https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js",
                                        timeout=3)
            except (httpx.TimeoutException, httpx.RequestError):
                is_cdn_available = False
                workflow.config.logger.warning("CDN连接失败，将使用本地JS进行渲染。")

            if isinstance(workflow, MarkdownBasedWorkflow):
                html_config = MD2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, TXTWorkflow):
                html_config = TXT2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, JsonWorkflow):
                html_config = Json2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, XlsxWorkflow):
                html_config = Xlsx2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, DocxWorkflow):
                html_config = Docx2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, SrtWorkflow):
                html_config = Srt2HTMLExporterConfig(cdn=is_cdn_available)
            elif isinstance(workflow, EpubWorkflow):
                html_config = Epub2HTMLExporterConfig(cdn=is_cdn_available)

        if file_type == 'html' and isinstance(workflow, HTMLExportable):
            content_str = await asyncio.to_thread(workflow.export_to_html, html_config)
            content_bytes, media_type, filename = content_str.encode(
                'utf-8'), "text/html; charset=utf-8", f"{filename_stem}_translated.html"
        elif file_type == 'markdown' and isinstance(workflow, MDFormatsExportable):
            md_content = workflow.export_to_markdown()
            content_bytes, media_type, filename = md_content.encode(
                'utf-8'), "text/markdown; charset=utf-8", f"{filename_stem}_translated.md"
        elif file_type == 'markdown_zip' and isinstance(workflow, MDFormatsExportable):
            content_bytes, media_type, filename = await asyncio.to_thread(
                workflow.export_to_markdown_zip), "application/zip", f"{filename_stem}_translated.zip"
        elif file_type == 'txt' and isinstance(workflow, TXTExportable):
            txt_content = await asyncio.to_thread(workflow.export_to_txt)
            content_bytes, media_type, filename = txt_content.encode(
                'utf-8'), "text/plain; charset=utf-8", f"{filename_stem}_translated.txt"
        elif file_type == 'json' and isinstance(workflow, JsonExportable):
            json_content = await asyncio.to_thread(workflow.export_to_json)
            content_bytes, media_type, filename = json_content.encode(
                'utf-8'), "application/json; charset=utf-8", f"{filename_stem}_translated.json"
        elif file_type == 'xlsx' and isinstance(workflow, XlsxExportable):
            content_bytes = await asyncio.to_thread(workflow.export_to_xlsx)
            media_type, filename = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", f"{filename_stem}_translated.xlsx"
        elif file_type == 'docx' and isinstance(workflow, DocxExportable):
            content_bytes = await asyncio.to_thread(workflow.export_to_docx)
            media_type, filename = "application/vnd.openxmlformats-officedocument.wordprocessingml.document", f"{filename_stem}_translated.docx"
        elif file_type == 'srt' and isinstance(workflow, SrtExportable):
            content_str = await asyncio.to_thread(workflow.export_to_srt)
            content_bytes, media_type, filename = content_str.encode(
                'utf-8'), "text/plain; charset=utf-8", f"{filename_stem}_translated.srt"
        elif file_type == 'epub' and isinstance(workflow, EpubExportable):
            content_bytes = await asyncio.to_thread(workflow.export_to_epub)
            media_type, filename = "application/epub+zip", f"{filename_stem}_translated.epub"
        else:
            raise HTTPException(status_code=404, detail=f"此任务不支持导出 '{file_type}' 类型的文件。")

        return content_bytes, media_type, filename
    except Exception as e:
        workflow.config.logger.error(f"导出 {file_type} 时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"导出 {file_type} 时发生内部错误: {e}")


@service_router.get(
    "/download/{task_id}/{file_type}",
    summary="下载翻译结果文件",
    responses={
        200: {
            "description": "成功返回文件流。文件名通过 Content-Disposition 头指定。",
            "content": {
                "text/html; charset=utf-8": {"schema": {"type": "string"}},
                "text/markdown; charset=utf-8": {"schema": {"type": "string"}},
                "text/plain; charset=utf-8": {"schema": {"type": "string"}},
                "application/zip": {"schema": {"type": "string", "format": "binary"}},
                "application/json": {"schema": {"type": "string", "format": "binary"}},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {
                    "schema": {"type": "string", "format": "binary"}},
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                    "schema": {"type": "string", "format": "binary"}},
                "application/epub+zip": {
                    "schema": {"type": "string", "format": "binary"}},
            }
        },
        404: {"description": "任务ID不存在，或该任务不支持所请求的文件类型。"},
        500: {"description": "在服务器上生成文件时发生内部错误。"}
    }
)
async def service_download_file(
        task_id: str = FastApiPath(..., description="已完成任务的ID", examples=["b2865b93"]),
        file_type: FileType = FastApiPath(..., description="要下载的文件类型。",
                                          examples=["html", "json", "docx", "srt", "epub"])
):
    content, media_type, filename = await _get_content_from_workflow(task_id, file_type)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename, safe='', encoding='utf-8')}"}
    return StreamingResponse(io.BytesIO(content), media_type=media_type, headers=headers)


@service_router.get(
    "/content/{task_id}/{file_type}",
    summary="下载翻译结果内容 (JSON)",
    description="""
以JSON格式获取指定文件类型的内容，而不是直接下载文件。

- **返回结构**: 返回一个JSON对象，包含文件名、文件类型和文件内容的Base64编码字符串。
- **内容编码**: 文件内容总是以 **Base64** 编码，客户端需要自行解码才能使用。
""",
    responses={
        200: {
            "description": "成功返回文件内容。",
            "content": {"application/json": {"examples": {
                "html_base64": {
                    "summary": "HTML 内容 (Base64)",
                    "value": {
                        "file_type": "html",
                        "filename": "my_doc_translated.html",
                        "content": "PGh0bWw+PGhlYWQ+..."
                    }
                },
                "docx_base64": {
                    "summary": "DOCX 内容 (Base64)",
                    "value": {
                        "file_type": "docx",
                        "filename": "my_doc_translated.docx",
                        "content": "UEsDBBQAAAAIA... (base64-encoded string)"
                    }
                },
                "epub_base64": {
                    "summary": "EPUB 内容 (Base64)",
                    "value": {
                        "file_type": "epub",
                        "filename": "my_book_translated.epub",
                        "content": "UEsDBBQAAAAIA... (base64-encoded string)"
                    }
                }
            }}}
        },
        404: {"description": "任务ID不存在，或该任务不支持所请求的文件类型。"},
        500: {"description": "在服务器上生成文件时发生内部错误。"}
    }
)
async def service_content(
        task_id: str = FastApiPath(..., description="已完成任务的ID", examples=["b2865b93"]),
        file_type: FileType = FastApiPath(..., description="要获取内容的文件类型。",
                                          examples=["html", "json", "docx", "srt", "epub"])
):
    content, _, filename = await _get_content_from_workflow(task_id, file_type)

    final_content = base64.b64encode(content).decode('utf-8')

    return JSONResponse(content={
        "file_type": file_type,
        "filename": filename,
        "content": final_content
    })


# ===================================================================
# --- 应用主路由和启动 ---
# ===================================================================
@service_router.get("/engin-list", tags=["Application"], description="返回正在进行的可用的转换引擎")
async def service_get_engin_list():
    engin_list = ["mineru"]
    if DOCLING_EXIST: engin_list.append("docling")
    return JSONResponse(content=engin_list)


@service_router.get("/task-list", tags=["Application"], description="返回正在进行的task_id列表")
async def service_get_task_list(): return JSONResponse(content=list(tasks_state.keys()))


@service_router.get("/default-params", tags=["Application"], description="返回一些默认参数")
def service_get_default_params(): return JSONResponse(content=default_params)


@service_router.get("/meta", tags=["Application"], description="返回软件版本号")
async def service_get_app_version(): return JSONResponse(content={"version": __version__})


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def main_page():
    index_path = Path(STATIC_DIR) / "index.html"
    if not index_path.exists(): raise HTTPException(status_code=404, detail="index.html not found")
    no_cache_headers = {"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache",
                        "Expires": "0"}
    return FileResponse(index_path, headers=no_cache_headers)

@app.get("/EN", response_class=HTMLResponse, include_in_schema=False)
async def main_page_EN():
    index_path = Path(STATIC_DIR) / "index_EN.html"
    if not index_path.exists(): raise HTTPException(status_code=404, detail="index_EN.html not found")
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


@app.post("/temp/translate", tags=["Temp"])
async def temp_translate(
        base_url: str = Body(...), api_key: str = Body(...), model_id: str = Body(...),
        mineru_token: Optional[str] = Body(None), file_name: str = Body(...), file_content: str = Body(...),
        to_lang: str = Body("中文"), concurrent: int = Body(default_params["concurrent"]),
        temperature: float = Body(default_params["temperature"]),
        thinking: ThinkingMode = Body(default_params["thinking"]),
        chunk_size: int = Body(default_params["chunk_size"]), custom_prompt: Optional[str] = Body(None),
):
    file_name = Path(file_name)
    try:
        decoded_content = base64.b64decode(file_content)
    except (ValueError, binascii.Error):
        decoded_content = file_content.encode('utf-8')
    try:
        workflow_config = MarkdownBasedWorkflowConfig(
            convert_engine="mineru", converter_config=ConverterMineruConfig(mineru_token=mineru_token),
            translator_config=MDTranslatorConfig(base_url=base_url, api_key=api_key, model_id=model_id,
                                                 to_lang=to_lang, custom_prompt=custom_prompt, temperature=temperature,
                                                 thinking=thinking, chunk_size=chunk_size, concurrent=concurrent),
            html_exporter_config=MD2HTMLExporterConfig()
        )
        workflow = MarkdownBasedWorkflow(workflow_config)
        workflow.read_bytes(content=decoded_content, stem=file_name.stem, suffix=file_name.suffix)
        await workflow.translate_async()
        return {"success": True, "content": workflow.export_to_markdown()}
    except Exception as e:
        global_logger.error(f"临时翻译接口出现错误：{e.__repr__()}", exc_info=True)
        return {"success": False, "reason": e.__repr__()}


app.include_router(service_router)


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
        uvicorn.run(app, host=None, port=port_to_use, workers=1)
    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    run_app()
