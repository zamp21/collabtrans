# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from pathlib import Path

# Create logger
logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """Application configuration class, manages all UI settings"""
    
    # Basic settings
    ui_language: str = "zh"
    
    # Workflow settings
    translator_last_workflow: str = "markdown_based"
    translator_auto_workflow_enabled: bool = True
    
    # Format-specific settings
    translator_txt_insert_mode: str = "replace"
    translator_txt_separator: str = "\\n"
    translator_xlsx_insert_mode: str = "replace"
    translator_xlsx_separator: str = "\\n"
    translator_xlsx_translate_regions: str = ""
    translator_docx_insert_mode: str = "replace"
    translator_docx_separator: str = "\\n"
    translator_srt_insert_mode: str = "replace"
    translator_srt_separator: str = "\\n"
    translator_epub_insert_mode: str = "replace"
    translator_epub_separator: str = "\\n"
    translator_html_insert_mode: str = "replace"
    translator_html_separator: str = " "
    translator_json_paths: str = ""
    
    # Parsing settings
    translator_convert_engine: str = ""
    translator_mineru_token: str = ""
    translator_mineru_model_version: str = "vlm"
    translator_formula_ocr: bool = False
    translator_code_ocr: bool = False
    
    # AI translation settings
    translator_skip_translate: bool = False
    translator_platform_last_platform: str = "https://api.openai.com/v1"
    translator_platform_custom_base_url: str = ""
    translator_thinking_mode: str = "disable"
    translator_target_language: str = "Chinese"
    translator_custom_language: str = ""
    translator_custom_prompt: str = ""
    translator_temperature: float = 0.3
    translator_max_tokens: int = 4000
    translator_top_p: float = 1.0
    translator_frequency_penalty: float = 0.0
    translator_presence_penalty: float = 0.0
    
    # Platform-specific API settings (dynamically save keys and models for different platforms)
    platform_api_keys: Dict[str, str] = field(default_factory=dict)
    platform_models: Dict[str, str] = field(default_factory=dict)
    
    # Glossary settings
    glossary_agent_last_platform: str = "https://api.openai.com/v1"
    glossary_agent_platform_custom_baseurl: str = ""
    glossary_agent_config_choice: str = "same"
    glossary_agent_thinking_mode: str = "disable"
    glossary_agent_temperature: float = 0.3
    glossary_agent_max_tokens: int = 4000
    glossary_agent_top_p: float = 1.0
    glossary_agent_frequency_penalty: float = 0.0
    glossary_agent_presence_penalty: float = 0.0
    glossary_agent_to_lang: str = "Chinese"
    
    # Glossary platform-specific API settings
    glossary_platform_api_keys: Dict[str, str] = field(default_factory=dict)
    glossary_platform_models: Dict[str, str] = field(default_factory=dict)
    
    # System settings
    active_task_ids: List[str] = field(default_factory=list)
    theme: str = "auto"
    
    @classmethod
    def _resolve_app_config_path(cls, config_file: str = "app_config.json") -> Path:
        """Resolve the actual read path for app_config.json, by priority:
        Windows/Linux override:
        0) COLLABTRANS_CONFIG_PATH env dir if set (Windows default: C:\\Users\\Public\\collabtrans)
        Linux:
        1) /etc/collabtrans/app_config.json
        Common:
        2) Executable directory (PyInstaller) or current working directory
        3) Project root directory (development environment)
        If an absolute path is passed, return it directly.
        """
        p = Path(config_file)
        if p.is_absolute():
            logger.info(f"[AppConfig] Using absolute path: {p}")
            return p

        # 0) Environment-configured directory (cross-platform override)
        env_dir = os.environ.get("COLLABTRANS_CONFIG_PATH")
        # Windows default runtime configuration directory
        if not env_dir and os.name == "nt":
            env_dir = r"C:\\Users\\Public\\collabtrans"
        if env_dir:
            env_cfg = Path(env_dir) / "app_config.json"
            if env_cfg.exists():
                logger.info(f"[AppConfig] Using env dir config: {env_cfg}")
                return env_cfg

        # 1) System directory priority (non-Windows)
        if os.name != "nt":
            system_dir = Path("/etc/collabtrans")
            system_cfg = system_dir / "app_config.json"
            if system_dir.exists() and system_cfg.exists():
                logger.info(f"[AppConfig] Using system config: {system_cfg}")
                return system_cfg

        # 2) Executable directory (PyInstaller) or current working directory
        try:
            if getattr(__import__('sys'), 'frozen', False):
                import sys as _sys
                exe_dir = Path(os.path.dirname(_sys.executable))
                exe_cfg = exe_dir / "app_config.json"
                if exe_cfg.exists():
                    logger.info(f"[AppConfig] Using executable directory config: {exe_cfg}")
                    return exe_cfg
                cwd_cfg = Path.cwd() / "app_config.json"
                if cwd_cfg.exists():
                    logger.info(f"[AppConfig] Using working directory config: {cwd_cfg}")
                    return cwd_cfg
                # Default return to expected path in executable directory (may be used for subsequent writes)
                return exe_cfg
        except Exception:
            pass

        # 3) Project root directory (development environment)
        project_root = Path(__file__).resolve().parents[2]
        return project_root / "app_config.json"

    @classmethod
    def load_from_file(cls, config_file: str = "app_config.json") -> "AppConfig":
        """Load configuration from file, following system priority path resolution"""
        try:
            cfg_path = cls._resolve_app_config_path(config_file)
            if cfg_path.exists():
                logger.info(f"Loading application configuration from file: {cfg_path}")
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = cls()
                    config.update_from_dict(data)
                    logger.info("Application configuration loaded successfully")
                    return config
            else:
                logger.info(f"Configuration file {cfg_path} does not exist, using default configuration")
                return cls()
        except Exception as e:
            logger.error(f"Failed to load application configuration: {e}")
            return cls()
    
    def save_to_file(self, config_file: str = "app_config.json") -> bool:
        """Save configuration to file (system directory priority, fallback to working directory on failure)"""
        config_data = asdict(self)
        # Use system-appropriate paths
        from ..utils.path_utils import get_collabtrans_paths
        paths = get_collabtrans_paths()
        
        candidates = [
            Path(paths["app_config"]),
            self._resolve_app_config_path(config_file),
            Path.cwd() / "app_config.json"
        ]

        last_error = None
        for path in candidates:
            try:
                if not path.parent.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4, ensure_ascii=False)
                try:
                    # Set appropriate permissions for system directories
                    if str(path).startswith("/etc/"):
                        os.chmod(path, 0o660)
                except Exception:
                    pass
                logger.info(f"Application configuration saved successfully: {path}")
                return True
            except Exception as e:
                last_error = e
                logger.warning(f"Write failed, trying next location: {path} -> {e}")
                continue

        logger.error(f"Failed to save application configuration: {last_error}")
        return False
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                if key in ['platform_api_keys', 'platform_models', 'glossary_platform_api_keys', 'glossary_platform_models']:
                    # Handle dictionary type fields
                    if isinstance(value, dict):
                        setattr(self, key, value)
                elif key == 'active_task_ids':
                    # Handle list type fields
                    if isinstance(value, list):
                        setattr(self, key, value)
                else:
                    # Handle other fields
                    setattr(self, key, value)
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration dictionary"""
        return asdict(self)
    
    def update_platform_api_key(self, platform: str, api_key: str) -> None:
        """Update platform API key"""
        self.platform_api_keys[platform] = api_key
    
    def update_platform_model(self, platform: str, model: str) -> None:
        """Update platform model"""
        self.platform_models[platform] = model
    
    def get_platform_api_key(self, platform: str) -> str:
        """Get platform API key"""
        return self.platform_api_keys.get(platform, "")
    
    def get_platform_model(self, platform: str) -> str:
        """Get platform model"""
        return self.platform_models.get(platform, "")
    
    def update_glossary_platform_api_key(self, platform: str, api_key: str) -> None:
        """Update glossary platform API key"""
        self.glossary_platform_api_keys[platform] = api_key
    
    def update_glossary_platform_model(self, platform: str, model: str) -> None:
        """Update glossary platform model"""
        self.glossary_platform_models[platform] = model
    
    def get_glossary_platform_api_key(self, platform: str) -> str:
        """Get glossary platform API key"""
        return self.glossary_platform_api_keys.get(platform, "")
    
    def get_glossary_platform_model(self, platform: str) -> str:
        """Get glossary platform model"""
        return self.glossary_platform_models.get(platform, "")

    @classmethod
    def get_config(cls, config_file: str = "app_config.json") -> "AppConfig":
        """Get configuration, resolve path by priority and load"""
        return cls.load_from_file(config_file)


# Global configuration instance
_app_config = None

def get_app_config() -> AppConfig:
    """Get global application configuration"""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig.get_config()
    return _app_config

def save_app_config() -> bool:
    """Save global application configuration"""
    global _app_config
    if _app_config is not None:
        return _app_config.save_to_file()
    return False
