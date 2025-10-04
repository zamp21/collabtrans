import json
import os
import logging
import secrets
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple
import hashlib

logger = logging.getLogger(__name__)


class LocalUserRole(str, Enum):
    ADMIN = "admin"            # Full admin (cannot change super admin password)
    APP_ADMIN = "app_admin"    # Manage prompts and glossary
    USER = "user"              # Regular user


@dataclass
class LocalUser:
    username: str
    password_hash: str  # stored as: pbkdf2_sha256$iterations$salt_hex$hash_hex
    role: LocalUserRole
    display_name: Optional[str] = None
    email: Optional[str] = None


class LocalUserStore:
    """Manages local users with secure password hashing and JSON persistence.

    Search/Write priority similar to SecretsManager:
    1) /etc/collabtrans/local_users.json if directory exists
    2) Executable directory (when frozen)
    3) Project root (repo root)
    """

    def __init__(self, filename: str = "local_users.json") -> None:
        system_dir = Path("/etc/collabtrans")
        system_file = system_dir / filename
        self.file_path: Path
        if system_dir.exists() and system_file.exists():
            self.file_path = system_file
            logger.info(f"[LocalUsers] Using system users file: {self.file_path}")
        else:
            import sys
            if getattr(sys, 'frozen', False):
                exe_dir = Path(os.path.dirname(sys.executable))
                exe_file = exe_dir / filename
                self.file_path = exe_file if exe_file.exists() else exe_dir / filename
                logger.info(f"[LocalUsers] Using executable users file: {self.file_path}")
            else:
                # repo root
                repo_root = Path(__file__).resolve().parents[2]
                self.file_path = (Path(filename) if Path(filename).is_absolute() else (repo_root / filename))
                logger.info(f"[LocalUsers] Using repo users file: {self.file_path}")
        self._cache: Optional[Dict[str, Dict]] = None

    # ===== Password hashing =====
    @staticmethod
    def _hash_password(password: str, iterations: int = 210_000) -> str:
        if not isinstance(password, str) or not password:
            raise ValueError("Password must be non-empty string")
        salt = secrets.token_bytes(16)
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"

    @staticmethod
    def _verify_password(password: str, encoded: str) -> bool:
        try:
            algo, iter_str, salt_hex, hash_hex = encoded.split('$', 3)
            if algo != 'pbkdf2_sha256':
                return False
            iterations = int(iter_str)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
            dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
            # constant time compare - use hmac.compare_digest for compatibility
            import hmac
            return hmac.compare_digest(dk, expected)
        except Exception:
            return False

    # ===== Persistence =====
    def _load(self) -> Dict[str, Dict]:
        if self._cache is not None:
            return self._cache
        if not self.file_path.exists():
            logger.warning(f"[LocalUsers] Users file not found: {self.file_path}, using empty store")
            self._cache = {"_meta": {"version": 1}, "users": {}}
            return self._cache
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if not isinstance(data, dict):
                data = {"_meta": {"version": 1}, "users": {}}
            data.setdefault("_meta", {"version": 1})
            data.setdefault("users", {})
            self._cache = data
            logger.info(f"[LocalUsers] Loaded {len(self._cache['users'])} local users")
            return self._cache
        except Exception as e:
            logger.error(f"[LocalUsers] Failed to load users file: {e}")
            self._cache = {"_meta": {"version": 1}, "users": {}}
            return self._cache

    def _save(self, data: Dict) -> bool:
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._cache = data
            # set safe permissions for system dir
            try:
                if str(self.file_path).startswith('/etc/collabtrans'):
                    os.chmod(self.file_path, 0o640)
            except Exception:
                pass
            logger.info(f"[LocalUsers] Saved users file to: {self.file_path}")
            return True
        except Exception as e:
            logger.error(f"[LocalUsers] Failed to save users file: {e}")
            return False

    # ===== CRUD =====
    def list_users(self) -> Dict[str, Dict]:
        return self._load().get("users", {})

    def get_user(self, username: str) -> Optional[LocalUser]:
        data = self._load().get("users", {}).get(username)
        if not data:
            return None
        try:
            return LocalUser(
                username=username,
                password_hash=data.get("password_hash", ""),
                role=LocalUserRole(data.get("role", LocalUserRole.USER)),
                display_name=data.get("display_name"),
                email=data.get("email")
            )
        except Exception:
            return None

    def create_user(self, username: str, password: str, role: LocalUserRole, display_name: Optional[str] = None, email: Optional[str] = None) -> bool:
        users = self._load()
        if username in users.get("users", {}):
            raise ValueError("User already exists")
        password_hash = self._hash_password(password)
        users["users"][username] = {
            "password_hash": password_hash,
            "role": role.value,
            "display_name": display_name or username,
            "email": email or None
        }
        return self._save(users)

    def update_user(self, username: str, role: Optional[LocalUserRole] = None, display_name: Optional[str] = None, email: Optional[str] = None) -> bool:
        users = self._load()
        if username not in users.get("users", {}):
            raise ValueError("User not found")
        u = users["users"][username]
        if role is not None:
            u["role"] = role.value
        if display_name is not None:
            u["display_name"] = display_name
        if email is not None:
            u["email"] = email
        return self._save(users)

    def reset_password(self, username: str, new_password: str) -> bool:
        users = self._load()
        if username not in users.get("users", {}):
            raise ValueError("User not found")
        users["users"][username]["password_hash"] = self._hash_password(new_password)
        return self._save(users)

    def delete_user(self, username: str) -> bool:
        users = self._load()
        if username in users.get("users", {}):
            del users["users"][username]
            return self._save(users)
        return True

    # ===== Auth =====
    def verify_credentials(self, username: str, password: str) -> Tuple[bool, Optional[LocalUser]]:
        user = self.get_user(username)
        if not user:
            return False, None
        ok = self._verify_password(password, user.password_hash)
        return ok, user if ok else None

    # ===== Template =====
    def ensure_template(self) -> Path:
        template = self.file_path.parent / f"{self.file_path.stem}.template"
        if template.exists():
            return template
        data = {
            "_comment": "Local users template - copy to local_users.json and edit.",
            "_warning": "Do not commit this file to git.",
            "_meta": {"version": 1},
            "users": {
                "editor": {
                    "password_hash": self._hash_password("change_me_please"),
                    "role": LocalUserRole.APP_ADMIN.value,
                    "display_name": "Editor",
                    "email": ""
                }
            }
        }
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(template, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"[LocalUsers] Created template: {template}")
            return template
        except Exception as e:
            logger.error(f"[LocalUsers] Failed to create template: {e}")
            return template


# Singleton accessor
_local_users_store: Optional[LocalUserStore] = None

def get_local_user_store() -> LocalUserStore:
    global _local_users_store
    if _local_users_store is None:
        _local_users_store = LocalUserStore()
    return _local_users_store
