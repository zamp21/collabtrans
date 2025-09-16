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
class GlobalConfig:
    """全局配置类，存储系统级配置和敏感信息"""
    
    # 解析设置（全局配置）
    translator_convert_engin: str = "mineru"
    translator_mineru_token: str = ""
    translator_mineru_model_version: str = "vlm"
    translator_formula_ocr: bool = False
    translator_code_ocr: bool = False
    
    # AI翻译设置（全局配置）
    translator_skip_translate: bool = False
    
    # 平台URL映射 (全局配置)
    platform_urls: Dict[str, str] = field(default_factory=lambda: {
        # OpenAI 及兼容
        "openai": "https://api.openai.com/v1",
        "azure": "https://your-resource.openai.azure.com/",
        "groq": "https://api.groq.com/openai/v1",
        "together": "https://api.together.xyz/v1",
        # 其他主流模型提供商
        "anthropic": "https://api.anthropic.com",
        "google": "https://generativelanguage.googleapis.com/v1beta",
        "mistral": "https://api.mistral.ai/v1",
        "cohere": "https://api.cohere.com/v1",
        "xai": "https://api.x.ai/v1",
        # 国内常见兼容/平台
        "deepseek": "https://api.deepseek.com/v1",
        "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "volcengine_ark": "https://ark.cn-beijing.volces.com/api/v3",
        "siliconflow": "https://api.siliconflow.cn/v1",
        "zhipu": "https://open.bigmodel.cn/api/paas/v4",
        "dmxapi": "https://www.dmxapi.cn/v1",
        # 自定义占位
        "custom": ""
    })
    
    # 平台特定API设置 (全局配置 - 敏感信息)
    platform_api_keys: Dict[str, str] = field(default_factory=dict)
    platform_models: Dict[str, str] = field(default_factory=lambda: {
        # 海外主流
        "openai": "gpt-4o-mini",                  # 价格/速度/翻译质量均衡
        "azure": "gpt-4o-mini",                   # 需用户在Azure端创建部署
        "anthropic": "claude-3-5-sonnet-latest",  # 高质量理解与生成
        "google": "gemini-1.5-pro",               # 多模态强，翻译稳健
        "mistral": "mistral-large-latest",        # 英欧语系表现好
        "cohere": "command-r-plus",               # 长文本与推理较强
        "xai": "grok-2",                          # 英文泛用
        "groq": "llama3-70b-8192",                # 低延迟推理，适合中短文本
        "together": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",

        # 国内与兼容（名称因平台更新可能变化）
        "deepseek": "deepseek-v3",
        "dashscope": "qwen2.5-7b-instruct",
        "volcengine_ark": "doubao-pro-32k",
        "siliconflow": "Qwen2.5-7B-Instruct",
        "zhipu": "glm-4-plus",
        "dmxapi": "gpt-4o-mini",                  # 聚合转发，默认给出兼容模型名

        # 自定义
        "custom": ""
    })
    
    
    # 系统设置
    active_task_ids: list = field(default_factory=list)
    
    @classmethod
    def load_from_file(cls, config_file: str = "global_config.json") -> "GlobalConfig":
        """从文件加载全局配置，并从敏感配置文件加载API密钥"""
        try:
            if os.path.exists(config_file):
                logger.info(f"正在从文件加载全局配置: {config_file}")
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 创建配置实例并更新字段
                    config = cls()
                    config.update_from_dict(data)
                    logger.info("全局配置加载成功")
            else:
                logger.info(f"全局配置文件 {config_file} 不存在，使用默认配置")
                config = cls()
            
            # 从敏感配置文件加载API密钥等敏感信息
            config._load_secrets()
            
            return config
        except Exception as e:
            logger.error(f"加载全局配置失败: {e}")
            config = cls()
            config._load_secrets()
            return config
    
    def _load_secrets(self) -> None:
        """从敏感配置文件加载敏感信息"""
        try:
            secrets_manager = get_secrets_manager()
            
            # 加载API密钥
            api_keys = secrets_manager.get_api_keys()
            if api_keys:
                # 合并API密钥，敏感配置优先
                for platform, key in api_keys.items():
                    if key and key.strip():  # 只更新非空的密钥
                        self.platform_api_keys[platform] = key
                logger.info(f"从敏感配置加载了 {len(api_keys)} 个API密钥")
            
            # 加载MinerU令牌
            mineru_token = secrets_manager.get_mineru_token()
            if mineru_token and mineru_token.strip():
                self.translator_mineru_token = mineru_token
                logger.info("从敏感配置加载了MinerU令牌")
                
        except Exception as e:
            logger.warning(f"加载敏感配置失败: {e}")
    
    def save_to_file(self, config_file: str = "global_config.json") -> bool:
        """保存全局配置到文件（不包含敏感信息）"""
        try:
            # 创建不包含敏感信息的配置副本
            config_dict = asdict(self)
            
            # 移除敏感信息，这些信息保存在local_secrets.json中
            config_dict.pop("platform_api_keys", None)
            config_dict.pop("translator_mineru_token", None)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
            logger.info(f"全局配置已保存到: {config_file}（不包含敏感信息）")
            return True
        except Exception as e:
            logger.error(f"保存全局配置失败: {e}")
            return False
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新配置"""
        for key, value in data.items():
            if hasattr(self, key):
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
    
    def get_platform_url(self, platform: str) -> str:
        """获取平台URL"""
        return self.platform_urls.get(platform, "")
    
    def update_platform_url(self, platform: str, url: str) -> None:
        """更新平台URL"""
        self.platform_urls[platform] = url
    
    
    @classmethod
    def get_config(cls, config_file: str = "global_config.json") -> "GlobalConfig":
        """获取配置，优先从文件加载"""
        return cls.load_from_file(config_file)


# 全局配置实例
_global_config: Optional[GlobalConfig] = None

def get_global_config() -> GlobalConfig:
    """获取全局配置"""
    global _global_config
    if _global_config is None:
        _global_config = GlobalConfig.get_config()
    return _global_config

def save_global_config() -> bool:
    """保存全局配置"""
    global _global_config
    if _global_config is not None:
        return _global_config.save_to_file()
    return False
