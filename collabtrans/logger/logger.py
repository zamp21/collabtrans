# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from collabtrans.config.global_config import get_global_config


def get_log_level_from_config():
    """Get log level from configuration file"""
    try:
        config = get_global_config()
        level_str = config.logging.level.upper()
        return getattr(logging, level_str, logging.INFO)
    except Exception:
        return logging.INFO


# Create logger object
global_logger = logging.getLogger("TranslaterLogger")
global_logger.setLevel(get_log_level_from_config())

# Unified log format
_formatter = logging.Formatter(
    fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

# Output to console
console_handler = logging.StreamHandler()
console_handler.setFormatter(_formatter)

# Output to file (daily rotation, keep 7 days), log directory is in project root logs/
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
    # If file handler initialization fails, keep only console output to avoid affecting main process
    file_handler = None

# Prevent duplicate handler addition (e.g., in hot reload scenarios)
existing = {type(h).__name__ for h in global_logger.handlers}
if 'StreamHandler' not in existing:
    global_logger.addHandler(console_handler)
if file_handler and 'TimedRotatingFileHandler' not in existing:
    global_logger.addHandler(file_handler)

# Sync to root logger, so loggers obtained by modules through logging.getLogger(__name__) also write to file
root_logger = logging.getLogger()
# Set root log level from configuration file
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