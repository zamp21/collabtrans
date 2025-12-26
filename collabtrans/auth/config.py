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

# Create logger
logger = logging.getLogger(__name__)

_AUTH_CONFIG_SINGLETON: Optional["AuthConfig"] = None


def _resolve_auth_config_path(config_file: str = "local_config.json") -> Path:
    """Resolve absolute path for local_config.json with deployment-aware priority.

    Priority:
      Windows/Linux override:
        0) COLLABTRANS_CONFIG_PATH env dir if set (Windows default: C:\\Users\\Public\\collabtrans)
      Linux:
        1) /etc/collabtrans/local_config.json (system)
      Common:
        2) Executable directory (PyInstaller) / same-dir as binary (or cwd)
        3) Project root (development) fallback
    """
    # Absolute path: use directly
    p = Path(config_file)
    if p.is_absolute():
        logger.debug(f"[AuthConfig] Using absolute path: {p}")
        return p

    # 0) Environment-configured directory (cross-platform override)
    env_dir = os.environ.get("COLLABTRANS_CONFIG_PATH")
    # Windows default runtime configuration directory
    if not env_dir and os.name == "nt":
        env_dir = r"C:\\Users\\Public\\collabtrans"
    if env_dir:
        env_cfg = Path(env_dir) / "local_config.json"
        if env_cfg.exists():
            logger.debug(f"[AuthConfig] Using env config: {env_cfg}")
            return env_cfg

    if os.name != "nt":
        system_dir = Path("/etc/collabtrans")
        system_cfg = system_dir / "local_config.json"
        if system_dir.exists() and system_cfg.exists():
            logger.debug(f"[AuthConfig] Using system config: {system_cfg}")
            return system_cfg

    # Executable directory (PyInstaller)
    if getattr(sys, 'frozen', False):
        exe_dir = Path(os.path.dirname(sys.executable))
        exe_cfg = exe_dir / "local_config.json"
        if exe_cfg.exists():
            logger.debug(f"[AuthConfig] Using executable directory config: {exe_cfg}")
            return exe_cfg
        # fallback to cwd if exists
        cwd_cfg = Path.cwd() / "local_config.json"
        if cwd_cfg.exists():
            logger.debug(f"[AuthConfig] Using working directory config: {cwd_cfg}")
            return cwd_cfg
        # default to executable dir path
        return exe_cfg

    # Development: project root (two levels up from this file)
    project_root = Path(__file__).resolve().parents[2]
    return project_root / "local_config.json"


@dataclass
class AuthConfig:
    """Authentication configuration class"""
    
    # LDAP configuration
    ldap_enabled: bool = False
    ldap_protocol: str = "ldap"  # "ldap" or "ldaps"
    ldap_host: str = "dc.example.com"
    ldap_port: int = 389
    ldap_bind_dn_template: str = "EXAMPLE\\{username}"
    ldap_base_dn: str = "OU=Users,DC=example,DC=com"
    ldap_user_filter: str = "(sAMAccountName={username})"
    ldap_tls_cacertfile: Optional[str] = None
    ldap_tls_verify: bool = True  # Whether to verify TLS certificate
    
    # LDAP group configuration
    ldap_admin_group_enabled: bool = False  # Whether to enable admin group query
    ldap_glossary_group_enabled: bool = False   # Whether to enable glossary group query (new name)
    ldap_admin_group: str = "DocuTranslate-Admins"  # Admin group name
    ldap_glossary_group: str = "DocuTranslate-Glossary"    # Glossary group name (new name)
    ldap_group_base_dn: str = "OU=Groups,DC=example,DC=com"  # Group search base DN
    
    # Default user configuration (used when LDAP is disabled)
    default_username: str = "admin"
    
    # Session configuration
    session_secret_key: str = "your-secret-key-change-in-production"
    session_cookie_name: str = "collabtrans_session"
    session_max_age: int = 3600 * 24 * 7  # 7 days
    
    # Redis configuration
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # Security configuration
    max_login_attempts: int = 5
    login_attempt_window: int = 300  # 5 minutes
    rate_limit_window: int = 300  # 5 minutes
    
    # Message configuration
    login_banner: str = "Welcome to document translation system."
    usage_message: str = "Please drop your file and click Translate."
    
    @classmethod
    def from_env(cls) -> "AuthConfig":
        """Create configuration from environment variables"""
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
            # Only support new environment variable names
            ldap_glossary_group_enabled=os.getenv("LDAP_GLOSSARY_GROUP_ENABLED", "false").lower() == "true",
            ldap_admin_group=os.getenv("LDAP_ADMIN_GROUP", "DocuTranslate-Admins"),
            ldap_glossary_group=os.getenv("LDAP_GLOSSARY_GROUP", "DocuTranslate-Users"),
            ldap_group_base_dn=os.getenv("LDAP_GROUP_BASE_DN", "OU=Groups,DC=example,DC=com"),
            default_username=os.getenv("DEFAULT_USERNAME", "admin"),
            session_secret_key=os.getenv("SESSION_SECRET_KEY", "your-secret-key-change-in-production"),
            session_cookie_name=os.getenv("SESSION_COOKIE_NAME", "collabtrans_session"),
            session_max_age=int(os.getenv("SESSION_MAX_AGE", "604800")),  # 7 days
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD"),
            max_login_attempts=int(os.getenv("MAX_LOGIN_ATTEMPTS", "5")),
            login_attempt_window=int(os.getenv("LOGIN_ATTEMPT_WINDOW", "300")),
            rate_limit_window=int(os.getenv("RATE_LIMIT_WINDOW", "300")),
            login_banner=os.getenv("LOGIN_BANNER", "Welcome to document translation system."),
            usage_message=os.getenv("USAGE_MESSAGE", "Please drop your file and click Translate."),
        )
    
    def get_ldap_uri(self) -> str:
        """Get complete LDAP URI"""
        return f"{self.ldap_protocol}://{self.ldap_host}:{self.ldap_port}"
    
    @classmethod
    def load_from_file(cls, config_file: str = "local_config.json") -> "AuthConfig":
        """Load configuration from grouped local_config.json and then load secrets.
        Prefer the most recently modified existing config among system/executable/cwd/project.
        """
        # Build candidate paths
        system_dir = Path("/etc/collabtrans")
        system_cfg = system_dir / "local_config.json"
        exe_cfg = None
        if getattr(sys, 'frozen', False):
            exe_dir = Path(os.path.dirname(sys.executable))
            exe_cfg = exe_dir / "local_config.json"
        cwd_cfg = Path.cwd() / "local_config.json"
        project_root = Path(__file__).resolve().parents[2]
        proj_cfg = project_root / "local_config.json"

        candidates = []
        for p in [system_cfg, exe_cfg, cwd_cfg, proj_cfg]:
            if p is not None and p.exists():
                try:
                    mtime = p.stat().st_mtime
                except Exception:
                    mtime = 0
                candidates.append((mtime, p))

        # Choose newest existing config, otherwise fall back to resolved path
        if candidates:
            candidates.sort(reverse=True)
            config_path = candidates[0][1]
            logger.debug(f"[AuthConfig] Selected newest config: {config_path}")
        else:
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
        
        # Load sensitive information from sensitive configuration file
        
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
        messages = data.get("messages", {})

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
            login_banner=messages.get("login_banner", "Welcome to document translation system."),
            usage_message=messages.get("usage_message", "Please drop your file and click Translate."),
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
            "messages": {
                "login_banner": self.login_banner,
                "usage_message": self.usage_message,
            },
        }
    
    
    def save_to_file(self, config_file: str = "local_config.json") -> bool:
        """Save grouped configuration to local_config.json (without secrets).

        Write-order policy (mirrors AppConfig/global_config):
        1) /etc/collabtrans/local_config.json (if dir exists and writable)
        2) Resolved path by _resolve_auth_config_path (executable dir or cwd)
        3) Explicit fallback to CWD local_config.json
        """
        grouped = self.to_grouped_dict()
        grouped.get("session", {}).pop("secret_key", None)
        grouped.get("redis", {}).pop("password", None)

        candidates = []
        system_dir = Path("/etc/collabtrans")
        candidates.append(system_dir / "local_config.json")
        try:
            candidates.append(_resolve_auth_config_path(config_file))
        except Exception:
            pass
        candidates.append(Path.cwd() / "local_config.json")

        last_error = None
        for path in candidates:
            try:
                logger.debug(f"[AuthConfig] Attempting to save to: {path}")
                logger.debug(f"[AuthConfig] Path exists: {path.exists()}, parent exists: {path.parent.exists()}")
                logger.debug(f"[AuthConfig] Path permissions: {oct(path.stat().st_mode) if path.exists() else 'N/A'}")
                
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(grouped, f, indent=2, ensure_ascii=False)
                # conservative permissions for system dir
                try:
                    if str(path).startswith(str(system_dir)):
                        os.chmod(path, 0o640)
                        logger.debug(f"[AuthConfig] Set permissions 640 for {path}")
                except Exception as perm_e:
                    logger.warning(f"[AuthConfig] Failed to set permissions for {path}: {perm_e}")
                logger.info(f"[AuthConfig] Grouped config saved to {path}")
                return True
            except Exception as e:
                last_error = e
                logger.warning(f"[AuthConfig] Write failed, trying next location: {path} -> {e}")
                logger.debug(f"[AuthConfig] Exception details: {type(e).__name__}: {e}")
                continue

        logger.error(f"[AuthConfig] Failed to save grouped config after fallbacks: {last_error}")
        return False
    
    def update_from_dict(self, config_data: dict) -> None:
        """Update configuration from dictionary"""
        for key, value in config_data.items():
            if hasattr(self, key):
                # Special handling for boolean values
                if key == "ldap_enabled" and isinstance(value, str):
                    value = value.lower() in ("true", "1", "yes", "on")
                # Special handling for integers
                elif key in ["session_max_age", "max_login_attempts", "login_attempt_window", "rate_limit_window"]:
                    value = int(value)
                # Special handling for empty strings
                elif key == "ldap_tls_cacertfile" and value == "":
                    value = None
                
                setattr(self, key, value)
                logger.info(f"Updated configuration {key} = {value}")
    
    @classmethod
    def get_config(cls, config_file: str = "local_config.json") -> "AuthConfig":
        """Get configuration (prioritize file, then environment variables)"""
        # First try to load from file
        config = cls.load_from_file(config_file)
        
        # If configuration in file is default value, check if environment variables have overrides
        env_config = cls.from_env()
        
        # Merge strategy: only override file values when corresponding environment variables are explicitly set
        # Build field to environment variable name mapping (including compatibility with old names)
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
            # Only support new environment variable names
            'ldap_glossary_group_enabled': ['LDAP_GLOSSARY_GROUP_ENABLED'],
            'ldap_glossary_group': ['LDAP_GLOSSARY_GROUP'],
            'ldap_group_base_dn': ['LDAP_GROUP_BASE_DN'],
            'default_username': ['DEFAULT_USERNAME'],
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
                    logger.info(f"Using environment variable override {field_name} = {env_value}")
            except Exception:
                continue
        
        return config


# Module-level singleton accessor for route single-item save calls
def get_auth_config(config_file: str = "local_config.json") -> "AuthConfig":
    global _AUTH_CONFIG_SINGLETON
    if _AUTH_CONFIG_SINGLETON is None:
        try:
            _AUTH_CONFIG_SINGLETON = AuthConfig.load_from_file(config_file)
        except Exception as e:
            logger.warning(f"[AuthConfig] Failed to initialize authentication configuration singleton, using default values: {e}")
            _AUTH_CONFIG_SINGLETON = AuthConfig.from_env()
    return _AUTH_CONFIG_SINGLETON


def save_auth_config(config_file: str = "local_config.json") -> bool:
    try:
        global _AUTH_CONFIG_SINGLETON
        # Prefer in-memory singleton (which may have recent updates) to avoid stale writes
        cfg = _AUTH_CONFIG_SINGLETON if _AUTH_CONFIG_SINGLETON is not None else AuthConfig.get_config(config_file)
        result = cfg.save_to_file(config_file)
        logger.info(f"[AuthConfig] save_auth_config write result: {result}")
        return result
    except Exception as e:
        logger.error(f"[AuthConfig] Failed to save auth config: {e}")
        return False


def reload_auth_config(config_file: str = "local_config.json") -> "AuthConfig":
    """Force reload authentication configuration from disk and refresh singleton."""
    global _AUTH_CONFIG_SINGLETON
    try:
        _AUTH_CONFIG_SINGLETON = AuthConfig.load_from_file(config_file)
        logger.info("[AuthConfig] Reloaded authentication configuration from disk")
    except Exception as e:
        logger.error(f"[AuthConfig] Failed to reload authentication configuration: {e}")
    return _AUTH_CONFIG_SINGLETON
