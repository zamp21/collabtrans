# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path

# 创建日志记录器
logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """认证配置类"""
    
    # LDAP 配置
    ldap_enabled: bool = False
    ldap_uri: str = "ldap://dc.example.com:389"
    ldap_bind_dn_template: str = "EXAMPLE\\{username}"
    ldap_base_dn: str = "OU=Users,DC=example,DC=com"
    ldap_user_filter: str = "(sAMAccountName={username})"
    ldap_tls_cacertfile: Optional[str] = None
    
    # 默认用户配置（LDAP 关闭时使用）
    default_username: str = "admin"
    default_password: str = "admin123"
    
    # Session 配置
    session_secret_key: str = "your-secret-key-change-in-production"
    session_cookie_name: str = "docutranslate_session"
    session_max_age: int = 3600 * 24 * 7  # 7天
    
    # Redis 配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # 安全配置
    max_login_attempts: int = 5
    login_attempt_window: int = 300  # 5分钟
    rate_limit_window: int = 300  # 5分钟
    
    @classmethod
    def from_env(cls) -> "AuthConfig":
        """从环境变量创建配置"""
        return cls(
            ldap_enabled=os.getenv("LDAP_ENABLED", "false").lower() == "true",
            ldap_uri=os.getenv("LDAP_URI", "ldap://dc.example.com:389"),
            ldap_bind_dn_template=os.getenv("LDAP_BIND_DN_TEMPLATE", "EXAMPLE\\{username}"),
            ldap_base_dn=os.getenv("LDAP_BASE_DN", "OU=Users,DC=example,DC=com"),
            ldap_user_filter=os.getenv("LDAP_USER_FILTER", "(sAMAccountName={username})"),
            ldap_tls_cacertfile=os.getenv("LDAP_TLS_CACERTFILE"),
            default_username=os.getenv("DEFAULT_USERNAME", "admin"),
            default_password=os.getenv("DEFAULT_PASSWORD", "admin123"),
            session_secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production"),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "docutranslate_session"),
            session_max_age=int(os.getenv("SESSION_MAX_AGE", "604800")),  # 7天
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            login_attempt_window=int(os.getenv("LOGIN_ATTEMPT_WINDOW", "300")),
            rate_limit_window=int(os.getenv("RATE_LIMIT_WINDOW", "300")),
        )
    
    @classmethod
    def load_from_file(cls, config_file: str = "auth_config.json") -> "AuthConfig":
        """从配置文件加载配置"""
        config_path = Path(config_file)
        
        if not config_path.exists():
            logger.info(f"配置文件 {config_file} 不存在，使用默认配置")
            return cls.from_env()
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            logger.info(f"从配置文件 {config_file} 加载配置")
            return cls(**config_data)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return cls.from_env()
    
    def save_to_file(self, config_file: str = "auth_config.json") -> bool:
        """保存配置到文件"""
        config_path = Path(config_file)
        
        try:
            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 转换为字典并保存
            config_dict = asdict(self)
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"配置已保存到 {config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def update_from_dict(self, config_data: dict) -> None:
        """从字典更新配置"""
        for key, value in config_data.items():
            if hasattr(self, key):
                # 跳过密码字段的更新（避免被***覆盖）
                if key == "default_password" and value == "***":
                    logger.info(f"跳过密码字段更新，保持原值")
                    continue
                
                # 特殊处理布尔值
                if key == "ldap_enabled" and isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes", "on")
                # 特殊处理整数
                elif key in ["session_max_age", "max_login_attempts", "login_attempt_window", "rate_limit_window"]:
                    value = int(value)
                # 特殊处理空字符串
                elif key == "ldap_tls_cacertfile" and value == "":
                    value = None
                
                setattr(self, key, value)
                logger.info(f"更新配置 {key} = {value}")
    
    @classmethod
    def get_config(cls, config_file: str = "auth_config.json") -> "AuthConfig":
        """获取配置（优先从文件，然后从环境变量）"""
        # 首先尝试从文件加载
        config = cls.load_from_file(config_file)
        
        # 如果文件中的配置是默认值，则检查环境变量是否有覆盖
        env_config = cls.from_env()
        
        # 合并配置：文件配置优先，环境变量作为覆盖
        for field_name in config.__dataclass_fields__:
            env_value = getattr(env_config, field_name)
            file_value = getattr(config, field_name)
            
            # 如果环境变量不是默认值，则使用环境变量
            if env_value != getattr(cls(), field_name):
                setattr(config, field_name, env_value)
                logger.info(f"使用环境变量覆盖 {field_name} = {env_value}")
        
        return config
