# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any
from pathlib import Path
from .secrets_manager import get_secrets_manager

# 创建日志记录器
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

@dataclass
class GlobalConfig:
    """Global configuration class for system-level settings and sensitive information"""
    
    # General settings
    default_language: str = "en"
    
    # Translator settings (grouped configuration)
    translator_settings: TranslatorSettings = field(default_factory=TranslatorSettings)
    
    # AI platforms configuration (loaded from JSON file, includes API keys)
    ai_platforms: Dict[str, AIPlatformConfig] = field(default_factory=dict)
    
    # MinerU token (sensitive information)
    translator_mineru_token: str = ""
    
    
    # System settings
    active_task_ids: list = field(default_factory=list)

    # Web/HTTPS settings
    https_enabled: bool = False
    https_cert_file: Optional[str] = None
    https_key_file: Optional[str] = None
    # Whether to force HTTP redirect to HTTPS when HTTPS is enabled
    https_force_redirect: bool = True
    
    @classmethod
    def load_from_file(cls, config_file: str = "global_config.json") -> "GlobalConfig":
        """Load global configuration from JSON file and API keys from secrets file"""
        try:
            if os.path.exists(config_file):
                logger.info(f"Loading global configuration from: {config_file}")
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Create config instance and update fields
                    config = cls()
                    config.update_from_dict(data)
                    logger.info("Global configuration loaded successfully")
            else:
                logger.warning(f"Global config file {config_file} not found, using empty configuration")
                config = cls()
            
            # Load API keys and other sensitive information from secrets file
            config._load_secrets()
            
            return config
        except Exception as e:
            logger.error(f"Failed to load global configuration: {e}")
            config = cls()
            config._load_secrets()
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
    
    def save_to_file(self, config_file: str = "global_config.json") -> bool:
        """Save global configuration to file (excluding sensitive information)"""
        try:
            # Get configuration dictionary in new format (API keys are not included)
            config_dict = self.get_config_dict(include_api_keys=False)
            
            # Remove other sensitive information
            config_dict.pop("translator_mineru_token", None)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            logger.info(f"Global configuration saved to: {config_file} (excluding sensitive information)")
            return True
        except Exception as e:
            logger.error(f"Failed to save global configuration: {e}")
            return False
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        # Handle translator settings
        if 'translator_settings' in data:
            translator_data = data['translator_settings']
            self.translator_settings = TranslatorSettings(**translator_data)
        
        # Handle AI platforms
        if 'ai_platforms' in data:
            ai_platforms_data = data['ai_platforms']
            self.ai_platforms = {}
            for platform_key, platform_data in ai_platforms_data.items():
                self.ai_platforms[platform_key] = AIPlatformConfig(**platform_data)
        
        # Handle other fields
        for key, value in data.items():
            if hasattr(self, key) and key not in ['translator_settings', 'ai_platforms']:
                setattr(self, key, value)
    
    def get_config_dict(self, include_api_keys: bool = False, flatten: bool = True) -> Dict[str, Any]:
        """Get configuration dictionary in new format"""
        # Manually construct the dictionary to avoid asdict() issues with nested dataclasses
        config_dict = {
            'translator_settings': asdict(self.translator_settings),
            'ai_platforms': {},
            'active_task_ids': self.active_task_ids,
            'https_enabled': self.https_enabled,
            'https_cert_file': self.https_cert_file,
            'https_key_file': self.https_key_file,
            'https_force_redirect': self.https_force_redirect
        }
        
        # Convert ai_platforms to dictionary format (API keys are stored separately)
        for platform_key, platform_config in self.ai_platforms.items():
            platform_dict = asdict(platform_config)
            config_dict['ai_platforms'][platform_key] = platform_dict
        
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
