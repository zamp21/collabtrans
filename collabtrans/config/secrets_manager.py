# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Create logger
logger = logging.getLogger(__name__)


class SecretsManager:
    """Sensitive configuration manager - manages API keys and other sensitive information"""
    
    def __init__(self, secrets_file: str = "local_secrets.json"):
        """
        Initialize sensitive configuration manager
        
        Args:
            secrets_file: Sensitive configuration file path
        """
        # Configuration file priority:
        # Windows/Linux override:
        # 0. COLLABTRANS_CONFIG_PATH env dir if set (Windows default: C:\\Users\\Public\\collabtrans)
        # Linux:
        # 1. /etc/collabtrans/local_secrets.json (system configuration)
        # Common:
        # 2. local_secrets.json in executable directory (packaged configuration)
        # 3. local_secrets.json in project root/current directory (development environment)
        
        # 0) Environment-configured directory (cross-platform override)
        env_dir = os.environ.get("COLLABTRANS_CONFIG_PATH")
        # Windows default runtime configuration directory
        if not env_dir and os.name == "nt":
            env_dir = r"C:\\Users\\Public\\collabtrans"
        if env_dir:
            env_path = Path(env_dir) / "local_secrets.json"
            # If exists, prefer it; if not, set as target path for creation
            if env_path.exists():
                self.secrets_file = env_path
                logger.debug(f"Using env dir secrets config: {env_path}")
                self._secrets_cache = None
                return
            else:
                # Defer to other locations, but remember env target for save
                self.secrets_file = env_path

        if os.name != "nt":
            system_secrets_file = "/etc/collabtrans/local_secrets.json"
            system_secrets_template = "/etc/collabtrans/local_secrets.json.template"
            system_dir_exists = os.path.exists("/etc/collabtrans")
            if system_dir_exists:
                if os.path.exists(system_secrets_file):
                    self.secrets_file = Path(system_secrets_file)
                    logger.debug(f"Using system secrets config: {system_secrets_file}")
                else:
                    # Auto-create from template if available
                    if os.path.exists(system_secrets_template):
                        try:
                            import shutil
                            shutil.copy2(system_secrets_template, system_secrets_file)
                            # Set conservative permissions: rw-r----- (0640)
                            try:
                                os.chmod(system_secrets_file, 0o640)
                            except Exception:
                                pass
                            self.secrets_file = Path(system_secrets_file)
                            logger.info(
                                f"First deployment: created {system_secrets_file} from template {system_secrets_template}"
                            )
                        except Exception as copy_err:
                            logger.warning(
                                f"Failed to create system secrets from template: {copy_err}. Will try other locations."
                            )
                    # If still not set, fall through to other locations
        else:
            # Try to load configuration file from executable directory
            import sys
            if getattr(sys, 'frozen', False):
                # PyInstaller packaged environment
                exe_dir = os.path.dirname(sys.executable)
                exe_secrets_file = os.path.join(exe_dir, "local_secrets.json")
                if os.path.exists(exe_secrets_file):
                    self.secrets_file = Path(exe_secrets_file)
                    logger.debug(f"Using executable directory secrets config: {exe_secrets_file}")
                else:
                    # Fix relative path to repository root directory to avoid writing to wrong location due to working directory changes
                    proj_root = Path(__file__).resolve().parents[2]
                    sf = Path(secrets_file)
                    self.secrets_file = sf if sf.is_absolute() else (proj_root / sf)
                    logger.debug(f"Using local secrets config: {self.secrets_file}")
            else:
                # Development environment
                proj_root = Path(__file__).resolve().parents[2]
                sf = Path(secrets_file)
                self.secrets_file = sf if sf.is_absolute() else (proj_root / sf)
                logger.debug(f"Using local secrets config: {self.secrets_file}")
        self._secrets_cache: Optional[Dict[str, Any]] = None
        
    def load_secrets(self) -> Dict[str, Any]:
        """
        Load sensitive configuration
        
        Returns:
            Sensitive configuration dictionary, returns empty dictionary if file does not exist
        """
        if self._secrets_cache is not None:
            return self._secrets_cache
            
        if not self.secrets_file.exists():
            # In PyInstaller environment, avoid pointing to /tmp/_MEI* directory
            try:
                import sys as _sm_sys
                if getattr(_sm_sys, 'frozen', False):
                    exe_dir = Path(os.path.dirname(_sm_sys.executable))
                    fallback = exe_dir / self.secrets_file.name
                    if fallback != self.secrets_file:
                        logger.debug(f"Secrets file not found at {self.secrets_file}, trying executable dir: {fallback}")
                        if fallback.exists():
                            self.secrets_file = fallback
            except Exception:
                pass

        if not self.secrets_file.exists():
            logger.warning(f"Secrets file {self.secrets_file} not found, using empty configuration")
            self._secrets_cache = {}
            return self._secrets_cache
            
        try:
            with open(self.secrets_file, 'r', encoding='utf-8') as f:
                secrets = json.load(f)

            # Normalize structure: add configured attribute for api keys and mineru token (backward compatibility)
            try:
                changed = False
                # Platform API Keys
                pak = secrets.get("platform_api_keys")
                if isinstance(pak, dict):
                    for platform, val in list(pak.items()):
                        if isinstance(val, str):
                            pak[platform] = {"key": val, "configured": bool(val)}
                            changed = True
                        elif isinstance(val, dict):
                            # Ensure fields exist
                            if "key" not in val:
                                val["key"] = ""
                                changed = True
                            if "configured" not in val:
                                val["configured"] = bool(val.get("key"))
                                changed = True
                # MinerU Token
                if isinstance(secrets.get("translator_mineru_token"), str):
                    secrets["translator_mineru_token"] = {
                        "key": secrets["translator_mineru_token"],
                        "configured": bool(secrets["translator_mineru_token"])
                    }
                    changed = True
                elif isinstance(secrets.get("translator_mineru_token"), dict):
                    mt = secrets["translator_mineru_token"]
                    if "key" not in mt:
                        mt["key"] = ""
                        changed = True
                    if "configured" not in mt:
                        mt["configured"] = bool(mt.get("key"))
                        changed = True

                if changed:
                    # Save immediately to ensure file is written with new structure
                    self._secrets_cache = secrets
                    self.save_secrets(secrets)
            except Exception:
                # Normalization failure does not affect reading
                pass
            
            logger.debug(f"Successfully loaded sensitive configuration file: {self.secrets_file}")
            self._secrets_cache = secrets
            return secrets
            
        except Exception as e:
            logger.error(f"Failed to load sensitive configuration file: {e}")
            self._secrets_cache = {}
            return self._secrets_cache
    
    def get_api_keys(self) -> Dict[str, str]:
        """
        Get API key configuration
        
        Returns:
            API key dictionary
        """
        secrets = self.load_secrets()
        raw = secrets.get("platform_api_keys", {})
        # Compatibility: return platform->string
        result: Dict[str, str] = {}
        if isinstance(raw, dict):
            for platform, val in raw.items():
                if isinstance(val, dict):
                    result[platform] = val.get("key", "")
                else:
                    result[platform] = str(val) if val is not None else ""
        return result

    def get_api_keys_meta(self) -> Dict[str, Dict[str, Any]]:
        """
        Return platform API Key metadata { platform: { key: str, configured: bool } }
        """
        secrets = self.load_secrets()
        pak = secrets.get("platform_api_keys", {})
        meta: Dict[str, Dict[str, Any]] = {}
        if isinstance(pak, dict):
            for platform, val in pak.items():
                if isinstance(val, dict):
                    meta[platform] = {
                        "key": val.get("key", ""),
                        "configured": bool(val.get("configured", bool(val.get("key"))))
                    }
                else:
                    key = str(val) if val is not None else ""
                    meta[platform] = {"key": key, "configured": bool(key)}
        return meta
    
    def get_mineru_token(self) -> Optional[str]:
        """
        Get MinerU token
        
        Returns:
            MinerU token, returns None if not exists
        """
        secrets = self.load_secrets()
        val = secrets.get("translator_mineru_token")
        if isinstance(val, dict):
            return val.get("key")
        return val

    def get_mineru_token_meta(self) -> Dict[str, Any]:
        """Return { key: str, configured: bool }"""
        secrets = self.load_secrets()
        val = secrets.get("translator_mineru_token")
        if isinstance(val, dict):
            return {"key": val.get("key", ""), "configured": bool(val.get("configured", bool(val.get("key"))))}
        key = str(val) if val is not None else ""
        return {"key": key, "configured": bool(key)}

    def get_docling_auth(self) -> Dict[str, Any]:
        """
        Get Docling remote authentication configuration
        Return structure: {"auth_type": "none|bearer|header", "token": str, "header_name": str, "header_value": str}
        """
        secrets = self.load_secrets()
        return secrets.get("docling_auth", {})
    
    
    # Default password is now managed by unified user storage
    # This method is deprecated
    
    # Session secret key is now managed by local_config.json
    # This method is deprecated
    
    # Redis password is now managed by local_config.json
    # This method is deprecated
    
    def save_secrets(self, secrets: Dict[str, Any]) -> bool:
        """
        Save sensitive configuration to file
        
        Args:
            secrets: Sensitive configuration to save
            
        Returns:
            Whether save was successful
        """
        try:
            # Ensure directory exists
            self.secrets_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.secrets_file, 'w', encoding='utf-8') as f:
                json.dump(secrets, f, indent=2, ensure_ascii=False)
            
            # Update cache
            self._secrets_cache = secrets
            
            logger.info(f"Sensitive configuration saved to: {self.secrets_file}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save sensitive configuration file: {e}")
            return False
    
    def update_api_key(self, platform: str, api_key: str, configured: Optional[bool] = None) -> bool:
        """
        Update API key for specified platform
        
        Args:
            platform: Platform name
            api_key: API key
            
        Returns:
            Whether update was successful
        """
        secrets = self.load_secrets()
        if "platform_api_keys" not in secrets:
            secrets["platform_api_keys"] = {}
        key_meta = secrets["platform_api_keys"].get(platform)
        if not isinstance(key_meta, dict):
            key_meta = {"key": "", "configured": False}
        key_meta["key"] = api_key
        if configured is None:
            key_meta["configured"] = bool(api_key)
        else:
            key_meta["configured"] = bool(configured)
        secrets["platform_api_keys"][platform] = key_meta
        return self.save_secrets(secrets)
    
    def update_mineru_token(self, token: str, configured: Optional[bool] = None) -> bool:
        """
        Update MinerU token
        
        Args:
            token: MinerU token
            
        Returns:
            Whether update was successful
        """
        secrets = self.load_secrets()
        meta = secrets.get("translator_mineru_token")
        if not isinstance(meta, dict):
            meta = {"key": "", "configured": False}
        meta["key"] = token
        meta["configured"] = bool(configured) if configured is not None else bool(token)
        secrets["translator_mineru_token"] = meta
        return self.save_secrets(secrets)
    

    # ==== Web/HTTPS TLS Private Key Password ====
    def get_web_tls_password(self) -> Optional[str]:
        secrets = self.load_secrets()
        return secrets.get("web_tls", {}).get("key_password")

    def update_web_tls_password(self, password: Optional[str]) -> bool:
        secrets = self.load_secrets()
        if "web_tls" not in secrets:
            secrets["web_tls"] = {}
        if password:
            secrets["web_tls"]["key_password"] = password
        else:
            # Remove key when clearing to avoid residue
            secrets["web_tls"].pop("key_password", None)
        return self.save_secrets(secrets)
    
    def has_secrets_file(self) -> bool:
        """
        Check if sensitive configuration file exists
        
        Returns:
            Whether file exists
        """
        return self.secrets_file.exists()
    
    def create_template_file(self) -> bool:
        """
        Create configuration template file
        
        Returns:
            Whether creation was successful
        """
        template_file = self.secrets_file.parent / f"{self.secrets_file.stem}.template"
        
        template_content = {
            "_comment": "Local sensitive configuration file template - please copy as local_secrets.json and fill in real values",
            "_warning": "This file contains sensitive information, do not commit to git repository",
            
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
            
        }
        
        try:
            with open(template_file, 'w', encoding='utf-8') as f:
                json.dump(template_content, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration template file created: {template_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to create configuration template file: {e}")
            return False

    def update_docling_auth(self, auth: Dict[str, Any]) -> bool:
        """Update Docling remote authentication configuration"""
        secrets = self.load_secrets()
        secrets["docling_auth"] = {
            "auth_type": auth.get("auth_type", "none"),
            "token": auth.get("token", ""),
            "header_name": auth.get("header_name", ""),
            "header_value": auth.get("header_value", ""),
        }
        self.save_secrets(secrets)
        logger.info("Docling auth secrets updated")
        return True


# Global instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """Get global sensitive configuration manager instance"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
