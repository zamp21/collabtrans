# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict
from typing import Optional
from pathlib import Path
import sys
from ..config.secrets_manager import get_secrets_manager

# 创建日志记录器
logger = logging.getLogger(__name__)

_AUTH_CONFIG_SINGLETON: Optional["AuthConfig"] = None


def _resolve_auth_config_path(config_file: str = "local_config.json") -> Path:
    """Resolve absolute path for local_config.json with deployment-aware priority.

    Priority:
      1) /etc/collabtrans/local_config.json (system)
      2) Executable directory (PyInstaller) / same-dir as binary
      3) Project root (development) fallback
    """
    # Absolute path: use directly
    p = Path(config_file)
    if p.is_absolute():
        logger.info(f"[AuthConfig] Using absolute path: {p}")
        return p

    system_dir = Path("/etc/collabtrans")
    system_cfg = system_dir / "local_config.json"
    if system_dir.exists() and system_cfg.exists():
        logger.info(f"[AuthConfig] Using system config: {system_cfg}")
        return system_cfg

    # Executable directory (PyInstaller)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(os.path.dirname(sys.executable))
        exe_cfg = exe_dir / "local_config.json"
        if exe_cfg.exists():
            logger.info(f"[AuthConfig] Using executable directory config: {exe_cfg}")
            return exe_cfg
        # fallback to cwd if exists
        cwd_cfg = Path.cwd() / "local_config.json"
        if cwd_cfg.exists():
            logger.info(f"[AuthConfig] Using working directory config: {cwd_cfg}")
            return cwd_cfg
        # default to executable dir path
        return exe_cfg

    # Development: project root (two levels up from this file)
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "local_config.json"


@dataclass
class AuthConfig:
    """认证配置类"""
    
    # LDAP 配置
    ldap_enabled: bool = False
    ldap_protocol: str = "ldap"  # "ldap" 或 "ldaps"
    ldap_host: str = "dc.example.com"
    ldap_port: int = 389
    ldap_bind_dn_template: str = "EXAMPLE\\{username}"
    ldap_base_dn: str = "OU=Users,DC=example,DC=com"
    ldap_user_filter: str = "(sAMAccountName={username})"
    ldap_tls_cacertfile: Optional[str] = None
    ldap_tls_verify: bool = True  # 是否验证TLS证书
    
    # LDAP 组配置
    ldap_admin_group_enabled: bool = False  # 是否启用管理员组查询
    ldap_glossary_group_enabled: bool = False   # 是否启用术语表组查询（新名）
    ldap_admin_group: str = "DocuTranslate-Admins"  # 管理员组名
    ldap_glossary_group: str = "DocuTranslate-Glossary"    # 术语表组名（新名）
    ldap_group_base_dn: str = "OU=Groups,DC=example,DC=com"  # 组搜索基础DN
    
    # 默认用户配置（LDAP 关闭时使用）
    default_username: str = "admin"
    default_password: str = "admin123"
    
    # Session 配置
    session_secret_key: str = "your-secret-key-change-in-production"
    session_cookie_name: str = "collabtrans_session"
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
            ldap_protocol=os.getenv("LDAP_PROTOCOL", "ldap"),
            ldap_host=os.getenv("LDAP_HOST", "dc.example.com"),
            ldap_port=int(os.getenv("LDAP_PORT", "389")),
            ldap_bind_dn_template=os.getenv("LDAP_BIND_DN_TEMPLATE", "EXAMPLE\\{username}"),
            ldap_base_dn=os.getenv("LDAP_BASE_DN", "OU=Users,DC=example,DC=com"),
            ldap_user_filter=os.getenv("LDAP_USER_FILTER", "(sAMAccountName={username})"),
            ldap_tls_cacertfile=os.getenv("LDAP_TLS_CACERTFILE"),
            ldap_tls_verify=os.getenv("LDAP_TLS_VERIFY", "true").lower() == "true",
            ldap_admin_group_enabled=os.getenv("LDAP_ADMIN_GROUP_ENABLED", "false").lower() == "true",
            # 仅支持新环境变量名
            ldap_glossary_group_enabled=os.getenv("LDAP_GLOSSARY_GROUP_ENABLED", "false").lower() == "true",
            ldap_admin_group=os.getenv("LDAP_ADMIN_GROUP", "DocuTranslate-Admins"),
            ldap_glossary_group=os.getenv("LDAP_GLOSSARY_GROUP", "DocuTranslate-Users"),
            ldap_group_base_dn=os.getenv("LDAP_GROUP_BASE_DN", "OU=Groups,DC=example,DC=com"),
            default_username=os.getenv("DEFAULT_USERNAME", "admin"),
            default_password=os.getenv("DEFAULT_PASSWORD", "admin123"),
            session_secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production"),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "collabtrans_session"),
            session_max_age=int(os.getenv("SESSION_MAX_AGE", "604800")),  # 7天
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            login_attempt_window=int(os.getenv("LOGIN_ATTEMPT_WINDOW", "300")),
            rate_limit_window=int(os.getenv("RATE_LIMIT_WINDOW", "300")),
        )
    
    def get_ldap_uri(self) -> str:
        """获取完整的LDAP URI"""
        return f"{self.ldap_protocol}://{self.ldap_host}:{self.ldap_port}"
    
    @classmethod
    def load_from_file(cls, config_file: str = "local_config.json") -> "AuthConfig":
        """Load configuration from grouped local_config.json and then load secrets"""
        config_path = _resolve_auth_config_path(config_file)
        
        logger.debug(f"[AuthConfig] Attempting to read config from: {config_path}")
        if not config_path.exists():
            # Auto-create from template if available (system first)
            system_dir = Path("/etc/collabtrans")
            system_tpl = system_dir / "local_config.json.template"
            try:
                if system_dir.exists() and system_tpl.exists():
                    import shutil
                    shutil.copy2(system_tpl, config_path)
                    try:
                        os.chmod(config_path, 0o640)
                    except Exception:
                        pass
                    logger.info(f"[AuthConfig] First deployment: created {config_path} from template {system_tpl}")
                else:
                    # Try executable dir template in frozen mode
                    if getattr(sys, 'frozen', False):
                        exe_dir = Path(os.path.dirname(sys.executable))
                        exe_tpl = exe_dir / "local_config.json.template"
                        if exe_tpl.exists():
                            import shutil
                            shutil.copy2(exe_tpl, config_path)
                            try:
                                os.chmod(config_path, 0o640)
                            except Exception:
                                pass
                            logger.info(f"[AuthConfig] Created {config_path} from executable template {exe_tpl}")
            except Exception as e:
                logger.warning(f"[AuthConfig] Failed to create config from template: {e}")

            if not config_path.exists():
                logger.info(f"[AuthConfig] Config file {config_path} does not exist, using default config")
                config = cls.from_env()
            else:
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        grouped = json.load(f)
                    config = cls._from_grouped_dict(grouped)
                except Exception as e:
                    logger.error(f"[AuthConfig] Failed to load grouped config after creation: {e}, using default config")
                    config = cls.from_env()
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    grouped = json.load(f)
                logger.debug(f"[AuthConfig] Loaded grouped config from file: {config_path}")
                config = cls._from_grouped_dict(grouped)
            except Exception as e:
                logger.error(f"[AuthConfig] Failed to load config file: {e}, using default config")
                config = cls.from_env()
        
        # 从敏感配置文件加载敏感信息
        config._load_auth_secrets()
        
        return config

    @classmethod
    def _from_grouped_dict(cls, data: dict) -> "AuthConfig":
        """Create AuthConfig from grouped local_config.json dictionary."""
        ldap = data.get("ldap", {})
        tls = ldap.get("tls", {})
        groups = ldap.get("groups", {})
        default_user = data.get("default_user", {})
        session = data.get("session", {})
        redis = data.get("redis", {})
        security = data.get("security", {})

        return cls(
            ldap_enabled=ldap.get("enabled", False),
            ldap_protocol=ldap.get("protocol", "ldap"),
            ldap_host=ldap.get("host", "dc.example.com"),
            ldap_port=int(ldap.get("port", 389)),
            ldap_bind_dn_template=ldap.get("bind_dn_template", "EXAMPLE\\{username}"),
            ldap_base_dn=ldap.get("base_dn", "OU=Users,DC=example,DC=com"),
            ldap_user_filter=ldap.get("user_filter", "(sAMAccountName={username})"),
            ldap_tls_cacertfile=tls.get("cacertfile"),
            ldap_tls_verify=bool(tls.get("verify", True)),
            ldap_admin_group_enabled=bool(groups.get("admin_enabled", False)),
            ldap_glossary_group_enabled=bool(groups.get("glossary_enabled", False)),
            ldap_admin_group=groups.get("admin_group", "DocuTranslate-Admins"),
            ldap_glossary_group=groups.get("glossary_group", "DocuTranslate-Glossary"),
            ldap_group_base_dn=groups.get("group_base_dn", "OU=Groups,DC=example,DC=com"),
            default_username=default_user.get("username", "admin"),
            default_password=default_user.get("password", "admin123"),
            session_secret_key=session.get("secret_key", "your-secret-key-change-in-production"),
            session_cookie_name=session.get("cookie_name", "collabtrans_session"),
            session_max_age=int(session.get("max_age", 604800)),
            redis_host=redis.get("host", "localhost"),
            redis_port=int(redis.get("port", 6379)),
            redis_db=int(redis.get("db", 0)),
            redis_password=redis.get("password"),
            max_login_attempts=int(security.get("max_login_attempts", 5)),
            login_attempt_window=int(security.get("login_attempt_window", 300)),
            rate_limit_window=int(security.get("rate_limit_window", 300)),
        )

    def to_grouped_dict(self) -> dict:
        """Serialize AuthConfig to grouped dictionary for local_config.json."""
        return {
            "ldap": {
                "enabled": self.ldap_enabled,
                "protocol": self.ldap_protocol,
                "host": self.ldap_host,
                "port": self.ldap_port,
                "bind_dn_template": self.ldap_bind_dn_template,
                "base_dn": self.ldap_base_dn,
                "user_filter": self.ldap_user_filter,
                "tls": {
                    "cacertfile": self.ldap_tls_cacertfile,
                    "verify": self.ldap_tls_verify,
                },
                "groups": {
                    "admin_enabled": self.ldap_admin_group_enabled,
                    "glossary_enabled": self.ldap_glossary_group_enabled,
                    "admin_group": self.ldap_admin_group,
                    "glossary_group": self.ldap_glossary_group,
                    "group_base_dn": self.ldap_group_base_dn,
                },
            },
            "default_user": {
                "username": self.default_username,
                "password": self.default_password,
            },
            "session": {
                "secret_key": self.session_secret_key,
                "cookie_name": self.session_cookie_name,
                "max_age": self.session_max_age,
            },
            "redis": {
                "host": self.redis_host,
                "port": self.redis_port,
                "db": self.redis_db,
                "password": self.redis_password,
            },
            "security": {
                "max_login_attempts": self.max_login_attempts,
                "login_attempt_window": self.login_attempt_window,
                "rate_limit_window": self.rate_limit_window,
            },
        }
    
    def _load_auth_secrets(self) -> None:
        """从敏感配置文件加载认证相关敏感信息"""
        try:
            secrets_manager = get_secrets_manager()
            auth_secrets = secrets_manager.get_auth_secrets()
            
            if auth_secrets:
                # 更新敏感信息
                if "default_password" in auth_secrets and auth_secrets["default_password"]:
                    self.default_password = auth_secrets["default_password"]
                    logger.info("从敏感配置加载了默认密码")
                
                if "session_secret_key" in auth_secrets and auth_secrets["session_secret_key"]:
                    self.session_secret_key = auth_secrets["session_secret_key"]
                    logger.info("从敏感配置加载了会话密钥")
                
                if "redis_password" in auth_secrets and auth_secrets["redis_password"]:
                    self.redis_password = auth_secrets["redis_password"]
                    logger.info("从敏感配置加载了Redis密码")
                    
        except Exception as e:
            logger.warning(f"加载认证敏感配置失败: {e}")
    
    def save_to_file(self, config_file: str = "local_config.json") -> bool:
        """Save grouped configuration to local_config.json (without secrets).

        Always prefer writing to /etc/collabtrans/local_config.json if the system directory exists.
        """
        try:
            # If config_file is absolute, use it directly
            if Path(config_file).is_absolute():
                config_path = Path(config_file)
            else:
                system_dir = Path("/etc/collabtrans")
                if system_dir.exists():
                    config_path = system_dir / "local_config.json"
                else:
                    config_path = _resolve_auth_config_path(config_file)

            logger.info(f"[AuthConfig] Preparing to write grouped config to: {config_path}")

            # 确保目录存在
            config_path.parent.mkdir(parents=True, exist_ok=True)

            grouped = self.to_grouped_dict()
            grouped.get("default_user", {}).pop("password", None)
            grouped.get("session", {}).pop("secret_key", None)
            grouped.get("redis", {}).pop("password", None)

            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(grouped, f, indent=2, ensure_ascii=False)

            # 系统目录下设置保守权限
            try:
                if str(config_path).startswith(str(system_dir)):
                    os.chmod(config_path, 0o640)
            except Exception:
                pass

            logger.info(f"[AuthConfig] Grouped config saved to {config_path}")
            return True
        except Exception as e:
            logger.error(f"[AuthConfig] Failed to save grouped config: {e}")
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
    def get_config(cls, config_file: str = "local_config.json") -> "AuthConfig":
        """获取配置（优先从文件，然后从环境变量）"""
        # 首先尝试从文件加载
        config = cls.load_from_file(config_file)
        
        # 如果文件中的配置是默认值，则检查环境变量是否有覆盖
        env_config = cls.from_env()
        
        # 合并策略：仅当对应环境变量显式设置时才覆盖文件值
        # 建立字段到环境变量名的映射（含兼容旧名）
        field_env_map = {
            'ldap_enabled': ['LDAP_ENABLED'],
            'ldap_protocol': ['LDAP_PROTOCOL'],
            'ldap_host': ['LDAP_HOST'],
            'ldap_port': ['LDAP_PORT'],
            'ldap_bind_dn_template': ['LDAP_BIND_DN_TEMPLATE'],
            'ldap_base_dn': ['LDAP_BASE_DN'],
            'ldap_user_filter': ['LDAP_USER_FILTER'],
            'ldap_tls_cacertfile': ['LDAP_TLS_CACERTFILE'],
            'ldap_tls_verify': ['LDAP_TLS_VERIFY'],
            'ldap_admin_group_enabled': ['LDAP_ADMIN_GROUP_ENABLED'],
            'ldap_admin_group': ['LDAP_ADMIN_GROUP'],
            # 仅支持新环境变量名
            'ldap_glossary_group_enabled': ['LDAP_GLOSSARY_GROUP_ENABLED'],
            'ldap_glossary_group': ['LDAP_GLOSSARY_GROUP'],
            'ldap_group_base_dn': ['LDAP_GROUP_BASE_DN'],
            'default_username': ['DEFAULT_USERNAME'],
            'default_password': ['DEFAULT_PASSWORD'],
            'session_secret_key': ['SESSION_SECRET_KEY'],
            'session_cookie_name': ['SESSION_COOKIE_NAME'],
            'session_max_age': ['SESSION_MAX_AGE'],
            'redis_host': ['REDIS_HOST'],
            'redis_port': ['REDIS_PORT'],
            'redis_db': ['REDIS_DB'],
            'redis_password': ['REDIS_PASSWORD'],
            'max_login_attempts': ['MAX_LOGIN_ATTEMPTS'],
            'login_attempt_window': ['LOGIN_ATTEMPT_WINDOW'],
            'rate_limit_window': ['RATE_LIMIT_WINDOW']
        }
        
        for field_name, env_vars in field_env_map.items():
            try:
                if any(os.getenv(var) is not None for var in env_vars):
                    env_value = getattr(env_config, field_name)
                    setattr(config, field_name, env_value)
                    logger.info(f"使用环境变量覆盖 {field_name} = {env_value}")
            except Exception:
                continue
        
        return config


# 模块级单例访问器，供路由的单项保存调用
def get_auth_config(config_file: str = "local_config.json") -> "AuthConfig":
    global _AUTH_CONFIG_SINGLETON
    if _AUTH_CONFIG_SINGLETON is None:
        try:
            _AUTH_CONFIG_SINGLETON = AuthConfig.load_from_file(config_file)
        except Exception as e:
            logger.warning(f"[AuthConfig] 初始化认证配置单例失败，使用默认值: {e}")
            _AUTH_CONFIG_SINGLETON = AuthConfig.from_env()
    return _AUTH_CONFIG_SINGLETON


def save_auth_config(config_file: str = "local_config.json") -> bool:
    try:
        cfg = get_auth_config(config_file)
        result = cfg.save_to_file(config_file)
        logger.info(f"[AuthConfig] save_auth_config 写盘结果: {result}")
        return result
    except Exception as e:
        logger.error(f"[AuthConfig] 保存认证配置失败: {e}")
        return False


def reload_auth_config(config_file: str = "local_config.json") -> "AuthConfig":
    """强制从磁盘重新加载认证配置，并刷新单例。"""
    global _AUTH_CONFIG_SINGLETON
    try:
        _AUTH_CONFIG_SINGLETON = AuthConfig.load_from_file(config_file)
        logger.info("[AuthConfig] 已从磁盘重新加载认证配置")
    except Exception as e:
        logger.error(f"[AuthConfig] 重新加载认证配置失败: {e}")
    return _AUTH_CONFIG_SINGLETON
