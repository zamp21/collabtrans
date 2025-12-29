# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any
from pathlib import Path
from .secrets_manager import get_secrets_manager
from .env_detector import is_production, get_config_path, get_dev_config_path, get_prod_config_path

# Create logger
logger = logging.getLogger(__name__)


@dataclass
class TranslatorSettings:
    """Translator settings configuration"""
    convert_engine: str = "mineru"
    mineru_model_version: str = "vlm"
    formula_ocr: bool = False
    code_ocr: bool = False
    skip_translate: bool = False
    # Detailed parsing engines configurations (non-sensitive)
    # Example:
    # {
    #   "mineru": {"name": "MinerU", "type": "mineru", "model_version": "vlm"},
    #   "docling": {"name": "Docling", "type": "docling"},
    #   "identity": {"name": "Identity", "type": "identity"}
    # }
    engines: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AIPlatformConfig:
    """AI Platform configuration (API keys stored separately in local_secrets.json)"""
    name: str = ""
    url: str = ""
    model: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    recommended_tokens: Optional[int] = None
    performance_note: Optional[str] = None
    api_type: str = "openai"  # API type: "openai" or "ollama"

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    console_enabled: bool = True
    file_enabled: bool = True
    max_file_size_mb: int = 10
    backup_count: int = 7

@dataclass
class GlobalConfig:
    """Global configuration class for system-level settings and sensitive information"""
    
    # General settings
    default_language: str = "en"
    
    # Logging settings
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    # Translator settings (grouped configuration)
    translator_settings: TranslatorSettings = field(default_factory=TranslatorSettings)
    
    # AI platforms configuration (loaded from JSON file, includes API keys)
    ai_platforms: Dict[str, AIPlatformConfig] = field(default_factory=dict)
    # Default platform for homepage model selection (stored in JSON at ai_platforms.default_platform)
    ai_platforms_default_platform: Optional[str] = None
    
    # MinerU token (sensitive information)
    translator_mineru_token: str = ""
    
    
    # System settings
    active_task_ids: list = field(default_factory=list)
    
    @classmethod
    def load_from_file(cls, config_file: str = "global_config.json") -> "GlobalConfig":
        """Load global configuration from JSON file and API keys from secrets file"""
        try:
            # Configuration file priority:
            # 0. COLLABTRANS_CONFIG_PATH env dir if set (cross-platform override)
            # 1. Environment-based path (production: /etc/collabtrans/, development: project root)
            # 2. Fallback to legacy paths for backward compatibility
            
            # 0) Environment-configured directory (cross-platform override)
            env_dir = os.environ.get("COLLABTRANS_CONFIG_PATH")
            # Windows default runtime configuration directory
            if not env_dir and os.name == "nt":
                env_dir = r"C:\\Users\\Public\\collabtrans"
            if env_dir:
                env_cfg = os.path.join(env_dir, config_file)
                if os.path.exists(env_cfg):
                    logger.info(f"Loading global configuration from env dir: {env_cfg}")
                    with open(env_cfg, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        config = cls()
                        config.update_from_dict(data)
                        logger.debug("Global configuration loaded successfully from env dir")
                        return config

            # 1) Environment-based path (production or development)
            if is_production():
                # Production: use /etc/collabtrans/
                config_path = get_prod_config_path(config_file)
                if config_path.exists():
                    logger.info(f"Loading global configuration from production config: {config_path}")
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        config = cls()
                        config.update_from_dict(data)
                        logger.debug("Global configuration loaded successfully from production config")
                        config._load_secrets()
                        return config
            else:
                # Development: use project root
                config_path = get_dev_config_path(config_file)
                if config_path.exists():
                    logger.info(f"Loading global configuration from development config: {config_path}")
                    with open(config_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        config = cls()
                        config.update_from_dict(data)
                        logger.debug("Global configuration loaded successfully from development config")
                        config._load_secrets()
                        return config

            # 2) Fallback to legacy paths for backward compatibility
            if os.name != "nt":
                system_config_file = "/etc/collabtrans/global_config.json"
                system_dir_exists = os.path.exists("/etc/collabtrans")
                if system_dir_exists and os.path.exists(system_config_file):
                    logger.info(f"Loading global configuration from system config (legacy): {system_config_file}")
                    with open(system_config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        config = cls()
                        config.update_from_dict(data)
                        logger.debug("Global configuration loaded successfully from system config")
                        config._load_secrets()
                        return config
            
            # Try to load configuration file from executable directory
            import sys
            if getattr(sys, 'frozen', False):
                # PyInstaller packaged environment
                exe_dir = os.path.dirname(sys.executable)
                exe_config_file = os.path.join(exe_dir, config_file)
                if os.path.exists(exe_config_file):
                    logger.info(f"Loading global configuration from executable directory (legacy): {exe_config_file}")
                    with open(exe_config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        config = cls()
                        config.update_from_dict(data)
                        logger.debug("Global configuration loaded successfully from executable directory")
                        config._load_secrets()
                        return config
                elif os.path.exists(config_file):
                    logger.info(f"Loading global configuration from current directory (legacy): {config_file}")
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        config = cls()
                        config.update_from_dict(data)
                        logger.debug("Global configuration loaded successfully")
                        config._load_secrets()
                        return config
            
            # Development environment fallback
            if os.path.exists(config_file):
                logger.info(f"Loading global configuration from current directory (legacy): {config_file}")
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = cls()
                    config.update_from_dict(data)
                    logger.debug("Global configuration loaded successfully")
                    config._load_secrets()
                    return config
            
            # No config file found, use defaults
            logger.warning(f"Global config file not found, using empty configuration")
            config = cls()
            config._load_secrets()
            
            # Migration: Ensure all platforms have api_type field
            config._migrate_platform_api_types()
            
            return config
        except Exception as e:
            logger.error(f"Failed to load global configuration: {e}")
            config = cls()
            config._load_secrets()
            config._migrate_platform_api_types()
            return config
    
    def _load_secrets(self) -> None:
        """Load sensitive information from secrets configuration file"""
        try:
            secrets_manager = get_secrets_manager()
            
            # Load MinerU token
            mineru_token = secrets_manager.get_mineru_token()
            if mineru_token and mineru_token.strip():
                self.translator_mineru_token = mineru_token
                logger.info("Loaded MinerU token from secrets config")
                
        except Exception as e:
            logger.warning(f"Failed to load secrets config: {e}")
    
    def _migrate_platform_api_types(self) -> None:
        """Migration: Ensure all platforms have api_type field
        
        Auto-detect api_type based on URL:
        - If URL contains '/api/chat' or port 11434 (common Ollama port), set to 'ollama'
        - Otherwise, default to 'openai'
        """
        try:
            migrated = False
            for platform_key, platform_config in self.ai_platforms.items():
                if not hasattr(platform_config, 'api_type') or not platform_config.api_type:
                    # Auto-detect api_type based on URL
                    url = (platform_config.url or '').lower()
                    if '/api/chat' in url or ':11434' in url or 'ollama' in url:
                        api_type = 'ollama'
                    else:
                        api_type = 'openai'
                    
                    platform_config.api_type = api_type
                    migrated = True
                    logger.info(f"Migrated platform '{platform_key}': added api_type='{api_type}' (detected from URL: {platform_config.url})")
            # If any platform was migrated, save the configuration to persist the change
            if migrated:
                try:
                    self.save_to_file()
                    logger.info("Configuration migrated and saved with api_type fields")
                except Exception as e:
                    logger.warning(f"Failed to save migrated configuration: {e}")
        except Exception as e:
            logger.warning(f"Failed to migrate platform api_type fields: {e}")
    
    def save_to_file(self, config_file: str = "global_config.json") -> bool:
        """Save global configuration to file (excluding sensitive information)
        Uses the same path priority as load_from_file to ensure consistency:
        - Environment-configured directory (if COLLABTRANS_CONFIG_PATH is set)
        - System directory (/etc/collabtrans/global_config.json on Linux)
        - Executable directory or current working directory
        """
        # Prepare dictionary without sensitive info
        try:
            config_dict = self.get_config_dict(include_api_keys=False)
            config_dict.pop("translator_mineru_token", None)
        except Exception:
            config_dict = {}

        # Use the same path priority as load_from_file to ensure consistency
        candidates = []
        
        # 0) Environment-configured directory (cross-platform override)
        env_dir = os.environ.get("COLLABTRANS_CONFIG_PATH")
        # Windows default runtime configuration directory
        if not env_dir and os.name == "nt":
            env_dir = r"C:\\Users\\Public\\collabtrans"
        if env_dir:
            env_cfg = os.path.join(env_dir, "global_config.json")
            candidates.append(env_cfg)
        
        # 1) System directory on non-Windows platforms
        if os.name != "nt":
            system_config_file = "/etc/collabtrans/global_config.json"
            # Only add to candidates if directory exists (even if file doesn't exist yet)
            if os.path.exists("/etc/collabtrans"):
                candidates.append(system_config_file)
        
        # 2) Executable directory (for packaged applications)
        import sys
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            exe_config_file = os.path.join(exe_dir, "global_config.json")
            candidates.append(exe_config_file)
        
        # 3) Current working directory (development environment)
        candidates.append(config_file)
        candidates.append(str(Path.cwd() / "global_config.json"))
        
        # Fallback: user config directory (if none of the above work)
        from ..utils.path_utils import get_collabtrans_paths
        paths = get_collabtrans_paths()
        if paths["global_config"] not in candidates:
            candidates.append(paths["global_config"])

        last_error = None
        for target_path in candidates:
            try:
                # Ensure directory exists
                target_dir = os.path.dirname(target_path)
                if target_dir:
                    Path(target_dir).mkdir(parents=True, exist_ok=True)
                with open(target_path, 'w', encoding='utf-8') as f:
                    json.dump(config_dict, f, ensure_ascii=False, indent=2)
                # Set appropriate permissions for system directories
                try:
                    if target_path.startswith("/etc/"):
                        os.chmod(target_path, 0o640)
                except Exception:
                    pass
                logger.info(f"Global configuration saved to: {target_path} (excluding sensitive information)")
                return True
            except PermissionError as e:
                last_error = e
                logger.warning(f"Permission denied writing global config to {target_path}: {e}, trying next location")
                continue
            except Exception as e:
                last_error = e
                logger.warning(f"Failed to write global config to {target_path}: {e}, trying next location")
                continue

        logger.error(f"Failed to save global configuration after fallbacks: {last_error}")
        return False
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        # Handle logging settings
        if 'logging' in data:
            logging_data = data['logging']
            self.logging = LoggingConfig(**logging_data)
        
        # Handle translator settings
        if 'translator_settings' in data:
            translator_data = data['translator_settings']
            self.translator_settings = TranslatorSettings(**translator_data)
        
        # Handle AI platforms
        if 'ai_platforms' in data:
            ai_platforms_data = data['ai_platforms']
            # Handle default_platform specially
            dp = ai_platforms_data.get('default_platform')
            if isinstance(dp, str) and dp.strip():
                self.ai_platforms_default_platform = dp.strip()
            # Merge platform updates instead of replacing all platforms
            # This ensures existing platforms are preserved when only updating one platform
            for platform_key, platform_data in ai_platforms_data.items():
                if platform_key == 'default_platform':
                    continue
                if isinstance(platform_data, dict):
                    # If platform already exists, merge the updates
                    if platform_key in self.ai_platforms:
                        existing_config = self.ai_platforms[platform_key]
                        # Update existing config with new values
                        for key, value in platform_data.items():
                            if hasattr(existing_config, key):
                                # Update the field value (allow None and empty values to be set)
                                setattr(existing_config, key, value)
                        # Ensure api_type is set if missing (migration for old configs)
                        # Only update if explicitly provided in platform_data, or if missing entirely
                        if 'api_type' in platform_data:
                            existing_config.api_type = platform_data['api_type']
                        elif not hasattr(existing_config, 'api_type') or not existing_config.api_type:
                            # Auto-detect if missing
                            url = (existing_config.url or '').lower()
                            if '/api/chat' in url or ':11434' in url or 'ollama' in url:
                                existing_config.api_type = 'ollama'
                            else:
                                existing_config.api_type = 'openai'
                    else:
                        # Create new platform config with default values for missing fields
                        # Use AIPlatformConfig defaults for any missing fields
                        platform_dict = platform_data.copy()
                        # Ensure all required fields have values (use defaults if missing)
                        if 'api_type' not in platform_dict:
                            platform_dict['api_type'] = 'openai'
                        self.ai_platforms[platform_key] = AIPlatformConfig(**platform_dict)
        
        # Handle other fields
        for key, value in data.items():
            if hasattr(self, key) and key not in ['logging', 'translator_settings', 'ai_platforms']:
                setattr(self, key, value)
    
    def get_config_dict(self, include_api_keys: bool = False, flatten: bool = True) -> Dict[str, Any]:
        """Get configuration dictionary in new format"""
        # Manually construct the dictionary to avoid asdict() issues with nested dataclasses
        config_dict = {
            'default_language': self.default_language,
            'logging': asdict(self.logging),
            'translator_settings': asdict(self.translator_settings),
            'ai_platforms': {},
            'active_task_ids': self.active_task_ids
        }
        
        # Convert ai_platforms to dictionary format (API keys are stored separately)
        for platform_key, platform_config in self.ai_platforms.items():
            platform_dict = asdict(platform_config)
            config_dict['ai_platforms'][platform_key] = platform_dict
        # Inject default_platform under ai_platforms for storage
        if self.ai_platforms_default_platform:
            config_dict['ai_platforms']['default_platform'] = self.ai_platforms_default_platform
        
        # Flatten translator_settings for backward compatibility
        if flatten:
            translator_settings = config_dict['translator_settings']
            config_dict['translator_convert_engine'] = translator_settings['convert_engine']
            config_dict['translator_mineru_model_version'] = translator_settings['mineru_model_version']
            config_dict['translator_formula_ocr'] = translator_settings['formula_ocr']
            config_dict['translator_code_ocr'] = translator_settings['code_ocr']
            config_dict['translator_skip_translate'] = translator_settings['skip_translate']
        
        return config_dict
    
    def get_platform_api_key(self, platform: str) -> str:
        """Get platform API key from secrets manager"""
        try:
            secrets_manager = get_secrets_manager()
            api_keys = secrets_manager.get_api_keys()
            return api_keys.get(platform) or ""
        except Exception as e:
            logger.warning(f"Failed to get API key for platform {platform}: {e}")
            return ""
    
    # New methods for AI platform configuration
    def get_ai_platform_config(self, platform: str) -> Optional[AIPlatformConfig]:
        """Get AI platform configuration"""
        return self.ai_platforms.get(platform)
    
    def update_ai_platform_config(self, platform: str, config: AIPlatformConfig) -> None:
        """Update AI platform configuration"""
        self.ai_platforms[platform] = config
    
    def get_platform_name(self, platform: str) -> str:
        """Get platform display name"""
        platform_config = self.get_ai_platform_config(platform)
        return platform_config.name if platform_config else platform
    
    def get_platform_max_tokens(self, platform: str) -> int:
        """Get platform max tokens"""
        platform_config = self.get_ai_platform_config(platform)
        return platform_config.max_tokens if platform_config else 4096
    
    def get_platform_temperature(self, platform: str) -> float:
        """Get platform temperature"""
        platform_config = self.get_ai_platform_config(platform)
        return platform_config.temperature if platform_config else 0.7
    
    def get_platform_recommended_tokens(self, platform: str) -> Optional[int]:
        """Get platform recommended tokens"""
        platform_config = self.get_ai_platform_config(platform)
        return platform_config.recommended_tokens if platform_config else None
    
    def get_platform_performance_note(self, platform: str) -> Optional[str]:
        """Get platform performance note"""
        platform_config = self.get_ai_platform_config(platform)
        return platform_config.performance_note if platform_config else None
    
    
    @classmethod
    def get_config(cls, config_file: str = "global_config.json") -> "GlobalConfig":
        """Get configuration, load from file first"""
        return cls.load_from_file(config_file)


# Global configuration instance
_global_config: Optional[GlobalConfig] = None

def get_global_config() -> GlobalConfig:
    """Get global configuration"""
    global _global_config
    if _global_config is None:
        _global_config = GlobalConfig.get_config()
    return _global_config

def save_global_config() -> bool:
    """Save global configuration"""
    global _global_config
    if _global_config is not None:
        return _global_config.save_to_file()
    return False
