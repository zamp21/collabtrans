# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""
Process memory usage helpers for debug logging.
Use at key steps (e.g. after load, after each chunk) to find memory hotspots.
"""
import logging
import os
import resource
import sys

try:
    import psutil
    _PSUTIL = True
except ImportError:
    _PSUTIL = False


def get_process_memory_mb() -> float:
    """
    Return current process resident set size (RSS) in MB.
    Uses psutil if available (current RSS), else resource.getrusage (max RSS so far).
    """
    if _PSUTIL:
        try:
            return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
        except Exception:
            pass
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF)
        rss = usage.ru_maxrss
        if sys.platform == "darwin":
            return rss / (1024 * 1024)
        return rss / 1024
    except Exception:
        return 0.0


def log_memory(logger: logging.Logger, step_name: str, extra: str = "") -> None:
    """Log current process memory (MB) at INFO level. Step name and optional extra text."""
    if not logger.isEnabledFor(logging.INFO):
        return
    mb = get_process_memory_mb()
    msg = f"[Memory] {step_name}: {mb:.1f} MB"
    if extra:
        msg += f" ({extra})"
    logger.info(msg)
