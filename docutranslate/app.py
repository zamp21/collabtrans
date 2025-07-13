import asyncio
import io
import logging
import os
import socket
import time
from contextlib import asynccontextmanager, closing
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import quote

import httpx
import uvicorn
from fastapi import FastAPI, File, Form, UploadFile, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from docutranslate import FileTranslater, __version__
from docutranslate.logger import translater_logger
from docutranslate.translater import default_params
from docutranslate.utils.resource_utils import resource_path
from docutranslate.global_values import available_packages

httpx_client = httpx.AsyncClient()

# --- 全局配置 (修改) ---
# 将单个状态变更为一个字典，以task_id为键，管理多个任务的状态
tasks_state: Dict[str, Dict[str, Any]] = {}
# 将单个日志队列变更为字典，为每个task_id提供独立的日志队列
tasks_log_queues: Dict[str, asyncio.Queue] = {}
# 将单个日志历史变更为字典，为每个task_id提供独立的日志历史
tasks_log_histories: Dict[str, List[str]] = {}

MAX_LOG_HISTORY = 200


# --- 辅助函数：创建默认任务状态 (新增) ---
def _create_default_task_state() -> Dict[str, Any]:
    """创建一个新的、默认的任务状态字典。"""
    return {
        "is_processing": False,
        "status_message": "空闲",
        "error_flag": False,
        "download_ready": False,
        "markdown_content": None,
        "markdown_zip_content": None,
        "html_content": None,
        "original_filename_stem": None,
        "task_start_time": 0,
        "task_end_time": 0,
        "current_task_ref": None,
    }


# --- 日志处理器 (基本无修改，但其使用方式已改变) ---
class QueueAndHistoryHandler(logging.Handler):
    def __init__(self, queue_ref: asyncio.Queue, history_list_ref: List[str], max_history_items: int):
        super().__init__()
        self.queue = queue_ref
        self.history_list = history_list_ref
        self.max_history = max_history_items

    def emit(self, record: logging.LogRecord):
        log_entry = self.format(record)
        print(f"[{record.task_id}] {log_entry}" if hasattr(record, 'task_id') else log_entry)  # 控制台日志增加task_id
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


# --- 应用生命周期事件 (修改) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.main_event_loop = asyncio.get_running_loop()

    # 清空所有旧的任务状态，确保重启后是干净的
    tasks_state.clear()
    tasks_log_queues.clear()
    tasks_log_histories.clear()

    # 移除所有旧的处理器，因为处理器现在是按任务动态添加的
    for handler in translater_logger.handlers[:]:
        translater_logger.removeHandler(handler)

    translater_logger.propagate = False
    translater_logger.setLevel(logging.INFO)

    print("应用启动完成，多任务状态已初始化。")
    yield


app = FastAPI(lifespan=lifespan)

STATIC_DIR = resource_path("static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Background Task Logic (修改) ---
async def _perform_translation(task_id: str, params: Dict[str, Any], file_contents: bytes, original_filename: str):
    """后台翻译任务，现在接收 task_id 以便操作对应的状态和日志。"""
    task_state = tasks_state[task_id]
    log_queue = tasks_log_queues[task_id]
    log_history = tasks_log_histories[task_id]

    # 为当前任务动态创建并添加日志处理器
    task_handler = QueueAndHistoryHandler(log_queue, log_history, MAX_LOG_HISTORY)
    task_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    # 为日志记录添加task_id上下文，方便区分
    log_filter = logging.Filter()
    log_filter.task_id = task_id
    task_handler.addFilter(log_filter)

    translater_logger.addHandler(task_handler)

    translater_logger.info(f"后台翻译任务开始: 文件 '{original_filename}'")
    task_state["status_message"] = f"正在处理 '{original_filename}'..."

    try:
        translater_logger.info(f"使用 Base URL: {params['base_url']}, Model: {params['model_id']}")
        # ... (其余日志记录)

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
        except (httpx.TimeoutException, httpx.RequestError) as e:
            translater_logger.info(f"连接s4.zstatic.net失败，错误信息：{e}")
            translater_logger.info("使用本地js进行pdf渲染")
            html_content = ft.export_to_html(title=task_state["original_filename_stem"], cdn=False)

        end_time = time.time()
        duration = end_time - task_state["task_start_time"]

        task_state.update({
            "markdown_content": md_content,
            "markdown_zip_content": md_zip_content,
            "html_content": html_content,
            "status_message": f"翻译成功！用时 {duration:.2f} 秒。",
            "download_ready": True, "error_flag": False, "task_end_time": end_time,
        })
        translater_logger.info(f"翻译成功完成，用时 {duration:.2f} 秒。")

    except asyncio.CancelledError:
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        translater_logger.info(f"翻译任务 '{original_filename}' 已被取消 (用时 {duration:.2f} 秒).")
        task_state.update({
            "status_message": f"翻译任务已取消（若有转换任务仍会后台进行） (用时 {duration:.2f} 秒).",
            "error_flag": False, "download_ready": False,
            "markdown_content": None, "md_zip_content": None, "html_content": None,
            "task_end_time": end_time,
        })
    except Exception as e:
        end_time = time.time()
        duration = end_time - task_state["task_start_time"]
        error_message = f"翻译失败: {e}"
        translater_logger.error(error_message, exc_info=True)
        task_state.update({
            "status_message": f"翻译过程中发生错误 (用时 {duration:.2f} 秒): {e}",
            "error_flag": True, "download_ready": False,
            "markdown_content": None, "md_zip_content": None, "html_content": None,
            "task_end_time": end_time,
        })
    finally:
        # 任务结束，重置处理状态并移除任务引用
        task_state["is_processing"] = False
        task_state["current_task_ref"] = None
        translater_logger.info(f"后台翻译任务 '{original_filename}' 处理结束。")
        # 关键步骤：移除此任务的处理器，防止日志系统混乱
        translater_logger.removeHandler(task_handler)


# --- API Endpoints ---
@app.get("/", response_class=HTMLResponse)
async def main_page(request: Request):
    index_path = Path("index.html")
    if not index_path.exists():
        index_path = STATIC_DIR / "index.html"
        if not index_path.exists():
            raise HTTPException(status_code=404, detail="index.html not found")
    no_cache_headers = {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache", "Expires": "0",
    }
    return FileResponse(index_path, headers=no_cache_headers)


@app.post("/translate")
async def handle_translate(
        # 添加 task_id 参数，默认为 '0'
        task_id: str = Form("0"),
        base_url: str = Form(...), apikey: str = Form(...), model_id: str = Form(...),
        to_lang: str = Form("中文"), formula_ocr: bool = Form(False), code_ocr: bool = Form(False),
        refine_markdown: bool = Form(False), convert_engin: str = Form(...),
        mineru_token: Optional[str] = Form(None), chunk_size: int = Form(...),
        concurrent: int = Form(...), temperature: float = Form(...),
        custom_prompt_translate: Optional[str] = Form(None),
        file: UploadFile = File(...)
):
    # 获取或创建当前 task_id 的状态
    if task_id not in tasks_state:
        tasks_state[task_id] = _create_default_task_state()
        tasks_log_queues[task_id] = asyncio.Queue()
        tasks_log_histories[task_id] = []
    task_state = tasks_state[task_id]

    if task_state["is_processing"] and task_state["current_task_ref"] and not task_state["current_task_ref"].done():
        return JSONResponse(
            status_code=429,
            content={"task_started": False, "message": f"任务ID '{task_id}' 正在进行中，请稍后再试。"}
        )

    task_state["is_processing"] = True
    original_filename_for_init = file.filename or "uploaded_file"

    # 更新特定 task_id 的状态
    task_state.update({
        "status_message": "任务初始化中...", "error_flag": False, "download_ready": False,
        "markdown_content": None, "md_zip_content": None, "html_content": None,
        "original_filename_stem": Path(original_filename_for_init).stem,
        "task_start_time": time.time(), "task_end_time": 0, "current_task_ref": None,
    })

    # 清空特定 task_id 的日志历史和队列
    log_history = tasks_log_histories[task_id]
    log_queue = tasks_log_queues[task_id]
    log_history.clear()
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except asyncio.QueueEmpty:
            break

    initial_log_msg = f"收到新的翻译请求: {original_filename_for_init}"
    print(f"[{task_id}] {initial_log_msg}")  # 控制台直接打印
    log_history.append(initial_log_msg)
    await log_queue.put(initial_log_msg)

    try:
        file_contents = await file.read()
        original_filename = file.filename
        await file.close()

        task_params = {
            "base_url": base_url, "apikey": apikey, "model_id": model_id,
            "to_lang": to_lang, "formula_ocr": formula_ocr, "code_ocr": code_ocr,
            "refine_markdown": refine_markdown, "convert_engin": convert_engin,
            "mineru_token": mineru_token, "chunk_size": chunk_size, "concurrent": concurrent,
            "temperature": temperature, "custom_prompt_translate": custom_prompt_translate,
        }

        loop = asyncio.get_running_loop()
        # 将 task_id 传递给后台任务
        task = loop.create_task(
            _perform_translation(task_id, task_params, file_contents, original_filename)
        )
        task_state["current_task_ref"] = task

        return JSONResponse(
            content={"task_started": True, "task_id": task_id, "message": "翻译任务已成功启动，请稍候..."})
    except Exception as e:
        task_state["is_processing"] = False
        task_state["status_message"] = f"启动任务失败: {e}"
        task_state["error_flag"] = True
        task_state["current_task_ref"] = None
        return JSONResponse(status_code=500,
                            content={"task_started": False, "task_id": task_id, "message": f"启动翻译任务时出错: {e}"})


@app.post("/cancel-translate")
async def cancel_translate_task(task_id: str = Form("0")):  # 使用Form以匹配POST请求
    task_state = tasks_state.get(task_id)
    if not task_state or not task_state["is_processing"] or not task_state["current_task_ref"]:
        return JSONResponse(
            status_code=400,
            content={"cancelled": False, "message": f"任务ID '{task_id}' 没有正在进行的翻译任务可取消。"}
        )

    task_to_cancel: Optional[asyncio.Task] = task_state["current_task_ref"]

    if not task_to_cancel or task_to_cancel.done():
        task_state["is_processing"] = False
        task_state["current_task_ref"] = None
        return JSONResponse(
            status_code=400,
            content={"cancelled": False, "message": "任务已完成或已被取消。"}
        )

    print(f"[{task_id}] 收到取消翻译任务的请求。")
    task_to_cancel.cancel()
    task_state["status_message"] = "正在取消任务..."

    return JSONResponse(content={"cancelled": True, "message": "取消请求已发送。请等待状态更新。"})


@app.get("/get-engin-list")
async def get_engin_list():
    engin_list = ["mineru"]
    if available_packages.get("docling"):
        engin_list.append("docling")
    return JSONResponse(content=engin_list)


@app.get("/get-status")
async def get_status(task_id: str = Query("0")):
    task_state = tasks_state.get(task_id)
    if not task_state:
        # 如果task_id不存在，返回一个默认的空闲状态
        task_state = _create_default_task_state()

    # 在URL中附带task_id，以便下载和后续请求能找到正确的任务
    def generate_url(path_prefix, filename_stem, extension):
        if task_state["download_ready"] and filename_stem:
            return f"/download/{path_prefix}/{filename_stem}_translated.{extension}?task_id={task_id}"
        return None

    status_data = {
        "is_processing": task_state["is_processing"],
        "status_message": task_state["status_message"],
        "error_flag": task_state["error_flag"],
        "download_ready": task_state["download_ready"],
        "original_filename_stem": task_state["original_filename_stem"],
        "markdown_url": generate_url("markdown", task_state["original_filename_stem"], "md"),
        "markdown_zip_url": generate_url("markdown_zip", task_state["original_filename_stem"], "zip"),
        "html_url": generate_url("html", task_state["original_filename_stem"], "html"),
        "task_start_time": task_state["task_start_time"],
        "task_end_time": task_state["task_end_time"],
    }
    return JSONResponse(content=status_data)


@app.get("/get-logs")
async def get_logs_from_queue(task_id: str = Query("0")):
    log_queue = tasks_log_queues.get(task_id)
    new_logs = []
    if log_queue:
        while not log_queue.empty():
            try:
                log_entry = log_queue.get_nowait()
                new_logs.append(log_entry)
                log_queue.task_done()
            except asyncio.QueueEmpty:
                break
    return JSONResponse(content={"logs": new_logs})


@app.get("/download/{file_type}/{filename_with_ext}")
async def download_file(
        file_type: str,
        filename_with_ext: str,
        task_id: str = Query(...)  # task_id 在下载时是必需的
):
    task_state = tasks_state.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail=f"找不到任务ID '{task_id}'。")

    if not task_state["download_ready"] or not task_state["original_filename_stem"]:
        raise HTTPException(status_code=404, detail="内容尚未准备好或不可用。")

    if Path(filename_with_ext).stem != f"{task_state['original_filename_stem']}_translated":
        raise HTTPException(status_code=404, detail="请求的文件名与当前结果不符。")

    content_map = {
        "markdown": (task_state["markdown_content"], "text/markdown",
                     f"{task_state['original_filename_stem']}_translated.md"),
        "markdown_zip": (task_state["markdown_zip_content"], "application/zip",
                         f"{task_state['original_filename_stem']}_translated.zip"),
        "html": (task_state["html_content"], "text/html", f"{task_state['original_filename_stem']}_translated.html"),
    }

    if file_type not in content_map:
        raise HTTPException(status_code=404, detail="无效的文件类型。")

    content, media_type, actual_filename = content_map[file_type]

    if content is None:
        raise HTTPException(status_code=404, detail=f"{file_type.capitalize()} 内容不可用。")

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(actual_filename, safe='', encoding='utf-8')}"}

    if file_type == "html":
        return HTMLResponse(content=content, media_type=media_type, headers=headers)
    elif file_type == "markdown_zip":
        return StreamingResponse(io.BytesIO(content), media_type=media_type, headers=headers)
    else:  # markdown
        return StreamingResponse(io.StringIO(content), media_type=media_type, headers=headers)


@app.get("/translate/default_param")
def get_default_param():
    return JSONResponse(content=default_params)


@app.get("/meta")
async def get_app_version():
    return JSONResponse(content={"version": __version__})


def find_free_port(start_port):
    port = start_port
    while True:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            if sock.connect_ex(('127.0.0.1', port)) != 0:
                return port
            port += 1


def run_app(port: int | None = None):
    if port:
        initial_port = port
    else:
        env_port = os.environ.get("DOCUTRANSLATE_PORT")
        initial_port = int(env_port) if env_port else 8010
    try:
        port = find_free_port(initial_port)
        if port != initial_port:
            print(f"端口 {initial_port} 被占用，将使用端口 {port} 代替")
        print(f"正在启动 DocuTranslate WebUI 版本号：{__version__}")
        print(f"请用浏览器访问 http://127.0.0.1:{port} (部分终端可以使用ctrl+左键点击网址打开)")
        print(f"可以设置环境变量`DOCUTRANSLATE_PORT=<port>`改变默认服务端口号")
        uvicorn.run(app, host=None, port=port, workers=1)
    except Exception as e:
        print(f"启动失败: {e}")


if __name__ == "__main__":
    run_app()