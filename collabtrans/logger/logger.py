# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from collabtrans.config.global_config import get_global_config


def get_log_level_from_config():
    """从配置文件获取日志级别"""
    try:
        config = get_global_config()
        level_str = config.logging.level.upper()
        return getattr(logging, level_str, logging.INFO)
    except Exception:
        return logging.INFO


# 创建日志对象
global_logger = logging.getLogger("TranslaterLogger")
global_logger.setLevel(get_log_level_from_config())

# 统一日志格式
_formatter = logging.Formatter(
    fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

# 输出到控制台
console_handler = logging.StreamHandler()
console_handler.setFormatter(_formatter)

# 输出到文件（按天切割，保留7天），日志目录位于仓库根目录 logs/
try:
    proj_root = Path(__file__).resolve().parents[2]
    logs_dir = proj_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"

    file_handler = TimedRotatingFileHandler(
        filename=str(log_file),
        when="midnight",
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(_formatter)
except Exception:
    # 若文件处理器初始化失败，仅保留控制台输出，避免影响主流程
    file_handler = None

# 防重复添加 handler（例如在热重载场景下）
existing = {type(h).__name__ for h in global_logger.handlers}
if 'StreamHandler' not in existing:
    global_logger.addHandler(console_handler)
if file_handler and 'TimedRotatingFileHandler' not in existing:
    global_logger.addHandler(file_handler)

# 同步到 root logger，让各模块通过 logging.getLogger(__name__) 获取的记录器也写入文件
root_logger = logging.getLogger()
# 从配置文件设置根日志级别
config_log_level = get_log_level_from_config()
if root_logger.level > config_log_level or root_logger.level == logging.NOTSET:
    root_logger.setLevel(config_log_level)
root_existing = {type(h).__name__ for h in root_logger.handlers}
if 'StreamHandler' not in root_existing:
    root_ch = logging.StreamHandler()
    root_ch.setFormatter(_formatter)
    root_logger.addHandler(root_ch)
if file_handler and 'TimedRotatingFileHandler' not in root_existing:
    root_logger.addHandler(file_handler)