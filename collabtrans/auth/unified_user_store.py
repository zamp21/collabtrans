# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

"""
Unified user storage system for CollabTrans
Combines admin and regular users into a single storage mechanism
"""

import json
import os
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime

from .password_manager import password_manager

logger = logging.getLogger(__name__)


class UnifiedUserRole(str, Enum):
    """Unified user roles for all user types"""
    # System roles (highest priority)
    SUPER_ADMIN = "super_admin"      # System super administrator
    ADMIN = "admin"                  # System administrator
    
    # Application roles
    APP_ADMIN = "app_admin"          # Application administrator (manages glossary, etc.)
    USER = "user"                    # Regular user
    
    # LDAP roles (when LDAP enabled)
    LDAP_ADMIN = "ldap_admin"        # LDAP administrator
    LDAP_APP = "ldap_app"            # LDAP application administrator
    LDAP_USER = "ldap_user"          # LDAP regular user


@dataclass
class UnifiedUser:
    """Unified user model for all user types"""
    username: str
    password_hash: str
    role: UnifiedUserRole
    display_name: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[str] = None
    last_login: Optional[str] = None
    is_active: bool = True
    is_system_user: bool = False  # Identifies system users (like admin)
    
    def is_admin(self) -> bool:
        """Check if user is administrator"""
        return self.role in [UnifiedUserRole.SUPER_ADMIN, UnifiedUserRole.ADMIN]
    
    def is_super_admin(self) -> bool:
        """Check if user is super administrator"""
        return self.role == UnifiedUserRole.SUPER_ADMIN
    
    def can_access_admin_settings(self) -> bool:
        """Check if user can access administrator settings"""
        return self.is_admin()
    
    def can_access_glossary_management(self) -> bool:
        """Check if user can access glossary management"""
        return self.role in [
            UnifiedUserRole.SUPER_ADMIN, 
            UnifiedUserRole.ADMIN, 
            UnifiedUserRole.APP_ADMIN,
            UnifiedUserRole.LDAP_ADMIN,
            UnifiedUserRole.LDAP_APP
        ]
    
    def get_allowed_settings(self) -> List[str]:
        """Get allowed settings items"""
        if self.is_admin():
            return [
                "workflow_settings",
                "parsing_settings", 
                "ai_settings",
                "translation_settings",
                "auth_settings",
                "system_settings",
                "glossary_settings"
            ]
        elif self.role in [UnifiedUserRole.APP_ADMIN, UnifiedUserRole.LDAP_APP]:
            return [
                "workflow_settings",
                "translation_settings",
                "glossary_settings"
            ]
        else:
            return [
                "workflow_settings",
                "translation_settings"
            ]


class UnifiedUserStore:
    """Unified user storage manager for all user types"""
    
    def __init__(self, filename: str = "local_users.json"):
        """Initialize unified user store"""
        from ..config.env_detector import is_production, get_dev_config_path, get_prod_config_path
        
        # 0) Environment-configured directory
        env_dir = os.environ.get("COLLABTRANS_CONFIG_PATH")
        if not env_dir and os.name == "nt":
            env_dir = r"C:\\Users\\Public\\collabtrans"
        if env_dir:
            env_file = Path(env_dir) / filename
            if env_file.exists():
                self.file_path = env_file
                logger.debug(f"[UnifiedUsers] Using env users file: {self.file_path}")
                self._cache: Optional[Dict[str, Any]] = None
                return
        
        # 1) Environment-based path (production or development)
        if is_production():
            # Production: use /etc/collabtrans/
            prod_file = get_prod_config_path(filename)
            if prod_file.exists():
                self.file_path = prod_file
                logger.debug(f"[UnifiedUsers] Using production users file: {self.file_path}")
                self._cache: Optional[Dict[str, Any]] = None
                return
            # Default to production path even if file doesn't exist
            self.file_path = prod_file
            logger.debug(f"[UnifiedUsers] Using production users file (will create): {self.file_path}")
        else:
            # Development: use project root
            dev_file = get_dev_config_path(filename)
            if dev_file.exists():
                self.file_path = dev_file
                logger.debug(f"[UnifiedUsers] Using development users file: {self.file_path}")
                self._cache: Optional[Dict[str, Any]] = None
                return
            # Default to development path even if file doesn't exist
            self.file_path = dev_file
            logger.debug(f"[UnifiedUsers] Using development users file (will create): {self.file_path}")
        
        # 2) Legacy fallback (for backward compatibility)
        system_dir = Path("/etc/collabtrans")
        system_file = system_dir / filename
        if system_dir.exists() and system_file.exists():
            self.file_path = system_file
            logger.debug(f"[UnifiedUsers] Using system users file (legacy): {self.file_path}")
        else:
            import sys
            if getattr(sys, 'frozen', False):
                exe_dir = Path(os.path.dirname(sys.executable))
                exe_file = exe_dir / filename
                self.file_path = exe_file if exe_file.exists() else exe_dir / filename
                logger.debug(f"[UnifiedUsers] Using executable users file (legacy): {self.file_path}")
            else:
                # repo root
                repo_root = Path(__file__).resolve().parents[2]
                self.file_path = (Path(filename) if Path(filename).is_absolute() else (repo_root / filename))
                logger.debug(f"[UnifiedUsers] Using repo users file (legacy): {self.file_path}")
        
        self._cache: Optional[Dict[str, Any]] = None
    
    def _load(self) -> Dict[str, Any]:
        """Load users data from file"""
        if self._cache is not None:
            return self._cache
        
        if not self.file_path.exists():
            logger.warning(f"[UnifiedUsers] Users file not found: {self.file_path}, using empty store")
            self._cache = {
                "_meta": {"version": 2, "description": "Unified user storage"},
                "users": {}
            }
            return self._cache
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                data = {"_meta": {"version": 2}, "users": {}}
            
            # Ensure metadata exists
            data.setdefault("_meta", {"version": 2})
            data.setdefault("users", {})
            
            # Migrate from version 1 to version 2 if needed
            if data["_meta"].get("version", 1) < 2:
                data = self._migrate_to_v2(data)
            
            self._cache = data
            logger.info(f"[UnifiedUsers] Loaded {len(self._cache['users'])} unified users")
            return self._cache
            
        except Exception as e:
            logger.error(f"[UnifiedUsers] Failed to load users file: {e}")
            self._cache = {"_meta": {"version": 2}, "users": {}}
            return self._cache
    
    def _migrate_to_v2(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from version 1 to version 2 format"""
        logger.info("[UnifiedUsers] Migrating from version 1 to version 2")
        
        # Update metadata
        data["_meta"] = {
            "version": 2,
            "description": "Unified user storage with admin and regular users",
            "migrated_at": datetime.now().isoformat()
        }
        
        # Migrate user data format
        users = data.get("users", {})
        for username, user_data in users.items():
            if isinstance(user_data, dict):
                # Add missing fields with defaults
                user_data.setdefault("created_at", datetime.now().isoformat())
                user_data.setdefault("last_login", None)
                user_data.setdefault("is_active", True)
                user_data.setdefault("is_system_user", False)
        
        return data
    
    def _save(self, data: Dict[str, Any]) -> bool:
        """Save users data to file"""
        try:
            # Ensure directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            self._cache = data
            logger.info(f"[UnifiedUsers] Saved {len(data['users'])} users to {self.file_path}")
            return True
            
        except Exception as e:
            logger.error(f"[UnifiedUsers] Failed to save users file: {e}")
            return False
    
    def get_user(self, username: str) -> Optional[UnifiedUser]:
        """Get user by username"""
        data = self._load()
        user_data = data["users"].get(username)
        
        if not user_data:
            return None
        
        try:
            return UnifiedUser(
                username=user_data["username"],
                password_hash=user_data["password_hash"],
                role=UnifiedUserRole(user_data["role"]),
                display_name=user_data.get("display_name"),
                email=user_data.get("email"),
                created_at=user_data.get("created_at"),
                last_login=user_data.get("last_login"),
                is_active=user_data.get("is_active", True),
                is_system_user=user_data.get("is_system_user", False)
            )
        except Exception as e:
            logger.error(f"[UnifiedUsers] Failed to parse user {username}: {e}")
            return None
    
    def create_user(self, username: str, password: str, role: UnifiedUserRole, 
                   display_name: Optional[str] = None, email: Optional[str] = None,
                   is_system_user: bool = False, skip_password_validation: bool = False) -> bool:
        """Create a new user"""
        if self.get_user(username):
            logger.warning(f"[UnifiedUsers] User {username} already exists")
            return False
        
        # Validate password strength unless explicitly skipped (for default passwords)
        if not skip_password_validation:
            is_valid, error_msg = password_manager.validate_password_strength(password)
            if not is_valid:
                logger.error(f"[UnifiedUsers] Password validation failed: {error_msg}")
                return False
        
        # Hash password
        password_hash = password_manager.hash_password(password, skip_validation=skip_password_validation)
        
        # Create user
        user = UnifiedUser(
            username=username,
            password_hash=password_hash,
            role=role,
            display_name=display_name or username,
            email=email,
            created_at=datetime.now().isoformat(),
            last_login=None,
            is_active=True,
            is_system_user=is_system_user
        )
        
        # Save to storage
        data = self._load()
        data["users"][username] = asdict(user)
        
        return self._save(data)
    
    def verify_credentials(self, username: str, password: str) -> bool:
        """Verify user credentials"""
        user = self.get_user(username)
        if not user or not user.is_active:
            return False
        
        return password_manager.verify_password(password, user.password_hash)
    
    def update_password(self, username: str, new_password: str) -> bool:
        """Update user password"""
        user = self.get_user(username)
        if not user:
            return False
        
        # Validate password strength
        is_valid, error_msg = password_manager.validate_password_strength(new_password)
        if not is_valid:
            logger.error(f"[UnifiedUsers] Password validation failed: {error_msg}")
            return False
        
        # Hash new password
        password_hash = password_manager.hash_password(new_password)
        
        # Update user
        data = self._load()
        if username in data["users"]:
            data["users"][username]["password_hash"] = password_hash
            return self._save(data)
        
        return False
    
    def update_last_login(self, username: str) -> bool:
        """Update user's last login time"""
        data = self._load()
        if username in data["users"]:
            data["users"][username]["last_login"] = datetime.now().isoformat()
            return self._save(data)
        return False
    
    def delete_user(self, username: str) -> bool:
        """Delete a user (cannot delete system users)"""
        user = self.get_user(username)
        if not user:
            return False
        
        if user.is_system_user:
            logger.warning(f"[UnifiedUsers] Cannot delete system user: {username}")
            return False
        
        data = self._load()
        if username in data["users"]:
            del data["users"][username]
            return self._save(data)
        
        return False
    
    def list_users(self) -> List[UnifiedUser]:
        """List all users"""
        data = self._load()
        users = []
        
        for username, user_data in data["users"].items():
            user = self.get_user(username)
            if user:
                users.append(user)
        
        return users
    
    def get_users_by_role(self, role: UnifiedUserRole) -> List[UnifiedUser]:
        """Get users by role"""
        return [user for user in self.list_users() if user.role == role]
    
    def migrate_admin_from_secrets(self, admin_username: str, admin_password: str) -> bool:
        """Migrate admin user from secrets config to unified storage"""
        logger.info(f"[UnifiedUsers] Migrating admin user: {admin_username}")
        
        # Check if admin already exists
        if self.get_user(admin_username):
            logger.info(f"[UnifiedUsers] Admin user {admin_username} already exists in unified storage")
            return True
        
        # Create admin user in unified storage (skip password validation for default passwords)
        return self.create_user(
            username=admin_username,
            password=admin_password,
            role=UnifiedUserRole.SUPER_ADMIN,
            display_name="Administrator",
            is_system_user=True,
            skip_password_validation=True
        )


# Global instance
_unified_user_store: Optional[UnifiedUserStore] = None


def get_unified_user_store() -> UnifiedUserStore:
    """Get global unified user store instance"""
    global _unified_user_store
    if _unified_user_store is None:
        _unified_user_store = UnifiedUserStore()
    return _unified_user_store
