# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any
from pathlib import Path

# Create logger
logger = logging.getLogger(__name__)


@dataclass
class LDAPConfig:
    """LDAP configuration"""
    enabled: bool = False
    protocol: str = "ldap"
    host: str = "dc.example.com"
    port: int = 389
    bind_dn_template: str = "EXAMPLE\\{username}"
    base_dn: str = "OU=Users,DC=example,DC=com"
    user_filter: str = "(sAMAccountName={username})"
    tls: Dict[str, Any] = field(default_factory=lambda: {
        "cacertfile": None,
        "verify": True
    })
    groups: Dict[str, Any] = field(default_factory=lambda: {
        "admin_enabled": False,
        "glossary_enabled": False,
        "admin_group": "DocuTranslate-Admins",
        "glossary_group": "DocuTranslate-Glossary",
        "group_base_dn": "OU=Groups,DC=example,DC=com"
    })


@dataclass
class DefaultUserConfig:
    """Default user configuration"""
    username: str = "admin"


@dataclass
class SessionConfig:
    """Session configuration"""
    cookie_name: str = "collabtrans_session"
    max_age: int = 604800
    secret_key: str = "your-secret-key-change-in-production"


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


@dataclass
class SecurityConfig:
    """Security configuration"""
    max_login_attempts: int = 5
    login_attempt_window: int = 300
    rate_limit_window: int = 300
    password_recovery: bool = False


@dataclass
class MessagesConfig:
    """Messages configuration"""
    login_banner: str = "Welcome"
    usage_message: str = "Drop file and translate"


@dataclass
class HTTPSConfig:
    """HTTPS configuration"""
    enabled: bool = False
    cert_file: Optional[str] = None
    key_file: Optional[str] = None
    force_redirect: bool = False


@dataclass
class LocalConfig:
    """Local configuration class, manages system-level settings"""
    
    # LDAP settings
    ldap: LDAPConfig = field(default_factory=LDAPConfig)
    
    # Default user settings
    default_user: DefaultUserConfig = field(default_factory=DefaultUserConfig)
    
    # Session settings
    session: SessionConfig = field(default_factory=SessionConfig)
    
    # Redis settings
    redis: RedisConfig = field(default_factory=RedisConfig)
    
    # Security settings
    security: SecurityConfig = field(default_factory=SecurityConfig)
    
    # Messages settings
    messages: MessagesConfig = field(default_factory=MessagesConfig)
    
    # HTTPS settings
    https: HTTPSConfig = field(default_factory=HTTPSConfig)
    
    @classmethod
    def load_from_file(cls, config_file: str = "local_config.json") -> "LocalConfig":
        """Load local configuration from JSON file"""
        try:
            # Resolve the actual config file path
            from ..auth.config import _resolve_auth_config_path
            resolved_path = _resolve_auth_config_path(config_file)
            
            if resolved_path.exists():
                with open(resolved_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # Create configuration object
                config = cls()
                
                # Load LDAP configuration
                if 'ldap' in config_data:
                    config.ldap = LDAPConfig(**config_data['ldap'])
                
                # Load default user configuration
                if 'default_user' in config_data:
                    config.default_user = DefaultUserConfig(**config_data['default_user'])
                
                # Load session configuration
                if 'session' in config_data:
                    config.session = SessionConfig(**config_data['session'])
                
                # Load Redis configuration
                if 'redis' in config_data:
                    config.redis = RedisConfig(**config_data['redis'])
                
                # Load security configuration
                if 'security' in config_data:
                    config.security = SecurityConfig(**config_data['security'])
                
                # Load messages configuration
                if 'messages' in config_data:
                    config.messages = MessagesConfig(**config_data['messages'])
                
                # Load HTTPS configuration
                if 'https' in config_data:
                    config.https = HTTPSConfig(**config_data['https'])
                
                logger.debug(f"Loaded local configuration from {resolved_path}")
                return config
            else:
                logger.warning(f"Local configuration file {resolved_path} not found, using defaults")
                return cls()
                
        except Exception as e:
            logger.error(f"Error loading local configuration from {config_file}: {e}")
            return cls()
    
    def save_to_file(self, config_file: str = "local_config.json") -> bool:
        """Save local configuration to JSON file"""
        try:
            # Resolve the actual config file path
            from ..auth.config import _resolve_auth_config_path
            resolved_path = _resolve_auth_config_path(config_file)
            
            config_dict = {
                'ldap': asdict(self.ldap),
                'default_user': asdict(self.default_user),
                'session': asdict(self.session),
                'redis': asdict(self.redis),
                'security': asdict(self.security),
                'messages': asdict(self.messages),
                'https': asdict(self.https)
            }
            
            with open(resolved_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved local configuration to {resolved_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving local configuration to {resolved_path}: {e}")
            return False
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration dictionary"""
        return {
            'ldap': asdict(self.ldap),
            'default_user': asdict(self.default_user),
            'session': asdict(self.session),
            'redis': asdict(self.redis),
            'security': asdict(self.security),
            'messages': asdict(self.messages),
            'https': asdict(self.https)
        }
    
    def update_from_dict(self, config_data: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        try:
            # Update LDAP configuration
            if 'ldap' in config_data:
                for key, value in config_data['ldap'].items():
                    if hasattr(self.ldap, key):
                        setattr(self.ldap, key, value)
            
            # Update default user configuration
            if 'default_user' in config_data:
                for key, value in config_data['default_user'].items():
                    if hasattr(self.default_user, key):
                        setattr(self.default_user, key, value)
            
            # Update session configuration
            if 'session' in config_data:
                for key, value in config_data['session'].items():
                    if hasattr(self.session, key):
                        setattr(self.session, key, value)
            
            # Update Redis configuration
            if 'redis' in config_data:
                for key, value in config_data['redis'].items():
                    if hasattr(self.redis, key):
                        setattr(self.redis, key, value)
            
            # Update security configuration
            if 'security' in config_data:
                for key, value in config_data['security'].items():
                    if hasattr(self.security, key):
                        setattr(self.security, key, value)
            
            # Update messages configuration
            if 'messages' in config_data:
                for key, value in config_data['messages'].items():
                    if hasattr(self.messages, key):
                        setattr(self.messages, key, value)
            
            # Update HTTPS configuration
            if 'https' in config_data:
                for key, value in config_data['https'].items():
                    if hasattr(self.https, key):
                        setattr(self.https, key, value)
                        
        except Exception as e:
            logger.error(f"Error updating local configuration: {e}")
