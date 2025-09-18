# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from pathlib import Path

# 创建日志记录器
logger = logging.getLogger(__name__)


@dataclass
class AppConfig:
    """应用配置类，管理所有UI设置"""
    
    # 基础设置
    ui_language: str = "zh"
    
    # 工作流设置
    translator_last_workflow: str = "markdown_based"
    translator_auto_workflow_enabled: bool = True
    
    # 格式特定设置
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
    
    # 解析设置
    translator_convert_engin: str = ""
    translator_mineru_token: str = ""
    translator_mineru_model_version: str = "vlm"
    translator_formula_ocr: bool = False
    translator_code_ocr: bool = False
    
    # AI翻译设置
    translator_skip_translate: bool = False
    translator_platform_last_platform: str = "https://api.openai.com/v1"
    translator_platform_custom_base_url: str = ""
    translator_thinking_mode: str = "disable"
    translator_target_language: str = "中文"
    translator_custom_language: str = ""
    translator_custom_prompt: str = ""
    translator_temperature: float = 0.3
    translator_max_tokens: int = 4000
    translator_top_p: float = 1.0
    translator_frequency_penalty: float = 0.0
    translator_presence_penalty: float = 0.0
    
    # 平台特定API设置 (动态保存不同平台的key和model)
    platform_api_keys: Dict[str, str] = field(default_factory=dict)
    platform_models: Dict[str, str] = field(default_factory=dict)
    
    # 术语表设置
    glossary_agent_last_platform: str = "https://api.openai.com/v1"
    glossary_agent_platform_custom_baseurl: str = ""
    glossary_agent_config_choice: str = "same"
    glossary_agent_thinking_mode: str = "disable"
    glossary_agent_temperature: float = 0.3
    glossary_agent_max_tokens: int = 4000
    glossary_agent_top_p: float = 1.0
    glossary_agent_frequency_penalty: float = 0.0
    glossary_agent_presence_penalty: float = 0.0
    glossary_agent_to_lang: str = "中文"
    
    # 术语表平台特定API设置
    glossary_platform_api_keys: Dict[str, str] = field(default_factory=dict)
    glossary_platform_models: Dict[str, str] = field(default_factory=dict)
    
    # 系统设置
    active_task_ids: List[str] = field(default_factory=list)
    theme: str = "auto"
    
    @classmethod
    def load_from_file(cls, config_file: str = "app_config.json") -> "AppConfig":
        """从文件加载配置"""
        try:
            if os.path.exists(config_file):
                logger.info(f"正在从文件加载应用配置: {config_file}")
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 创建配置实例并更新字段
                    config = cls()
                    config.update_from_dict(data)
                    logger.info("应用配置加载成功")
                    return config
            else:
                logger.info(f"配置文件 {config_file} 不存在，使用默认配置")
                return cls()
        except Exception as e:
            logger.error(f"加载应用配置失败: {e}")
            return cls()
    
    def save_to_file(self, config_file: str = "app_config.json") -> bool:
        """保存配置到文件"""
        try:
            config_data = asdict(self)
            logger.info(f"正在保存应用配置到文件: {config_file}")
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            logger.info("应用配置保存成功")
            return True
        except Exception as e:
            logger.error(f"保存应用配置失败: {e}")
            return False
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新配置"""
        for key, value in data.items():
            if hasattr(self, key):
                if key in ['platform_api_keys', 'platform_models', 'glossary_platform_api_keys', 'glossary_platform_models']:
                    # 处理字典类型字段
                    if isinstance(value, dict):
                        setattr(self, key, value)
                elif key == 'active_task_ids':
                    # 处理列表类型字段
                    if isinstance(value, list):
                        setattr(self, key, value)
                else:
                    # 处理其他字段
                    setattr(self, key, value)
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return asdict(self)
    
    def update_platform_api_key(self, platform: str, api_key: str) -> None:
        """更新平台API密钥"""
        self.platform_api_keys[platform] = api_key
    
    def update_platform_model(self, platform: str, model: str) -> None:
        """更新平台模型"""
        self.platform_models[platform] = model
    
    def get_platform_api_key(self, platform: str) -> str:
        """获取平台API密钥"""
        return self.platform_api_keys.get(platform, "")
    
    def get_platform_model(self, platform: str) -> str:
        """获取平台模型"""
        return self.platform_models.get(platform, "")
    
    def update_glossary_platform_api_key(self, platform: str, api_key: str) -> None:
        """更新术语表平台API密钥"""
        self.glossary_platform_api_keys[platform] = api_key
    
    def update_glossary_platform_model(self, platform: str, model: str) -> None:
        """更新术语表平台模型"""
        self.glossary_platform_models[platform] = model
    
    def get_glossary_platform_api_key(self, platform: str) -> str:
        """获取术语表平台API密钥"""
        return self.glossary_platform_api_keys.get(platform, "")
    
    def get_glossary_platform_model(self, platform: str) -> str:
        """获取术语表平台模型"""
        return self.glossary_platform_models.get(platform, "")

    @classmethod
    def get_config(cls, config_file: str = "app_config.json") -> "AppConfig":
        """获取配置，优先从文件加载"""
        return cls.load_from_file(config_file)


# 全局配置实例
_app_config = None

def get_app_config() -> AppConfig:
    """获取全局应用配置"""
    global _app_config
    if _app_config is None:
        _app_config = AppConfig.get_config()
    return _app_config

def save_app_config() -> bool:
    """保存全局应用配置"""
    global _app_config
    if _app_config is not None:
        return _app_config.save_to_file()
    return False
