# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import json
import logging
import os
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
        # 配置文件优先级：
        # 1. /etc/collabtrans/local_secrets.json (系统配置)
        # 2. 可执行程序目录下的 local_secrets.json (打包的配置)
        # 3. 当前目录下的 local_secrets.json (开发环境)
        
        system_secrets_file = "/etc/collabtrans/local_secrets.json"
        system_secrets_template = "/etc/collabtrans/local_secrets.json.template"
        system_dir_exists = os.path.exists("/etc/collabtrans")
        
        if system_dir_exists:
            if os.path.exists(system_secrets_file):
                self.secrets_file = Path(system_secrets_file)
                logger.info(f"Using system secrets config: {system_secrets_file}")
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
            # 尝试从可执行程序目录加载配置文件
            import sys
            if getattr(sys, 'frozen', False):
                # PyInstaller打包环境
                exe_dir = os.path.dirname(sys.executable)
                exe_secrets_file = os.path.join(exe_dir, "local_secrets.json")
                if os.path.exists(exe_secrets_file):
                    self.secrets_file = Path(exe_secrets_file)
                    logger.info(f"Using executable directory secrets config: {exe_secrets_file}")
                else:
                    # 将相对路径固定到仓库根目录，避免工作目录变化导致写入到错误位置
                    proj_root = Path(__file__).resolve().parents[2]
                    sf = Path(secrets_file)
                    self.secrets_file = sf if sf.is_absolute() else (proj_root / sf)
                    logger.info(f"Using local secrets config: {self.secrets_file}")
            else:
                # 开发环境
                proj_root = Path(__file__).resolve().parents[2]
                sf = Path(secrets_file)
                self.secrets_file = sf if sf.is_absolute() else (proj_root / sf)
                logger.info(f"Using local secrets config: {self.secrets_file}")
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
            # 在PyInstaller环境中，避免指向 /tmp/_MEI* 目录
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

            # 规范化结构：为 api keys 与 mineru token 增加 configured 属性（向后兼容）
            try:
                changed = False
                # 平台API Keys
                pak = secrets.get("platform_api_keys")
                if isinstance(pak, dict):
                    for platform, val in list(pak.items()):
                        if isinstance(val, str):
                            pak[platform] = {"key": val, "configured": bool(val)}
                            changed = True
                        elif isinstance(val, dict):
                            # 确保字段存在
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
                    # 立即保存一次，保证文件落盘为新结构
                    self._secrets_cache = secrets
                    self.save_secrets(secrets)
            except Exception:
                # 规范化失败不影响读取
                pass
            
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
        raw = secrets.get("platform_api_keys", {})
        # 兼容：返回平台->字符串
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
        返回平台API Key的元信息 { platform: { key: str, configured: bool } }
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
        获取MinerU令牌
        
        Returns:
            MinerU令牌，如果不存在则返回None
        """
        secrets = self.load_secrets()
        val = secrets.get("translator_mineru_token")
        if isinstance(val, dict):
            return val.get("key")
        return val

    def get_mineru_token_meta(self) -> Dict[str, Any]:
        """返回 { key: str, configured: bool }"""
        secrets = self.load_secrets()
        val = secrets.get("translator_mineru_token")
        if isinstance(val, dict):
            return {"key": val.get("key", ""), "configured": bool(val.get("configured", bool(val.get("key"))))}
        key = str(val) if val is not None else ""
        return {"key": key, "configured": bool(key)}

    def get_docling_auth(self) -> Dict[str, Any]:
        """
        获取 Docling 远程鉴权配置
        返回结构：{"auth_type": "none|bearer|header", "token": str, "header_name": str, "header_value": str}
        """
        secrets = self.load_secrets()
        return secrets.get("docling_auth", {})
    
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
    
    def update_api_key(self, platform: str, api_key: str, configured: Optional[bool] = None) -> bool:
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
        更新MinerU令牌
        
        Args:
            token: MinerU令牌
            
        Returns:
            是否更新成功
        """
        secrets = self.load_secrets()
        meta = secrets.get("translator_mineru_token")
        if not isinstance(meta, dict):
            meta = {"key": "", "configured": False}
        meta["key"] = token
        meta["configured"] = bool(configured) if configured is not None else bool(token)
        secrets["translator_mineru_token"] = meta
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

    # ==== Web/HTTPS TLS 私钥密码 ====
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
            # 清空时移除键以避免残留
            secrets["web_tls"].pop("key_password", None)
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

    def update_docling_auth(self, auth: Dict[str, Any]) -> bool:
        """更新 Docling 远程鉴权配置"""
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


# 全局实例
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager() -> SecretsManager:
    """获取全局敏感配置管理器实例"""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager
