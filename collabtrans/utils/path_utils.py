# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import platform
from pathlib import Path
from typing import Dict, Optional


def get_system_data_dir() -> str:
    """Get system-appropriate data directory for CollabTrans
    
    Returns:
        str: Platform-specific data directory path
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: Use %APPDATA%\CollabTrans
        return os.path.join(os.environ.get("APPDATA", ""), "CollabTrans")
    elif system == "darwin":  # macOS
        # macOS: Use ~/Library/Application Support/CollabTrans
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "CollabTrans")
    else:  # Linux and others
        # Linux: Use ~/.local/share/collabtrans (following XDG Base Directory)
        xdg_data_home = os.environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return os.path.join(xdg_data_home, "collabtrans")
        else:
            return os.path.join(os.path.expanduser("~"), ".local", "share", "collabtrans")


def get_system_config_dir() -> str:
    """Get system-appropriate config directory for CollabTrans
    
    Returns:
        str: Platform-specific config directory path
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: Use %APPDATA%\CollabTrans\config
        return os.path.join(get_system_data_dir(), "config")
    elif system == "darwin":  # macOS
        # macOS: Use ~/Library/Application Support/CollabTrans/config
        return os.path.join(get_system_data_dir(), "config")
    else:  # Linux and others
        # Linux: Use ~/.config/collabtrans (following XDG Base Directory)
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return os.path.join(xdg_config_home, "collabtrans")
        else:
            return os.path.join(os.path.expanduser("~"), ".config", "collabtrans")


def get_system_cache_dir() -> str:
    """Get system-appropriate cache directory for CollabTrans
    
    Returns:
        str: Platform-specific cache directory path
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: Use %LOCALAPPDATA%\CollabTrans\cache
        return os.path.join(os.environ.get("LOCALAPPDATA", ""), "CollabTrans", "cache")
    elif system == "darwin":  # macOS
        # macOS: Use ~/Library/Caches/CollabTrans
        return os.path.join(os.path.expanduser("~"), "Library", "Caches", "CollabTrans")
    else:  # Linux and others
        # Linux: Use ~/.cache/collabtrans (following XDG Base Directory)
        xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
        if xdg_cache_home:
            return os.path.join(xdg_cache_home, "collabtrans")
        else:
            return os.path.join(os.path.expanduser("~"), ".cache", "collabtrans")


def get_collabtrans_paths() -> Dict[str, str]:
    """Get all CollabTrans-related paths for the current system
    
    Returns:
        Dict[str, str]: Dictionary containing all path types
    """
    # Check for deployment environment (systemd service)
    env_config_path = os.environ.get("COLLABTRANS_CONFIG_PATH")
    env_data_home = os.environ.get("XDG_DATA_HOME")
    
    # Use system directories if environment variables are set (deployment mode)
    if env_config_path and os.path.exists(env_config_path):
        config_dir = env_config_path
        data_dir = env_data_home if env_data_home else "/var/lib/collabtrans"
    else:
        # Development mode: use user directories
        data_dir = get_system_data_dir()
        config_dir = get_system_config_dir()
    
    cache_dir = get_system_cache_dir()
    
    return {
        "data_dir": data_dir,
        "config_dir": config_dir,
        "cache_dir": cache_dir,
        "user_profiles": os.path.join(data_dir, "user_profiles"),
        "prompts": os.path.join(data_dir, "prompts"),
        "glossaries": os.path.join(data_dir, "glossaries"),
        "global_config": os.path.join(config_dir, "global_config.json"),
        "app_config": os.path.join(config_dir, "app_config.json"),
        "local_secrets": os.path.join(config_dir, "local_secrets.json"),
        "local_config": os.path.join(config_dir, "local_config.json"),
        "local_users": os.path.join(config_dir, "local_users.json"),
    }


def ensure_directories() -> None:
    """Ensure all CollabTrans directories exist"""
    paths = get_collabtrans_paths()
    
    # Create main directories
    for key, path in paths.items():
        if key.endswith("_dir") or key in ["user_profiles", "prompts", "glossaries"]:
            os.makedirs(path, exist_ok=True)
