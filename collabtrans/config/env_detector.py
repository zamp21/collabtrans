"""
Environment detection utility for CollabTrans.

This module provides functions to detect whether the application is running
in production or development environment, and returns appropriate configuration paths.
"""
import os
from pathlib import Path
from typing import Optional


def _find_project_root() -> Path:
    """Find the project root directory by looking for .production file or other markers."""
    current = Path(__file__).resolve()
    
    # Look up to 5 levels up for project root markers
    for _ in range(5):
        if (current / ".production").exists() or (current / ".development").exists():
            return current
        if (current / "pyproject.toml").exists() and (current / "collabtrans").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    
    # Fallback to current working directory
    return Path.cwd()


def is_production() -> bool:
    """
    Detect if the application is running in production environment.
    
    Detection priority:
    1. Check for .production file in project root
    2. Check for .development file in project root (if exists, not production)
    3. Check for ENV_MODE environment variable
    4. Default to development if none found
    
    Returns:
        bool: True if production environment, False if development
    """
    project_root = _find_project_root()
    
    # Check for .production file
    if (project_root / ".production").exists():
        return True
    
    # Check for .development file
    if (project_root / ".development").exists():
        return False
    
    # Check environment variable
    env_mode = os.environ.get("ENV_MODE", "").lower()
    if env_mode == "production":
        return True
    if env_mode == "development":
        return False
    
    # Default to development
    return False


def get_config_base_dir() -> Path:
    """
    Get the base directory for configuration files based on environment.
    
    Returns:
        Path: Production: /etc/collabtrans, Development: project root
    """
    if is_production():
        return Path("/etc/collabtrans")
    else:
        return _find_project_root()


def get_config_path(config_filename: str) -> Path:
    """
    Get the full path to a configuration file based on environment.
    
    Args:
        config_filename: Name of the configuration file (e.g., "local_config.json")
    
    Returns:
        Path: Full path to the configuration file
    """
    base_dir = get_config_base_dir()
    return base_dir / config_filename


def get_dev_config_path(config_filename: str) -> Path:
    """
    Get the development configuration file path (project root).
    
    Args:
        config_filename: Name of the configuration file
    
    Returns:
        Path: Full path to the development configuration file
    """
    project_root = _find_project_root()
    return project_root / config_filename


def get_prod_config_path(config_filename: str) -> Path:
    """
    Get the production configuration file path (/etc/collabtrans).
    
    Args:
        config_filename: Name of the configuration file
    
    Returns:
        Path: Full path to the production configuration file
    """
    return Path("/etc/collabtrans") / config_filename

