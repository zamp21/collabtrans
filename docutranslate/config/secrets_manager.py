# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# 创建日志记录器
logger = logging.getLogger(__name__)


class SecretsManager:
    """敏感配置管理器 - 管理API密钥等敏感信息"""
    
    def __init__(self, secrets_file: str = "local_secrets.json"):
        """
        初始化敏感配置管理器
        
        Args:
            secrets_file: 敏感配置文件路径
        """
        self.secrets_file = Path(secrets_file)
        self._secrets_cache: Optional[Dict[str, Any]] = None
        
    def load_secrets(self) -> Dict[str, Any]:
        """
        加载敏感配置
        
        Returns:
            敏感配置字典，如果文件不存在则返回空字典
        """
        if self._secrets_cache is not None:
            return self._secrets_cache
            
        if not self.secrets_file.exists():
            logger.warning(f"敏感配置文件 {self.secrets_file} 不存在，使用空配置")
            self._secrets_cache = {}
            return self._secrets_cache
            
        try:
            with open(self.secrets_file, 'r', encoding='utf-8') as f:
                secrets = json.load(f)
            
            logger.info(f"成功加载敏感配置文件: {self.secrets_file}")
            self._secrets_cache = secrets
            return secrets
            
        except Exception as e:
            logger.error(f"加载敏感配置文件失败: {e}")
            self._secrets_cache = {}
            return self._secrets_cache
    
    def get_api_keys(self) -> Dict[str, str]:
        """
        获取API密钥配置
        
        Returns:
            API密钥字典
        """
        secrets = self.load_secrets()
        return secrets.get("platform_api_keys", {})
    
    def get_mineru_token(self) -> Optional[str]:
        """
        获取MinerU令牌
        
        Returns:
            MinerU令牌，如果不存在则返回None
        """
        secrets = self.load_secrets()
        return secrets.get("translator_mineru_token")
    
    def get_auth_secrets(self) -> Dict[str, Any]:
        """
        获取认证相关敏感信息
        
        Returns:
            认证敏感信息字典
        """
        secrets = self.load_secrets()
        return secrets.get("auth_secrets", {})
    
    def get_default_password(self) -> Optional[str]:
        """
        获取默认管理员密码
        
        Returns:
            默认密码，如果不存在则返回None
        """
        auth_secrets = self.get_auth_secrets()
        return auth_secrets.get("default_password")
    
    def get_session_secret_key(self) -> Optional[str]:
        """
        获取会话密钥
        
        Returns:
            会话密钥，如果不存在则返回None
        """
        auth_secrets = self.get_auth_secrets()
        return auth_secrets.get("session_secret_key")
    
    def get_redis_password(self) -> Optional[str]:
        """
        获取Redis密码
        
        Returns:
            Redis密码，如果不存在则返回None
        """
        auth_secrets = self.get_auth_secrets()
        return auth_secrets.get("redis_password")
    
    def save_secrets(self, secrets: Dict[str, Any]) -> bool:
        """
        保存敏感配置到文件
        
        Args:
            secrets: 要保存的敏感配置
            
        Returns:
            是否保存成功
        """
        try:
            # 确保目录存在
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.secrets_file, 'w', encoding='utf-8') as f:
                json.dump(secrets, f, indent=2, ensure_ascii=False)
            
            # 更新缓存
            self._secrets_cache = secrets
            
            logger.info(f"敏感配置已保存到: {self.secrets_file}")
            return True
            
        except Exception as e:
            logger.error(f"保存敏感配置文件失败: {e}")
            return False
    
    def update_api_key(self, platform: str, api_key: str) -> bool:
        """
        更新指定平台的API密钥
        
        Args:
            platform: 平台名称
            api_key: API密钥
            
        Returns:
            是否更新成功
        """
        secrets = self.load_secrets()
        
        if "platform_api_keys" not in secrets:
            secrets["platform_api_keys"] = {}
        
        secrets["platform_api_keys"][platform] = api_key
        
        return self.save_secrets(secrets)
    
    def update_mineru_token(self, token: str) -> bool:
        """
        更新MinerU令牌
        
        Args:
            token: MinerU令牌
            
        Returns:
            是否更新成功
        """
        secrets = self.load_secrets()
        secrets["translator_mineru_token"] = token
        
        return self.save_secrets(secrets)
    
    def update_auth_secret(self, key: str, value: str) -> bool:
        """
        更新认证相关敏感信息
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            是否更新成功
        """
        secrets = self.load_secrets()
        
        if "auth_secrets" not in secrets:
            secrets["auth_secrets"] = {}
        
        secrets["auth_secrets"][key] = value
        
        return self.save_secrets(secrets)
    
    def has_secrets_file(self) -> bool:
        """
        检查敏感配置文件是否存在
        
        Returns:
            文件是否存在
        """
        return self.secrets_file.exists()
    
    def create_template_file(self) -> bool:
        """
        创建配置模板文件
        
        Returns:
            是否创建成功
        """
        template_file = self.secrets_file.parent / f"{self.secrets_file.stem}.template"
        
        template_content = {
            "_comment": "本地敏感配置文件模板 - 请复制为 local_secrets.json 并填入真实值",
            "_warning": "此文件包含敏感信息，请勿提交到git仓库",
            
            "platform_api_keys": {
                "openai": "your-openai-api-key-here",
                "azure": "your-azure-api-key-here", 
                "anthropic": "your-anthropic-api-key-here",
                "google": "your-google-api-key-here",
                "mistral": "your-mistral-api-key-here",
                "cohere": "your-cohere-api-key-here",
                "xai": "your-xai-api-key-here",
                "groq": "your-groq-api-key-here",
                "together": "your-together-api-key-here",
                "deepseek": "your-deepseek-api-key-here",
                "dashscope": "your-dashscope-api-key-here",
                "volcengine_ark": "your-volcengine-api-key-here",
                "siliconflow": "your-siliconflow-api-key-here",
                "zhipu": "your-zhipu-api-key-here",
                "dmxapi": "your-dmxapi-key-here",
                "custom": "your-custom-api-key-here"
            },
            
            "translator_mineru_token": "your-mineru-token-here",
            
            "auth_secrets": {
                "default_password": "your-secure-admin-password",
                "session_secret_key": "your-very-long-random-session-secret-key-here",
                "redis_password": "your-redis-password-if-needed"
            }
        }
        
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_content, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置模板文件已创建: {template_file}")
            return True
            
        except Exception as e:
            logger.error(f"创建配置模板文件失败: {e}")
            return False


# 全局实例
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """获取全局敏感配置管理器实例"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
