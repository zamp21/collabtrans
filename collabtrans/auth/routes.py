# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from fastapi import APIRouter, Request, Response, HTTPException, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
from pathlib import Path
import time
import logging
import os
import json
import ssl
import httpx

from .config import AuthConfig
from .ldap_client import LDAPClient, InvalidCredentials
from .session_manager import AuthSessionManager
from .models import LoginRequest, LoginResponse, LogoutResponse, UserInfo, User, UserRole
from ..config import get_app_config, save_app_config
from ..config.secrets_manager import get_secrets_manager

# 创建认证专用的日志记录器
logger = logging.getLogger(__name__)

# 用户名脱敏：保留首尾字符，中间用×
def _mask_username(name: str) -> str:
    try:
        if not name:
            return ""
        if len(name) <= 2:
            return name[0] + ("×" if len(name) == 2 else "")
        return name[0] + ("×" * (len(name) - 2)) + name[-1]
    except Exception:
        return "***"

# 创建路由器
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# 创建不带前缀的兼容性路由器
auth_compat_router = APIRouter(tags=["Authentication"])

# 模板目录：使用资源路径解析，兼容开发与PyInstaller
from ..utils.resource_utils import resource_path
templates = Jinja2Templates(directory=str(resource_path("template")))

# 全局变量（在实际应用中应该通过依赖注入）
_auth_config: Optional[AuthConfig] = None
_session_manager: Optional[AuthSessionManager] = None
_ldap_client: Optional[LDAPClient] = None


def init_auth(config: AuthConfig):
    """初始化认证模块"""
    global _auth_config, _session_manager, _ldap_client
    _auth_config = config
    _session_manager = AuthSessionManager(config)
    if config.ldap_enabled:
        _ldap_client = LDAPClient(config)


def get_auth_config() -> AuthConfig:
    """获取认证配置"""
    if _auth_config is None:
        raise HTTPException(status_code=500, detail="Authentication not initialized")
    return _auth_config


def get_session_manager() -> AuthSessionManager:
    """获取会话管理器"""
    if _session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    return _session_manager


def get_ldap_client() -> Optional[LDAPClient]:
    """获取LDAP客户端"""
    return _ldap_client


def _refresh_ldap_client_if_endpoint_changed(old_cfg: "AuthConfig", new_cfg: "AuthConfig") -> None:
    """当LDAP端点相关配置发生变化时，安全地重建LDAP客户端。"""
    try:
        endpoint_fields = [
            'ldap_enabled', 'ldap_protocol', 'ldap_host', 'ldap_port',
            'ldap_tls_cacertfile', 'ldap_tls_verify'
        ]
        changed = any(getattr(old_cfg, f, None) != getattr(new_cfg, f, None) for f in endpoint_fields)
        if changed:
            global _ldap_client
            if _ldap_client is not None:
                try:
                    _ldap_client.close()
                except Exception:
                    pass
            # 仅当启用了LDAP时才重建
            if new_cfg.ldap_enabled:
                _ldap_client = LDAPClient(new_cfg)
                logger.info("[LDAP] Endpoint changed, LDAP client rebuilt")
            else:
                _ldap_client = None
                logger.info("[LDAP] LDAP disabled, client released")
    except Exception as e:
        logger.warning(f"[LDAP] Exception while checking/rebuilding client: {e}")


async def get_current_user(request: Request) -> Optional[User]:
    """获取当前用户"""
    session_manager = get_session_manager()
    return await session_manager.get_user(request)


@auth_router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    next_url: Optional[str] = None,
    error: Optional[str] = None
):
    """Login page"""
    from .config import AuthConfig
    config = AuthConfig.get_config()
    return templates.TemplateResponse("login.html", {
        "request": request,
        "next_url": next_url,
        "error": error,
        "ldap_enabled": config.ldap_enabled,
        "login_banner": config.login_banner
    })


@auth_router.post("/login", response_class=JSONResponse)
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None)
):
    """Handle login request"""
    config = get_auth_config()
    session_manager = get_session_manager()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"Login request received - user: {_mask_username(username)}, IP: {client_ip}")
    logger.info(f"Auth config - LDAP enabled: {config.ldap_enabled}")
    
    # Check login attempt count
    attempts = session_manager.get_login_attempts(client_ip)
    logger.info(f"Current login attempts: {attempts}/{config.max_login_attempts}")
    
    if attempts >= config.max_login_attempts:
        logger.warning(f"IP {client_ip} too many login attempts, locked")
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please try again in {config.login_attempt_window // 60} minutes."
        )
    
    try:
        user: User
        
        # Hybrid authentication policy:
        # 1) If username is admin -> always use local auth with ADMIN role
        # 2) If LDAP enabled and username is not admin -> use LDAP auth
        # 3) If LDAP disabled -> only local admin auth is allowed
        
        if username == config.default_username:
            # admin user always uses local authentication
            logger.info(f"Using local admin authentication for: {_mask_username(username)}")
            if password == config.default_password:
                user = User(
                    username=username,
                    display_name="Administrator",
                    email=None,
                    is_authenticated=True,
                    role=UserRole.ADMIN  # admin is always administrator
                )
                logger.info(f"Admin user authenticated: {_mask_username(username)}")
            else:
                logger.warning(f"Admin user authentication failed: {_mask_username(username)}")
                raise InvalidCredentials("Invalid username or password")
        elif config.ldap_enabled:
            # Non-admin users use LDAP authentication (ldap3 client)
            logger.info(f"Using LDAP authentication for user: {_mask_username(username)}")
            try:
                from .ldap_client import LDAPClient
                ldap3_client = LDAPClient(config)
                user = ldap3_client.authenticate(username, password)
            finally:
                try:
                    ldap3_client.close()
                except Exception:
                    pass
            logger.info(f"LDAP authentication successful, user: {_mask_username(username)}")
        else:
            # LDAP disabled and username is not admin
            logger.warning(f"LDAP disabled and non-admin user attempted login: {_mask_username(username)}")
            raise InvalidCredentials("LDAP authentication is disabled and only admin user is allowed")
        
        # Log permission/role info
        try:
            logger.info(
                "User permissions: role=%s, is_admin=%s, is_super_admin=%s, can_access_admin_settings=%s, can_access_glossary_management=%s",
                getattr(user, 'role', None).value if getattr(user, 'role', None) is not None else 'unknown',
                str(user.is_admin() if hasattr(user, 'is_admin') else False),
                str(user.is_super_admin() if hasattr(user, 'is_super_admin') else False),
                str(user.can_access_admin_settings() if hasattr(user, 'can_access_admin_settings') else False),
                str(user.can_access_glossary_management() if hasattr(user, 'can_access_glossary_management') else False)
            )
        except Exception:
            pass

        # Create session
        logger.info(f"Creating session for user {_mask_username(username)}")
        await session_manager.create_session(request, response, user)
        
        # Ensure user has a personal profile
        from .user_profile import get_user_profile_manager
        profile_manager = get_user_profile_manager()
        
        # Create default profile if not exists
        if not os.path.exists(f"user_profiles/{username}_profile.json"):
            logger.info(f"Creating default profile for user {_mask_username(username)}")
            profile_manager.create_default_profile(username)
        else:
            logger.info(f"User {_mask_username(username)} already has a profile, skipping creation")
        
        # Reset attempts for this IP
        session_manager.reset_login_attempts(client_ip)
        logger.info(f"Reset login attempts for IP {client_ip}")
        
        # Determine redirect URL
        redirect_url = next_url if next_url and next_url.startswith('/') else "/"
        logger.info(f"Login successful, redirect URL: {redirect_url}")
        
        return LoginResponse(
            success=True,
            message="Login successful",
            next_url=redirect_url
        )
        
    except InvalidCredentials as e:
        logger.warning(f"Authentication failed - invalid credentials: {_mask_username(username)}, error: {e}")
        # 增加登录尝试次数
        session_manager.increment_login_attempts(client_ip)
        logger.info(f"Incremented login attempts for IP {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    except Exception as e:
        logger.error(f"Exception during authentication: {_mask_username(username)}, error: {e}")
        logger.error(f"Exception type: {type(e)}")
        # 增加登录尝试次数
        session_manager.increment_login_attempts(client_ip)
        logger.info(f"增加IP {client_ip} 的登录尝试次数")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@auth_router.post("/logout", response_class=JSONResponse)
async def logout(request: Request, response: Response):
    """处理登出请求"""
    session_manager = get_session_manager()
    
    await session_manager.destroy_session(request, response)
    
    return LogoutResponse(
        success=True,
        message="Logout successful"
    )


@auth_router.get("/logout", response_class=RedirectResponse)
async def logout_get(request: Request, response: Response):
    """GET方式登出，重定向到登录页"""
    session_manager = get_session_manager()
    
    await session_manager.destroy_session(request, response)
    
    return RedirectResponse(url="/login", status_code=302)


@auth_router.get("/user", response_model=UserInfo)
async def get_user_info(request: Request):
    """获取当前用户信息"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return UserInfo(
        username=user.username,
        display_name=user.display_name,
        email=user.email
    )


@auth_router.get("/config")
async def get_auth_config_api(request: Request):
    """获取认证配置"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    config = get_auth_config()
    
    # 返回配置，但不包含敏感信息如密码
    return {
        "ldap_enabled": config.ldap_enabled,
        "ldap_protocol": config.ldap_protocol,
        "ldap_host": config.ldap_host,
        "ldap_port": config.ldap_port,
        "ldap_bind_dn_template": config.ldap_bind_dn_template,
        "ldap_base_dn": config.ldap_base_dn,
        "ldap_user_filter": config.ldap_user_filter,
        "ldap_tls_cacertfile": config.ldap_tls_cacertfile,
        "ldap_tls_verify": config.ldap_tls_verify,
        "default_username": config.default_username,
        "default_password": "***",  # 不返回真实密码
        "session_max_age": config.session_max_age,
        "max_login_attempts": config.max_login_attempts,
        "login_attempt_window": config.login_attempt_window,
    }


@auth_router.post("/config")
async def update_auth_config_api(request: Request, config_data: dict):
    """更新认证配置"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    logger.info(f"收到配置更新请求: {config_data}")
    
    try:
        # 获取当前配置
        config = get_auth_config()
        
        # 更新配置
        config.update_from_dict(config_data)
        
        # Save to grouped local_config.json
        config_file = "local_config.json"
        if config.save_to_file(config_file):
            logger.info("配置保存成功")
            return {"message": "Configuration updated successfully. Please restart the application to take effect."}
        else:
            logger.error("配置保存失败")
            raise HTTPException(status_code=500, detail="Failed to save configuration")
            
    except Exception as e:
        logger.error(f"更新配置时发生错误: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@auth_router.post("/test-ldap")
async def test_ldap_connection(request: Request, payload: dict):
    """测试LDAP/LDAPS连接（仅管理员可用）
    入参：{"username": "testuser", "password": "***"}
    使用当前认证配置执行一次简单绑定与检索。
    """
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not user.is_admin():
        return JSONResponse(status_code=403, content={"ok": False, "message": "forbidden"})

    username = (payload or {}).get("username", "").strip()
    password = (payload or {}).get("password", "")
    if not username or not password:
        return JSONResponse(status_code=400, content={"ok": False, "message": "username/password required"})

    base_config = get_auth_config()
    # Remove LDAP enabled check - allow testing regardless of current enabled state

    # 允许用当前UI中的值临时覆盖（不持久化）
    try:
        from dataclasses import asdict
        override = payload or {}
        cfg_dict = asdict(base_config)
        for key in [
            'ldap_protocol', 'ldap_host', 'ldap_port', 'ldap_bind_dn_template', 'ldap_base_dn',
            'ldap_user_filter', 'ldap_admin_group_enabled', 'ldap_glossary_group_enabled',
            'ldap_admin_group', 'ldap_glossary_group', 'ldap_group_base_dn',
            'ldap_tls_cacertfile', 'ldap_tls_verify'
        ]:
            if key in override and override[key] not in (None, ""):
                # 类型处理
                if key == 'ldap_port':
                    try:
                        cfg_dict[key] = int(override[key])
                    except Exception:
                        pass
                elif key in ['ldap_tls_verify', 'ldap_admin_group_enabled', 'ldap_glossary_group_enabled']:
                    val = override[key]
                    if isinstance(val, str):
                        cfg_dict[key] = val.lower() in ("true", "1", "yes", "on")
                    else:
                        cfg_dict[key] = bool(val)
                else:
                    cfg_dict[key] = override[key]

        
        # 构造临时配置，强制启用LDAP用于测试
        cfg_dict['ldap_enabled'] = True
        temp_config = AuthConfig(**cfg_dict)

        client = LDAPClient(temp_config)
        user = client.authenticate(username, password)
        
        # 构建结构化调试信息（前端用i18n渲染）
        groups_enabled = bool(temp_config.ldap_admin_group_enabled or temp_config.ldap_glossary_group_enabled)
        groups_codes = []  # ['admin', 'glossary']
        
        # 检查组查询状态
        if groups_enabled:
            
            # 获取用户的组成员信息（统一使用 ldap3，避免与 python-ldap API 混用）
            try:
                from ldap3 import SUBTREE as _LDAP3_SUBTREE
                conn = client._get_connection()
                user_filter = temp_config.ldap_user_filter.format(username=username)
                conn.search(
                    search_base=temp_config.ldap_base_dn,
                    search_filter=user_filter,
                    search_scope=_LDAP3_SUBTREE,
                    attributes=['sAMAccountName', 'displayName', 'mail', 'cn', 'memberOf']
                )

                if conn.entries:
                    user_entry = conn.entries[0]
                    is_admin_member = False
                    is_glossary_member = False

                    # 检查管理员组
                    if temp_config.ldap_admin_group_enabled:
                        is_admin_member = client._check_admin_group_membership(conn, user_entry)

                    # 检查术语表组
                    if temp_config.ldap_glossary_group_enabled:
                        is_glossary_member = client._check_user_group_membership(conn, user_entry)

                    if is_admin_member:
                        groups_codes.append('admin')
                    if is_glossary_member:
                        groups_codes.append('glossary')

            except Exception as e:
                logger.warning(f"获取组成员信息时发生错误: {e}")
        
        return JSONResponse(content={
            "ok": True,
            "groups_enabled": groups_enabled,
            "groups": groups_codes,
            "user_role": user.role.value,
            "is_admin": user.is_admin(),
            "test_validated": True  # Mark that LDAP test has passed
        })
    except InvalidCredentials:
        return JSONResponse(status_code=401, content={"ok": False, "message": "invalid credentials"})
    except Exception as e:
        return JSONResponse(status_code=502, content={"ok": False, "message": f"{str(e)}"})


@auth_router.get("/user/permissions")
async def get_user_permissions(
    user: User = Depends(get_current_user)
):
    """获取用户权限信息"""
    return {
        "is_admin": user.is_admin(),
        "is_super_admin": user.is_super_admin(),
        "can_access_admin_settings": user.can_access_admin_settings(),
        "can_access_glossary_management": user.can_access_glossary_management(),
        "allowed_settings": user.get_allowed_settings(),
        "role": user.role.value
    }


@auth_router.get("/app-config")
async def get_app_config_api(
    user: User = Depends(get_current_user)
):
    """获取应用配置（需要登录）"""
    from .user_profile import get_user_profile_manager
    from ..config.global_config import get_global_config
    
    # 获取用户个人配置
    profile_manager = get_user_profile_manager()
    user_profile = profile_manager.get_user_profile(user.username)
    user_config = user_profile.get_config_dict()
    
    # 获取全局配置
    global_config = get_global_config()
    global_config_dict = global_config.get_config_dict(include_api_keys=False, flatten=True)
    
    # 获取LDAP配置（使用本模块中的全局配置访问器）
    auth_config = get_auth_config()
    auth_config_dict = auth_config.__dict__
    
    # 合并配置：用户配置 + 全局配置 + LDAP配置
    config_dict = {**global_config_dict, **user_config, **auth_config_dict}
    
    # 输出时仅保留新键名（不处理已废弃旧键）
    
    # 根据用户权限过滤敏感配置
    if not user.is_admin():
        # 非管理员用户，只返回基础配置
        filtered_config = {}
        # 允许的基础设置
        allowed_keys = [
            'ui_language', 'translator_last_workflow', 'translator_auto_workflow_enabled',
            'translator_txt_insert_mode', 'translator_txt_separator',
            'translator_xlsx_insert_mode', 'translator_xlsx_separator', 'translator_xlsx_translate_regions',
            'translator_docx_insert_mode', 'translator_docx_separator',
            'translator_srt_insert_mode', 'translator_srt_separator',
            'translator_epub_insert_mode', 'translator_epub_separator',
            'translator_html_insert_mode', 'translator_html_separator',
            'translator_json_paths', 'translator_target_language', 'translator_custom_language',
            'translator_custom_prompt', 'translator_thinking_mode', 'theme',
            'translator_platform_type', 'translator_temperature', 'translator_max_tokens', 'translator_top_p',
            'translator_frequency_penalty', 'translator_presence_penalty',
            'chunk_size', 'concurrent',
            'glossary_generate_enable', 'glossary_agent_config_choice', 'glossary_agent_thinking_mode',
            'glossary_agent_platform_type', 'glossary_agent_temperature', 'glossary_agent_max_tokens', 'glossary_agent_top_p',
            'glossary_agent_frequency_penalty', 'glossary_agent_presence_penalty', 'glossary_agent_to_lang',
            'glossary_agent_chunk_size', 'glossary_agent_concurrent',
            # 全局配置中的非敏感设置
            'ai_platforms', 'translator_settings', 'default_language',
            # 用户维度模型覆盖
            'translator_platform_models', 'glossary_agent_platform_models',
            # LDAP配置（非敏感部分）
            'ldap_enabled', 'ldap_protocol', 'ldap_host', 'ldap_port'
        ]
        for key in allowed_keys:
            if key in config_dict:
                filtered_config[key] = config_dict[key]
        return filtered_config
    else:
        # 管理员用户，返回所有配置，但隐藏敏感信息
        # 脱敏API密钥（从ai_platforms中）
        if 'ai_platforms' in config_dict:
            for platform_key, platform_data in config_dict['ai_platforms'].items():
                if isinstance(platform_data, dict) and 'api_key' in platform_data:
                    api_key = platform_data['api_key']
                    if api_key:
                        platform_data['api_key'] = api_key[:8] + "***" if len(api_key) > 8 else "***"
                    else:
                        platform_data['api_key'] = ""
        
        
        # 脱敏Mineru Token（从敏感配置加载）
        from ..config.secrets_manager import get_secrets_manager
        secrets_manager = get_secrets_manager()
        mineru_token = secrets_manager.get_mineru_token()
        if mineru_token:
            config_dict['translator_mineru_token'] = mineru_token[:8] + "***" if len(mineru_token) > 8 else "***"
        else:
            config_dict['translator_mineru_token'] = ""
        
        return config_dict


@auth_router.get("/app-config/raw-secrets")
async def get_raw_secrets_api(
    user: User = Depends(get_current_user)
):
    """获取完整的敏感配置（仅管理员可用）"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")
    
    from ..config.secrets_manager import get_secrets_manager
    secrets_manager = get_secrets_manager()
    
    # 获取完整的API密钥及元信息（不脱敏）
    api_keys_meta = secrets_manager.get_api_keys_meta()
    mineru_meta = secrets_manager.get_mineru_token_meta()
    # 保持向后兼容：同时提供旧字段
    api_keys_plain = {k: v.get("key", "") for k, v in api_keys_meta.items()}
    return {
        "platform_api_keys": api_keys_plain,
        "platform_api_keys_meta": api_keys_meta,
        "translator_mineru_token": mineru_meta.get("key", ""),
        "translator_mineru_token_meta": mineru_meta
    }

@auth_router.post("/web/upload-cert")
async def upload_web_cert(
    cert: UploadFile | None = File(None),
    key: UploadFile | None = File(None),
    user: User = Depends(get_current_user)
):
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        from pathlib import Path
        from ..config.global_config import get_global_config, save_global_config
        base_dir = Path(__file__).resolve().parents[2]
        certs_dir = base_dir / "certs"
        certs_dir.mkdir(parents=True, exist_ok=True)

        saved_cert_path = None
        saved_key_path = None

        if cert is not None and cert.filename:
            target = certs_dir / cert.filename
            content = await cert.read()
            target.write_bytes(content)
            saved_cert_path = str(target)

        if key is not None and key.filename:
            target = certs_dir / key.filename
            content = await key.read()
            target.write_bytes(content)
            saved_key_path = str(target)

        if not saved_cert_path and not saved_key_path:
            raise HTTPException(status_code=400, detail="No files uploaded")

        gc = get_global_config()
        if saved_cert_path:
            gc.https_cert_file = saved_cert_path
        if saved_key_path:
            gc.https_key_file = saved_key_path
        save_global_config()

        return {"success": True, "cert": saved_cert_path, "key": saved_key_path}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传证书失败: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@auth_router.post("/web/test-https")
async def test_https_available(
    request: Request,
    payload: dict,
    user: User = Depends(get_current_user)
):
    """测试当前证书与HTTPS可用性（仅管理员）
    逻辑：
    1) 读取传入的证书/私钥路径（若未传入则使用全局配置）
    2) 校验证书/私钥文件存在与可读
    3) 尝试加载到 SSLContext（等同于Uvicorn使用）
    4) 对自身发起一次 HTTPS 请求（verify=False），返回状态码
    """
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        from ..config.global_config import get_global_config
        from ..config.secrets_manager import get_secrets_manager

        gc = get_global_config()
        sm = get_secrets_manager()
        cert_file = (payload or {}).get('https_cert_file') or gc.https_cert_file
        key_file = (payload or {}).get('https_key_file') or gc.https_key_file
        key_password = (payload or {}).get('https_key_password') or sm.get_web_tls_password()

        details = {
            "cert_exists": bool(cert_file and os.path.exists(cert_file)),
            "key_exists": bool(key_file and os.path.exists(key_file)),
        }

        # 检查 openssl 是否可用（用于自动生成或用户排障）
        try:
            import shutil
            details["openssl_available"] = bool(shutil.which("openssl"))
        except Exception:
            details["openssl_available"] = False

        if not details["cert_exists"] or not details["key_exists"]:
            return JSONResponse(status_code=400, content={
                "ok": False,
                "message": "Certificate or key file not found" + ("; please install openssl to auto-generate dev cert" if not details.get("openssl_available") else ""),
                **details
            })

        # 3) 加载到 SSLContext
        try:
            ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
            # 允许无密码
            ctx.load_cert_chain(certfile=cert_file, keyfile=key_file, password=key_password)
            details["load_sslcontext_ok"] = True
        except Exception as e:
            details["load_sslcontext_ok"] = False
            details["load_error"] = str(e)
            return JSONResponse(status_code=400, content={
                "ok": False,
                "message": "Failed to load cert/key into SSL context",
                **details
            })

        # 4) 自测：对自身发起一次HTTPS请求（关闭验证，以兼容自签名）
        port = getattr(request.app.state, 'port_to_use', 8010)
        try:
            async with httpx.AsyncClient(verify=False, timeout=2.5) as client:
                r = await client.get(f"https://127.0.0.1:{port}/login")
                details["probe_status"] = r.status_code
        except Exception as e:
            details["probe_status"] = None
            details["probe_error"] = str(e)

        return {"ok": True, "message": "HTTPS test completed", **details}
    except Exception as e:
        logger.error(f"测试HTTPS失败: {e}")
        return JSONResponse(status_code=500, content={"ok": False, "message": str(e)})


# === 术语表管理API ===

@auth_router.get("/glossaries")
async def get_glossaries_list(
    user: User = Depends(get_current_user)
):
    """获取术语表列表"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    
    # 获取全局术语表
    global_glossaries = manager.get_global_glossaries()
    
    # 获取用户个人术语表
    personal_glossary = manager.get_user_personal_glossary(user.username)
    
    # 获取用户选择
    user_selection = manager.get_user_selection(user.username)
    
    # 获取版本信息
    versions = manager.get_all_versions()
    
    return {
        "global_glossaries": [
            {
                "id": g.id,
                "name": g.name,
                "owner": g.owner,
                "is_global": g.is_global,
                "created_at": g.created_at.isoformat(),
                "updated_at": g.updated_at.isoformat(),
                "item_count": g.item_count,
                "description": g.description
            }
            for g in global_glossaries
        ],
        "personal_glossary": {
            "id": personal_glossary.id,
            "name": personal_glossary.name,
            "owner": personal_glossary.owner,
            "is_global": personal_glossary.is_global,
            "created_at": personal_glossary.created_at.isoformat(),
            "updated_at": personal_glossary.updated_at.isoformat(),
            "item_count": personal_glossary.item_count,
            "description": personal_glossary.description
        } if personal_glossary else None,
        "user_selection": {
            "username": user_selection.username,
            "selected_global_glossaries": user_selection.selected_global_glossaries,
            "personal_glossary": user_selection.personal_glossary
        },
        "versions": versions
    }


@auth_router.get("/glossaries/check-updates")
async def check_glossaries_updates(
    request: Request,
    user: User = Depends(get_current_user)
):
    """检查术语表更新"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    current_versions = manager.get_all_versions()
    
    # 获取用户上次检查的版本
    last_check = request.cookies.get('glossaries_last_check', '{}')
    try:
        last_versions = json.loads(last_check)
    except:
        last_versions = {}
    
    # 检查是否有更新
    has_updates = False
    for glossary_id, current_version in current_versions.items():
        last_version = last_versions.get(glossary_id, 0)
        if current_version > last_version:
            has_updates = True
            break
    
    return {
        "has_updates": has_updates,
        "current_versions": current_versions
    }


@auth_router.post("/glossaries/upload")
async def upload_glossary(
    request: Request,
    user: User = Depends(get_current_user)
):
    """上传术语表"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    
    try:
        form = await request.form()
        file = form.get("file")
        name = form.get("name", "").strip()
        description = form.get("description", "").strip()
        is_global = form.get("is_global", "false").lower() == "true"
        
        if not file or not name:
            raise HTTPException(status_code=400, detail="文件名和术语表名称不能为空")
        
        # 检查权限
        if is_global and not user.is_admin():
            raise HTTPException(status_code=403, detail="只有管理员可以上传全局术语表")
        
        # 读取文件内容
        content = await file.read()
        content_str = content.decode('utf-8-sig')
        
        # 解析CSV
        import csv
        from io import StringIO
        
        glossary_dict = {}
        reader = csv.DictReader(StringIO(content_str))
        for row in reader:
            src = row.get('src', '').strip()
            dst = row.get('dst', '').strip()
            if src and dst:
                glossary_dict[src] = dst
        
        if not glossary_dict:
            raise HTTPException(status_code=400, detail="术语表不能为空")
        
        # 验证术语表
        is_valid, message = manager.validate_glossary_dict(glossary_dict)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # 保存术语表
        if is_global:
            glossary = manager.create_global_glossary(name, glossary_dict, user.username, description)
            logger.info(f"管理员 {user.username} 创建了全局术语表: {name}")
        else:
            # 个人术语表
            success = manager.save_user_personal_glossary(user.username, glossary_dict)
            if not success:
                raise HTTPException(status_code=500, detail="保存个人术语表失败")
            logger.info(f"用户 {user.username} 更新了个人术语表")
        
        return {
            "success": True,
            "message": "术语表上传成功",
            "item_count": len(glossary_dict)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传术语表失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@auth_router.get("/glossaries/{glossary_id}/download")
async def download_glossary(
    glossary_id: str,
    user: User = Depends(get_current_user)
):
    """下载术语表"""
    from ..glossary.manager import get_glossary_manager
    from fastapi.responses import FileResponse
    
    manager = get_glossary_manager()
    
    # 获取术语表内容
    glossary_dict = manager.get_glossary_content(glossary_id)
    if not glossary_dict:
        raise HTTPException(status_code=404, detail="术语表不存在")
    
    # 生成临时CSV文件
    import tempfile
    import csv
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig')
    writer = csv.writer(temp_file)
    writer.writerow(['src', 'dst'])
    for src, dst in glossary_dict.items():
        writer.writerow([src, dst])
    temp_file.close()
    
    # 确定文件名
    if glossary_id.startswith('global_'):
        global_glossaries = manager.get_global_glossaries()
        for g in global_glossaries:
            if g.id == glossary_id:
                filename = f"{g.name}.csv"
                break
        else:
            filename = "glossary.csv"
    else:
        filename = "personal_glossary.csv"
    
    return FileResponse(
        path=temp_file.name,
        filename=filename,
        media_type='text/csv'
    )


@auth_router.put("/glossaries/selection")
async def update_glossary_selection(
    request: Request,
    user: User = Depends(get_current_user)
):
    """更新用户术语表选择"""
    from ..glossary.manager import get_glossary_manager
    from ..glossary.models import UserGlossarySelection
    
    manager = get_glossary_manager()
    
    try:
        data = await request.json()
        logger.info(f"[LDAP-API] 收到更新请求: {data}")
        selected_global_glossaries = data.get("selected_global_glossaries", [])
        personal_glossary = data.get("personal_glossary")
        
        # 验证选择的全局术语表是否存在
        global_glossaries = manager.get_global_glossaries()
        valid_global_ids = [g.id for g in global_glossaries]
        
        for glossary_id in selected_global_glossaries:
            if glossary_id not in valid_global_ids:
                raise HTTPException(status_code=400, detail=f"术语表 {glossary_id} 不存在")
        
        # 验证个人术语表
        if personal_glossary and personal_glossary != f"personal_{user.username}":
            raise HTTPException(status_code=400, detail="无效的个人术语表ID")
        
        # 保存选择
        selection = UserGlossarySelection(
            username=user.username,
            selected_global_glossaries=selected_global_glossaries,
            personal_glossary=personal_glossary
        )
        manager.save_user_selection(selection)
        
        logger.info(f"用户 {user.username} 更新了术语表选择")
        
        return {"success": True, "message": "术语表选择已更新"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新术语表选择失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@auth_router.delete("/glossaries/{glossary_id}")
async def delete_glossary(
    glossary_id: str,
    user: User = Depends(get_current_user)
):
    """删除术语表"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    
    # 检查权限
    if glossary_id.startswith('global_'):
        if not user.is_admin():
            raise HTTPException(status_code=403, detail="只有管理员可以删除全局术语表")
        
        success = manager.delete_global_glossary(glossary_id)
        if success:
            logger.info(f"管理员 {user.username} 删除了全局术语表: {glossary_id}")
        else:
            raise HTTPException(status_code=404, detail="术语表不存在")
    else:
        # 个人术语表 - 用户只能删除自己的
        if not glossary_id.startswith(f"personal_{user.username}"):
            raise HTTPException(status_code=403, detail="只能删除自己的个人术语表")
        
        # 清空个人术语表
        success = manager.save_user_personal_glossary(user.username, {})
        if success:
            logger.info(f"用户 {user.username} 清空了个人术语表")
        else:
            raise HTTPException(status_code=500, detail="删除个人术语表失败")
    
    return {"success": True, "message": "术语表已删除"}


# === 提示词管理API ===

@auth_router.get("/prompts")
async def get_prompts_list(
    user: User = Depends(get_current_user)
):
    """获取提示词列表"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # 获取全局提示词
    global_prompts = manager.get_global_prompts()
    
    # 获取用户个人提示词
    personal_prompt = manager.get_user_personal_prompt(user.username)
    
    # 获取用户选择
    user_selection = manager.get_user_selection(user.username)
    
    # 获取版本信息
    versions = manager.get_all_versions()
    
    return {
        "global_prompts": [
            {
                "id": p.id,
                "name": p.name,
                "owner": p.owner,
                "is_global": p.is_global,
                "created_at": p.created_at.isoformat(),
                "updated_at": p.updated_at.isoformat(),
                "item_count": p.item_count,
                "description": p.description
            }
            for p in global_prompts
        ],
        "personal_prompt": {
            "id": personal_prompt.id,
            "name": personal_prompt.name,
            "owner": personal_prompt.owner,
            "is_global": personal_prompt.is_global,
            "created_at": personal_prompt.created_at.isoformat(),
            "updated_at": personal_prompt.updated_at.isoformat(),
            "item_count": personal_prompt.item_count,
            "description": personal_prompt.description
        } if personal_prompt else None,
        "user_selection": {
            "username": user_selection.username,
            "selected_global_prompts": user_selection.selected_global_prompts,
            "personal_prompt": user_selection.personal_prompt
        },
        "versions": versions
    }


@auth_router.get("/prompts/check-updates")
async def check_prompts_updates(
    request: Request,
    user: User = Depends(get_current_user)
):
    """检查提示词更新"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        # 获取当前版本信息
        current_versions = manager.get_all_versions()
        
        # 这里可以添加更复杂的更新检查逻辑
        # 比如检查文件修改时间等
        
        return {
            "has_updates": False,  # 简化实现，总是返回无更新
            "current_versions": current_versions
        }
        
    except Exception as e:
        logger.error(f"检查提示词更新失败: {e}")
        return {
            "has_updates": False,
            "current_versions": {}
        }


@auth_router.post("/prompts/upload")
async def upload_prompt(
    request: Request,
    user: User = Depends(get_current_user)
):
    """上传提示词"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        form = await request.form()
        file = form.get("file")
        name = form.get("name", "").strip()
        description = form.get("description", "").strip()
        is_global = form.get("is_global", "false").lower() == "true"
        
        if not file or not name:
            raise HTTPException(status_code=400, detail="文件名和提示词名称不能为空")
        
        # 检查权限
        if is_global and not user.is_admin():
            raise HTTPException(status_code=403, detail="只有管理员可以上传全局提示词")
        
        # 读取文件内容
        content = await file.read()
        content_str = content.decode('utf-8-sig')
        
        # 解析JSON
        import json
        try:
            prompts_dict = json.loads(content_str)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON格式错误: {str(e)}")
        
        if not prompts_dict:
            raise HTTPException(status_code=400, detail="提示词不能为空")
        
        # 验证提示词
        is_valid, message = manager.validate_prompt_dict(prompts_dict)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # 保存提示词
        if is_global:
            prompt = manager.create_global_prompt(name, prompts_dict, user.username, description)
            logger.info(f"管理员 {user.username} 创建了全局提示词: {name}")
        else:
            # 个人提示词
            success = manager.save_user_personal_prompt(user.username, prompts_dict)
            if not success:
                raise HTTPException(status_code=500, detail="保存个人提示词失败")
            logger.info(f"用户 {user.username} 更新了个人提示词")
        
        return {
            "success": True,
            "message": "提示词上传成功",
            "item_count": len(prompts_dict)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传提示词失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@auth_router.get("/prompts/{prompt_id}/download")
async def download_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user)
):
    """下载提示词"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # 获取提示词文件
    if prompt_id.startswith('global_'):
        global_prompts = manager.get_global_prompts()
        prompt_file = None
        for p in global_prompts:
            if p.id == prompt_id:
                prompt_file = p
                break
        
        if not prompt_file:
            raise HTTPException(status_code=404, detail="提示词不存在")
        
        # 读取提示词内容
        prompts_dict = manager.storage.load_prompts_from_json(
            manager.storage.global_dir / manager.storage.global_prompts[prompt_id]['file_path']
        )
        
        filename = f"{prompt_file.name}.json"
        
    elif prompt_id.startswith(f"personal_{user.username}"):
        # 个人提示词
        personal_prompt = manager.get_user_personal_prompt(user.username)
        if not personal_prompt:
            raise HTTPException(status_code=404, detail="个人提示词不存在")
        
        prompts_dict = manager.storage.load_prompts_from_json(
            manager.storage.users_dir / f"{user.username}_prompts.json"
        )
        filename = f"{user.username}_personal_prompts.json"
        
    else:
        raise HTTPException(status_code=404, detail="提示词不存在")
    
    # 生成JSON内容
    import json
    content = json.dumps(prompts_dict, ensure_ascii=False, indent=2)
    
    return Response(
        content=content,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
        media_type='application/json'
    )


@auth_router.put("/prompts/selection")
async def update_prompt_selection(
    request: Request,
    user: User = Depends(get_current_user)
):
    """更新用户提示词选择"""
    from ..prompts.manager import get_prompt_manager
    from ..prompts.models import UserPromptSelection
    
    manager = get_prompt_manager()
    
    try:
        data = await request.json()
        logger.info(f"[PROMPT-API] 收到更新请求: {data}")
        selected_global_prompts = data.get("selected_global_prompts", [])
        personal_prompt = data.get("personal_prompt")
        
        # 验证选择的全局提示词是否存在
        global_prompts = manager.get_global_prompts()
        valid_global_ids = [p.id for p in global_prompts]
        
        for prompt_id in selected_global_prompts:
            if prompt_id not in valid_global_ids:
                raise HTTPException(status_code=400, detail=f"提示词 {prompt_id} 不存在")
        
        # 验证个人提示词
        if personal_prompt and personal_prompt != f"personal_{user.username}":
            raise HTTPException(status_code=400, detail="无效的个人提示词ID")
        
        # 保存选择
        selection = UserPromptSelection(
            username=user.username,
            selected_global_prompts=selected_global_prompts,
            personal_prompt=personal_prompt
        )
        manager.save_user_selection(selection)
        
        logger.info(f"用户 {user.username} 更新了提示词选择")
        
        return {"success": True, "message": "提示词选择已更新"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新提示词选择失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新失败: {str(e)}")


@auth_router.delete("/prompts/personal")
async def delete_personal_prompt(
    user: User = Depends(get_current_user)
):
    """删除用户个人提示词"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        # 检查是否存在个人提示词
        personal_prompt = manager.get_user_personal_prompt(user.username)
        if not personal_prompt:
            raise HTTPException(status_code=404, detail="个人提示词不存在")
        
        # 删除个人提示词文件
        success = manager.storage.delete_user_personal_prompt(user.username)
        if not success:
            raise HTTPException(status_code=500, detail="删除个人提示词失败")
        
        logger.info(f"用户 {user.username} 删除了个人提示词")
        
        return {"success": True, "message": "个人提示词已删除"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除个人提示词失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@auth_router.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user)
):
    """删除提示词"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # 检查权限
    if prompt_id.startswith('global_'):
        if not user.is_admin():
            raise HTTPException(status_code=403, detail="只有管理员可以删除全局提示词")
        
        success = manager.delete_global_prompt(prompt_id)
        if success:
            logger.info(f"管理员 {user.username} 删除了全局提示词: {prompt_id}")
        else:
            raise HTTPException(status_code=404, detail="提示词不存在")
    else:
        # 个人提示词 - 用户只能删除自己的
        if not prompt_id.startswith(f"personal_{user.username}"):
            raise HTTPException(status_code=403, detail="只能删除自己的个人提示词")
        
        # 清空个人提示词
        success = manager.save_user_personal_prompt(user.username, {})
        if success:
            logger.info(f"用户 {user.username} 清空了个人提示词")
        else:
            raise HTTPException(status_code=500, detail="删除个人提示词失败")
    
    return {"success": True, "message": "提示词已删除"}


@auth_router.get("/prompts/merged")
async def get_merged_prompts(
    user: User = Depends(get_current_user)
):
    """获取用户合并后的提示词"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    merged_prompts = manager.get_merged_prompts(user.username)
    
    return {
        "prompts": merged_prompts,
        "count": len(merged_prompts)
    }


# === 简化的提示词管理API ===

@auth_router.get("/prompts/simple")
async def get_simple_prompts(
    user: User = Depends(get_current_user)
):
    """获取简化的全局提示词列表"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # 获取全局提示词集合
    global_prompts = manager.get_global_prompts()
    
    # 查找名为"Simple Prompts"的全局提示词集合
    simple_prompts_collection = None
    for prompt_file in global_prompts:
        if prompt_file.name == "Simple Prompts":
            simple_prompts_collection = prompt_file
            break
    
    if simple_prompts_collection:
        # 加载提示词内容
        prompts_dict = manager.storage.load_prompts_from_json(
            Path(simple_prompts_collection.file_path)
        )
        
        # 转换为简化的格式
        simple_prompts = [
            {"id": f"global_{i}", "name": name, "content": content}
            for i, (name, content) in enumerate(prompts_dict.items())
        ]
        
        return simple_prompts
    else:
        return []


@auth_router.post("/prompts/simple")
async def add_simple_prompt(
    request: Request,
    user: User = Depends(get_current_user)
):
    """添加简化的全局提示词"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        content = data.get("content", "").strip()
        
        if not name or not content:
            raise HTTPException(status_code=400, detail="提示词描述和内容不能为空")
        
        # 获取全局提示词集合
        global_prompts = manager.get_global_prompts()
        
        # 查找名为"Simple Prompts"的全局提示词集合
        simple_prompts_collection = None
        for prompt_file in global_prompts:
            if prompt_file.name == "Simple Prompts":
                simple_prompts_collection = prompt_file
                break
        
        if simple_prompts_collection:
            # 加载现有提示词
            prompts_dict = manager.storage.load_prompts_from_json(
                Path(simple_prompts_collection.file_path)
            )
        else:
            # 创建新的全局提示词集合
            prompts_dict = {}
            simple_prompts_collection = manager.create_global_prompt(
                name="Simple Prompts",
                prompts_dict={},
                owner=user.username,
                description="简化的全局提示词集合"
            )
        
        # 添加新提示词
        prompts_dict[name] = content
        
        # 更新全局提示词
        success = manager.update_global_prompt(
            simple_prompts_collection.id,
            prompts_dict,
            user.username
        )
        if not success:
            raise HTTPException(status_code=500, detail="保存提示词失败")
        
        logger.info(f"用户 {user.username} 添加了全局提示词: {name}")
        
        return {"success": True, "message": "提示词添加成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加提示词失败: {e}")
        raise HTTPException(status_code=500, detail=f"添加失败: {str(e)}")


@auth_router.delete("/prompts/simple/{prompt_id}")
async def delete_simple_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user)
):
    """删除简化的全局提示词"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        # 解析提示词ID
        if not prompt_id.startswith("global_"):
            raise HTTPException(status_code=400, detail="无效的提示词ID")
        
        index = int(prompt_id.replace("global_", ""))
        
        # 获取全局提示词集合
        global_prompts = manager.get_global_prompts()
        
        # 查找名为"Simple Prompts"的全局提示词集合
        simple_prompts_collection = None
        for prompt_file in global_prompts:
            if prompt_file.name == "Simple Prompts":
                simple_prompts_collection = prompt_file
                break
        
        if not simple_prompts_collection:
            raise HTTPException(status_code=404, detail="全局提示词集合不存在")
        
        # 加载提示词
        prompts_dict = manager.storage.load_prompts_from_json(
            Path(simple_prompts_collection.file_path)
        )
        
        # 获取要删除的提示词名称
        prompt_names = list(prompts_dict.keys())
        if index >= len(prompt_names):
            raise HTTPException(status_code=404, detail="提示词不存在")
        
        prompt_name = prompt_names[index]
        
        # 删除提示词
        del prompts_dict[prompt_name]
        
        # 更新全局提示词
        success = manager.update_global_prompt(
            simple_prompts_collection.id,
            prompts_dict,
            user.username
        )
        if not success:
            raise HTTPException(status_code=500, detail="保存提示词失败")
        
        logger.info(f"用户 {user.username} 删除了全局提示词: {prompt_name}")
        
        return {"success": True, "message": "提示词删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除提示词失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@auth_router.post("/app-config")
async def update_app_config_api(
    request: Request,
    user: User = Depends(get_current_user)
):
    """更新应用配置（需要管理员或管理组权限；仅超级管理员可改默认密码）"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")
    
    try:
        config_data = await request.json()
        
        # 将LDAP相关键与App配置键分离处理，避免LDAP键误入app_config
        ldap_keys = {
            'ldap_enabled','ldap_protocol','ldap_host','ldap_port','ldap_bind_dn_template','ldap_base_dn',
            'ldap_user_filter','ldap_tls_cacertfile','ldap_tls_verify','ldap_admin_group_enabled','ldap_admin_group',
            'ldap_glossary_group_enabled','ldap_glossary_group','ldap_group_base_dn'
        }
        ldap_updates = {k: v for k, v in config_data.items() if k in ldap_keys}
        config_data = {k: v for k, v in config_data.items() if k not in ldap_keys}
        
        # 先处理LDAP更新（统一到新键），并写入auth_config
        if ldap_updates:
            try:
                from .config import get_auth_config as _get_auth_cfg, save_auth_config as _save_auth_cfg
                auth_cfg = _get_auth_cfg()
                # 保存前备份端点相关旧值
                import copy
                old_for_endpoint = copy.deepcopy(auth_cfg)
                auth_cfg.update_from_dict(ldap_updates)
                if _save_auth_cfg():
                    logger.info(f"[APP-CONFIG] 同步保存LDAP配置成功: {list(ldap_updates.keys())}")
                    # 同步刷新本模块内的内存实例，确保后续GET读取最新值
                    try:
                        global _auth_config
                        if _auth_config is not None:
                            _auth_config.update_from_dict(ldap_updates)
                            logger.info("[APP-CONFIG] 已同步更新模块内_auth_config")
                        # 热重载LDAP客户端（若端点变化）
                        _refresh_ldap_client_if_endpoint_changed(old_for_endpoint, auth_cfg)
                    except Exception as _e:
                        logger.warning(f"[APP-CONFIG] 同步模块内内存失败: {_e}")
                else:
                    logger.warning("[APP-CONFIG] 同步保存LDAP配置失败")
            except Exception as _e:
                logger.error(f"[APP-CONFIG] 处理LDAP配置时异常: {_e}")

        app_config = get_app_config()
        
        # 移除任何来自前端的 platform_api_keys（敏感信息不保存在应用配置）
        if 'platform_api_keys' in config_data:
            del config_data['platform_api_keys']
        
        
        # 处理Mineru Token（保存到敏感配置） - 支持 {key, configured}
        if 'translator_mineru_token' in config_data:
            token_val = config_data['translator_mineru_token']
            from ..config.secrets_manager import get_secrets_manager
            secrets_manager = get_secrets_manager()
            if isinstance(token_val, dict):
                raw = token_val.get('key', '')
                configured = token_val.get('configured')
                if raw and not str(raw).endswith('***'):
                    secrets_manager.update_mineru_token(str(raw), configured)
            else:
                raw = token_val
                if raw and not str(raw).endswith('***'):
                    secrets_manager.update_mineru_token(str(raw))
            del config_data['translator_mineru_token']
        
        # 禁止非超级管理员修改默认密码
        if not user.is_super_admin() and 'default_password' in config_data:
            del config_data['default_password']
        
        # 处理Web/HTTPS相关字段写入全局配置
        from ..config.global_config import get_global_config, save_global_config
        global_cfg = get_global_config()

        https_keys = {
            'https_enabled', 'https_force_redirect'
        }

        https_updates = {k: v for k, v in config_data.items() if k in https_keys}

        # 证书路径与私钥路径放入全局配置（作为普通字段存储路径字符串）
        if 'https_cert_file' in config_data:
            global_cfg.https_cert_file = config_data['https_cert_file'] or None
        if 'https_key_file' in config_data:
            global_cfg.https_key_file = config_data['https_key_file'] or None
        for k, v in https_updates.items():
            setattr(global_cfg, k, v)

        # 若请求启用HTTPS，则在保存前进行强校验（保证已通过测试）
        try:
            if bool(global_cfg.https_enabled):
                cert_file = global_cfg.https_cert_file
                key_file = global_cfg.https_key_file
                if not (cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file)):
                    raise HTTPException(status_code=400, detail="Enable HTTPS failed: certificate or key not found")
                import ssl as _ssl
                from ..config.secrets_manager import get_secrets_manager as _get_sm
                _pwd = _get_sm().get_web_tls_password()
                ctx = _ssl.create_default_context(purpose=_ssl.Purpose.CLIENT_AUTH)
                ctx.load_cert_chain(certfile=cert_file, keyfile=key_file, password=_pwd)
        except HTTPException:
            raise
        except Exception as _e:
            raise HTTPException(status_code=400, detail=f"Enable HTTPS failed: {str(_e)}")

        # Handle AI platform configuration updates
        ai_platform_updates = {}
        translator_settings_updates = {}
        
        if 'ai_platforms' in config_data:
            ai_platforms_data = config_data['ai_platforms']
            # Remove API keys from platform data (they are stored separately)
            for platform_key, platform_data in ai_platforms_data.items():
                if isinstance(platform_data, dict):
                    platform_data = platform_data.copy()
                    platform_data.pop('api_key', None)
                    ai_platforms_data[platform_key] = platform_data
            
            ai_platform_updates['ai_platforms'] = ai_platforms_data
            del config_data['ai_platforms']
        
        if 'translator_settings' in config_data:
            translator_settings_updates['translator_settings'] = config_data['translator_settings']
            del config_data['translator_settings']
        
        # Update global configuration with new structured data
        if ai_platform_updates or translator_settings_updates:
            global_cfg.update_from_dict({**ai_platform_updates, **translator_settings_updates})
        
        # 处理默认语言，写入全局配置根字段
        if 'default_language' in config_data:
            try:
                dl = str(config_data.get('default_language') or '').lower()
                if dl in ('zh', 'en'):
                    setattr(global_cfg, 'default_language', dl)
                else:
                    # 简单兜底：非预期值一律按en
                    setattr(global_cfg, 'default_language', 'en')
            except Exception as _e:
                logger.warning(f"[APP-CONFIG] 更新默认语言失败: {_e}")
            finally:
                # 避免同时写入用户级App配置
                del config_data['default_language']

        # 更新其他配置（用户级App配置）
        app_config.update_from_dict({k: v for k, v in config_data.items() if k not in https_keys and k not in ['https_cert_file','https_key_file']})
        
        # 保存配置
        # 保存HTTPS私钥密码到敏感配置
        from ..config.secrets_manager import get_secrets_manager
        secrets_manager = get_secrets_manager()
        if 'https_key_password' in config_data:
            secrets_manager.update_web_tls_password(config_data.get('https_key_password') or None)

        ok1 = save_app_config()
        ok2 = save_global_config()
        if ok1 and ok2:
            logger.info(f"应用配置已由用户 {_mask_username(user.username)} 更新")
            return {"success": True, "message": "Configuration updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        logger.error(f"更新应用配置失败: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update configuration: {str(e)}")


@auth_router.post("/app-config/setting")
async def update_single_setting(
    request: Request,
    user: User = Depends(get_current_user)
):
    """更新单个设置项"""
    try:
        data = await request.json()
        key = data.get('key')
        value = data.get('value')
        
        if not key:
            raise HTTPException(status_code=400, detail="Setting key is required")
        
        from .user_profile import get_user_profile_manager
        from ..config.global_config import get_global_config, save_global_config
        from ..config.secrets_manager import get_secrets_manager
        
        profile_manager = get_user_profile_manager()
        global_config = get_global_config()

        # 定义敏感配置键（只有管理员可以修改，保存到local_secrets.json）
        sensitive_config_keys = [
            'translator_mineru_token',
            'platform_api_keys',
            'default_password',
            'session_secret_key',
            'redis_password'
        ]
        
        # 定义全局配置键（只有管理员可以修改）
        global_config_keys = [
            'translator_convert_engine', 'translator_mineru_model_version',
            'translator_formula_ocr', 'translator_code_ocr', 'translator_skip_translate',
            'platform_urls', 'platform_models', 'active_task_ids',
            # Web/HTTPS 设置
            'https_enabled', 'https_force_redirect', 'https_cert_file', 'https_key_file',
            # LDAP配置键
            'ldap_enabled', 'ldap_protocol', 'ldap_host', 'ldap_port', 'ldap_bind_dn_template',
            'ldap_base_dn', 'ldap_user_filter', 'ldap_tls_cacertfile', 'ldap_tls_verify'
        ]

        # 定义用户配置键（所有用户都可以修改）
        user_config_keys = [
            'ui_language', 'translator_last_workflow', 'translator_auto_workflow_enabled',
            'translator_txt_insert_mode', 'translator_txt_separator',
            'translator_xlsx_insert_mode', 'translator_xlsx_separator', 'translator_xlsx_translate_regions',
            'translator_docx_insert_mode', 'translator_docx_separator',
            'translator_srt_insert_mode', 'translator_srt_separator',
            'translator_epub_insert_mode', 'translator_epub_separator',
            'translator_html_insert_mode', 'translator_html_separator',
            'translator_json_paths', 'translator_target_language', 'translator_custom_language',
            'translator_custom_prompt', 'translator_thinking_mode', 'theme',
            'translator_platform_type', 'translator_temperature', 'translator_max_tokens', 'translator_top_p',
            'translator_frequency_penalty', 'translator_presence_penalty',
            'chunk_size', 'concurrent',
            'glossary_generate_enable', 'glossary_agent_config_choice', 'glossary_agent_thinking_mode',
            'glossary_agent_platform_type', 'glossary_agent_temperature', 'glossary_agent_max_tokens', 'glossary_agent_top_p',
            'glossary_agent_frequency_penalty', 'glossary_agent_presence_penalty', 'glossary_agent_to_lang',
            'glossary_agent_chunk_size', 'glossary_agent_concurrent',
            # 用户维度模型覆盖字典键
            'translator_platform_models', 'glossary_agent_platform_models'
        ]
        
        # 权限检查
        if key in sensitive_config_keys:
            # 敏感配置，只有管理员可以修改
            if not user.is_admin():
                logger.warning(f"LDAP用户 {_mask_username(user.username)} 尝试修改敏感配置: {key}")
                raise HTTPException(status_code=403, detail="Access denied: Only admin can modify sensitive settings")
            # 默认密码仅超级管理员可改
            if key == 'default_password' and not user.is_super_admin():
                logger.warning(f"非超级管理员 {_mask_username(user.username)} 试图修改默认密码")
                raise HTTPException(status_code=403, detail="Only super admin can change default password")
        elif key in global_config_keys:
            # 全局配置，只有管理员可以修改
            if not user.is_admin():
                logger.warning(f"LDAP用户 {_mask_username(user.username)} 尝试修改全局配置: {key}")
                raise HTTPException(status_code=403, detail="Access denied: Only admin can modify global settings")
        elif key in user_config_keys:
            # 用户配置，所有用户都可以修改
            pass
        else:
            # 未知配置键
            logger.warning(f"用户 {_mask_username(user.username)} 尝试修改未知配置: {key}")
            raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")
        
        # 根据配置类型进行更新
        if key in sensitive_config_keys:
            # 更新敏感配置（保存到local_secrets.json）
            secrets_manager = get_secrets_manager()
            
            if key == 'translator_mineru_token':
                if secrets_manager.update_mineru_token(value):
                    logger.info(f"MinerU令牌已由用户 {_mask_username(user.username)} 更新")
                    return {"success": True, "message": "MinerU token updated successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to save MinerU token")
            
            elif key == 'platform_api_keys':
                # 处理平台API密钥字典
                if isinstance(value, dict):
                    updated_any = False
                    for platform, api_key in value.items():
                        # 兼容：value可能是 {platform: str} 或 {platform: {key, configured}}
                        configured_flag = None
                        if isinstance(api_key, dict):
                            configured_flag = api_key.get('configured')
                            api_key = api_key.get('key', '')
                        if api_key and str(api_key).strip():  # 只保存非空密钥
                            if secrets_manager.update_api_key(platform, str(api_key), configured_flag):
                                updated_any = True
                    # 同步刷新内存中的全局配置，确保刷新页面即可看到最新脱敏密钥
                    if updated_any:
                        try:
                            from ..config.global_config import get_global_config
                            global_config = get_global_config()
                            for platform, api_key in value.items():
                                if isinstance(api_key, dict):
                                    raw_key = api_key.get('key', '')
                                else:
                                    raw_key = str(api_key) if api_key is not None else ''
                                if raw_key and raw_key.strip():
                                    global_config.update_platform_api_key(platform, raw_key)
                        except Exception as _e:
                            logger.warning(f"刷新内存全局API密钥失败: {_e}")
                    logger.info(f"平台API密钥已由用户 {_mask_username(user.username)} 更新")
                    return {"success": True, "message": "Platform API keys updated successfully"}
                else:
                    raise HTTPException(status_code=400, detail="Platform API keys must be a dictionary")
            
            elif key in ['default_password', 'session_secret_key', 'redis_password']:
                if secrets_manager.update_auth_secret(key, value):
                    logger.info(f"认证敏感配置 {key} 已由用户 {_mask_username(user.username)} 更新")
                    return {"success": True, "message": f"Auth secret {key} updated successfully"}
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to save auth secret {key}")
            
            elif key == 'docling_auth':
                if isinstance(value, dict):
                    if get_secrets_manager().update_docling_auth(value):
                        logger.info(f"Docling鉴权已由用户 {_mask_username(user.username)} 更新")
                        return {"success": True, "message": "Docling auth updated successfully"}
                    else:
                        raise HTTPException(status_code=500, detail="Failed to save Docling auth")
                else:
                    raise HTTPException(status_code=400, detail="Docling auth must be a dictionary")
            else:
                raise HTTPException(status_code=400, detail=f"Unknown sensitive setting key: {key}")
        
        elif key in global_config_keys:
            # 更新全局配置
            if key.startswith('platform_') and key.endswith('_model_id'):
                # 处理平台模型
                platform = key.replace('translator_platform_', '').replace('_model_id', '')
                global_config.update_platform_model(platform, value)
            elif key.startswith('glossary_agent_platform_') and key.endswith('_model_id'):
                # 处理术语表平台模型
                platform = key.replace('glossary_agent_platform_', '').replace('_model_id', '')
                global_config.update_glossary_platform_model(platform, value)
            elif key.startswith('ldap_'):
                # 处理LDAP配置
                from .config import get_auth_config, save_auth_config
                auth_config = get_auth_config()
                if hasattr(auth_config, key):
                    setattr(auth_config, key, value)
                    if save_auth_config():
                        logger.info(f"LDAP设置项 {key} 已由用户 {_mask_username(user.username)} 更新")
                        return {"success": True, "message": f"LDAP setting {key} updated successfully"}
                    else:
                        raise HTTPException(status_code=500, detail="Failed to save LDAP configuration")
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown LDAP setting key: {key}")
            else:
                # 处理普通全局配置项
                if hasattr(global_config, key):
                    setattr(global_config, key, value)
                elif key in ['translator_convert_engine', 'translator_mineru_model_version', 'translator_formula_ocr', 'translator_code_ocr', 'translator_skip_translate']:
                    # 处理 translator_settings 中的字段
                    if key == 'translator_convert_engine':
                        global_config.translator_settings.convert_engine = value
                    elif key == 'translator_mineru_model_version':
                        global_config.translator_settings.mineru_model_version = value
                    elif key == 'translator_formula_ocr':
                        global_config.translator_settings.formula_ocr = value
                    elif key == 'translator_code_ocr':
                        global_config.translator_settings.code_ocr = value
                    elif key == 'translator_skip_translate':
                        global_config.translator_settings.skip_translate = value
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown global setting key: {key}")
            
            # 保存全局配置
            if save_global_config():
                logger.info(f"Global setting {key} updated by user {_mask_username(user.username)}")
                return {"success": True, "message": f"Global setting {key} updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to save global configuration")
        
        else:
            # 更新用户配置（包括按用户维度的模型键）
            if profile_manager.update_user_setting(user.username, key, value):
                logger.info(f"User setting {key} updated by user {_mask_username(user.username)}")
                return {"success": True, "message": f"User setting {key} updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to save user configuration")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新设置项失败: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update setting: {str(e)}")


# === LDAP 配置专用读写接口（统一入口）===
@auth_router.get("/ldap-config")
async def get_ldap_config_api(user: User = Depends(get_current_user)):
    """读取LDAP相关配置（登录即可读取；敏感信息不返回）"""
    config = get_auth_config()
    return {
        "ldap_enabled": config.ldap_enabled,
        "ldap_protocol": config.ldap_protocol,
        "ldap_host": config.ldap_host,
        "ldap_port": config.ldap_port,
        "ldap_bind_dn_template": config.ldap_bind_dn_template,
        "ldap_base_dn": config.ldap_base_dn,
        "ldap_user_filter": config.ldap_user_filter,
        "ldap_tls_cacertfile": config.ldap_tls_cacertfile,
        "ldap_tls_verify": config.ldap_tls_verify,
        "ldap_admin_group_enabled": config.ldap_admin_group_enabled,
        "ldap_admin_group": config.ldap_admin_group,
        "ldap_glossary_group_enabled": getattr(config, 'ldap_glossary_group_enabled', False),
        "ldap_glossary_group": getattr(config, 'ldap_glossary_group', ''),
        "ldap_group_base_dn": config.ldap_group_base_dn,
    }


@auth_router.post("/ldap-config")
async def update_ldap_config_api(request: Request, user: User = Depends(get_current_user)):
    """统一更新LDAP相关配置（需要管理员或管理组权限）。"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")

    try:
        data = await request.json()

        # 仅处理新键名

        # 仅提取LDAP相关字段
        allowed = {
            'ldap_enabled', 'ldap_protocol', 'ldap_host', 'ldap_port', 'ldap_bind_dn_template', 'ldap_base_dn',
            'ldap_user_filter', 'ldap_tls_cacertfile', 'ldap_tls_verify', 'ldap_admin_group_enabled', 'ldap_admin_group',
            'ldap_glossary_group_enabled', 'ldap_glossary_group', 'ldap_group_base_dn'
        }
        update_payload = {k: v for k, v in data.items() if k in allowed}

        # 类型处理
        if 'ldap_port' in update_payload:
            try:
                update_payload['ldap_port'] = int(update_payload['ldap_port'])
            except Exception:
                pass
        for b in ['ldap_enabled', 'ldap_tls_verify', 'ldap_admin_group_enabled', 'ldap_glossary_group_enabled']:
            if b in update_payload and isinstance(update_payload[b], str):
                update_payload[b] = update_payload[b].lower() in ("true", "1", "yes", "on")

        # Check if trying to enable LDAP without test validation
        if update_payload.get('ldap_enabled', False):
            # Check if this is a test validation request
            test_validated = data.get('ldap_test_validated', False)
            if not test_validated:
                return JSONResponse(
                    status_code=400, 
                    content={
                        "ok": False, 
                        "message": "LDAP test must be performed and passed before enabling LDAP. Please test the connection first."
                    }
                )

        # 更新并保存
        from .config import get_auth_config as _get_auth_cfg, save_auth_config as _save_auth_cfg
        auth_cfg = _get_auth_cfg()
        logger.info(f"[LDAP-API] 规范化后的更新字段: {update_payload}")
        auth_cfg.update_from_dict(update_payload)
        saved = _save_auth_cfg()
        # 同步更新本模块内存中的全局配置，避免重启才生效
        try:
            local_cfg = get_auth_config()
            local_cfg.update_from_dict(update_payload)
            logger.info("[LDAP-API] 已同步更新内存配置")
        except Exception:
            pass
        if saved:
            logger.info(f"LDAP配置已由用户 {_mask_username(user.username)} 更新")
            # 同步刷新本模块内的内存实例，避免刷新页仍读旧值
            try:
                global _auth_config
                if _auth_config is not None:
                    _auth_config.update_from_dict(update_payload)
                    logger.info("[LDAP-API] 已同步更新模块内_auth_config")
            except Exception as _e:
                logger.warning(f"[LDAP-API] 同步内存配置失败: {_e}")
            return {"success": True, "message": "LDAP configuration updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save LDAP configuration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新LDAP配置失败: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update LDAP configuration: {str(e)}")


# === Message 配置专用读写接口 ===
@auth_router.get("/message-config")
async def get_message_config_api():
    """读取消息相关配置（公开接口，无需认证）"""
    from .config import AuthConfig
    config = AuthConfig.get_config()
    return {
        "login_banner": config.login_banner,
        "usage_message": config.usage_message,
    }


@auth_router.post("/message-config")
async def update_message_config_api(request: Request, user: User = Depends(get_current_user)):
    """更新消息相关配置（需要管理员权限）"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")

    try:
        data = await request.json()

        # 仅提取消息相关字段
        allowed = {'login_banner', 'usage_message'}
        update_payload = {k: v for k, v in data.items() if k in allowed}

        # 更新并保存
        from .config import AuthConfig
        auth_cfg = AuthConfig.get_config()
        logger.info(f"[Message-API] 更新字段: {update_payload}")
        auth_cfg.update_from_dict(update_payload)
        saved = auth_cfg.save_to_file()
        
        # 同步更新本模块内存中的全局配置
        try:
            local_cfg = get_auth_config()
            local_cfg.update_from_dict(update_payload)
            logger.info("[Message-API] 已同步更新内存配置")
        except Exception:
            pass
            
        if saved:
            logger.info(f"消息配置已由用户 {_mask_username(user.username)} 更新")
            return {"success": True, "message": "Message configuration updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save message configuration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新消息配置失败: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update message configuration: {str(e)}")

# 兼容性路由（不使用/auth前缀）
@auth_compat_router.get("/login")
async def login_page_compat(request: Request, next_url: Optional[str] = None):
    """兼容性登录页面（不带/auth前缀）"""
    return await login_page(request, next_url)


@auth_compat_router.post("/login")
async def login_compat(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None)
):
    """兼容性登录处理（不带/auth前缀）"""
    return await login(request, response, username, password, next_url)


@auth_compat_router.get("/logout")
async def logout_get_compat(request: Request, response: Response):
    """兼容性登出（不带/auth前缀）"""
    return await logout_get(request, response)


@auth_router.post("/test-ai-platform")
async def test_ai_platform(
    request: Request,
    user: User = Depends(get_current_user)
):
    """测试AI平台连接"""
    try:
        data = await request.json()
        platform_type = data.get('platform_type')
        base_url = data.get('base_url')
        model_name = data.get('model_name')
        
        if not platform_type or not base_url or not model_name:
            raise HTTPException(status_code=400, detail="Missing required parameters: platform_type, base_url, model_name")
        
        # 获取API key
        from ..config.secrets_manager import get_secrets_manager
        secrets_manager = get_secrets_manager()
        api_keys = secrets_manager.get_api_keys()
        api_key = api_keys.get(platform_type)
        
        if not api_key:
            raise HTTPException(status_code=400, detail=f"No API key found for platform: {platform_type}")
        
        # 根据平台类型构建测试请求
        test_payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "Hello, this is a connection test."}
            ],
            "max_tokens": 10
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        # 发送测试请求
        async with httpx.AsyncClient(timeout=30.0) as client:
            if platform_type == "anthropic":
                # Anthropic 使用不同的API格式
                test_payload = {
                    "model": model_name,
                    "max_tokens": 10,
                    "messages": [
                        {"role": "user", "content": "Hello, this is a connection test."}
                    ]
                }
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                response = await client.post(f"{base_url}/messages", json=test_payload, headers=headers)
            elif platform_type == "google":
                # Google 使用不同的API格式
                test_payload = {
                    "contents": [
                        {"parts": [{"text": "Hello, this is a connection test."}]}
                    ],
                    "generationConfig": {
                        "maxOutputTokens": 10
                    }
                }
                headers = {
                    "Content-Type": "application/json"
                }
                response = await client.post(f"{base_url}/models/{model_name}:generateContent?key={api_key}", json=test_payload, headers=headers)
            else:
                # 标准OpenAI格式
                response = await client.post(f"{base_url}/chat/completions", json=test_payload, headers=headers)
            
            if response.status_code == 200:
                return {"success": True, "message": "AI platform connection test successful"}
            else:
                error_detail = response.text
                return {"success": False, "error": f"API returned status {response.status_code}: {error_detail}"}
                
    except httpx.TimeoutException:
        return {"success": False, "error": "Connection timeout - please check your network and API endpoint"}
    except httpx.ConnectError:
        return {"success": False, "error": "Connection failed - please check the API URL"}
    except Exception as e:
        logger.error(f"AI platform test failed: {e}")
        return {"success": False, "error": f"Test failed: {str(e)}"}


@auth_router.post("/mineru/test-connection")
async def test_mineru_connection(request: Request):
    """测试MinerU连接"""
    try:
        # 检查用户权限
        if not _session_manager:
            raise HTTPException(status_code=401, detail="会话管理器未初始化")
        
        user = await _session_manager.get_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="未登录或会话已过期")
        
        # 获取MinerU token
        try:
            sm = get_secrets_manager()
            mineru_token = sm.get_mineru_token()
            
            if not mineru_token:
                return {"success": False, "message": "MinerU API Key未配置"}
            
            # 测试MinerU API连接
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {mineru_token}'
            }
            
            # 使用一个简单的测试请求 - 使用PDF文件类型
            test_data = {
                "files": [
                    {"name": "test.pdf", "is_ocr": True}
                ]
            }
            
            logger.info("MinerU连接测试: 开始测试API连接")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    'https://mineru.net/api/v4/file-urls/batch',
                    headers=headers,
                    json=test_data
                )
                
                logger.info(f"MinerU连接测试: API响应状态 {response.status_code}")
                if response.status_code != 200:
                    logger.warning(f"MinerU连接测试: API请求失败，状态码 {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        return {"success": True, "message": "MinerU连接测试成功"}
                    else:
                        error_msg = result.get('message', '未知错误')
                        error_code = result.get('code', 'N/A')
                        return {"success": False, "message": f"MinerU API返回错误: {error_msg} (错误代码: {error_code})"}
                elif response.status_code == 401:
                    return {"success": False, "message": "MinerU API Key无效或已过期"}
                else:
                    try:
                        error_detail = response.text
                        return {"success": False, "message": f"MinerU API请求失败: {response.status_code} - {error_detail}"}
                    except:
                        return {"success": False, "message": f"MinerU API请求失败: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"MinerU连接测试失败: {e}")
            return {"success": False, "message": f"连接测试失败: {str(e)}"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MinerU测试连接端点错误: {e}")
        raise HTTPException(status_code=500, detail="服务器内部错误")


@auth_router.get("/certificate-list")
async def get_certificate_list(user: User = Depends(get_current_user)):
    """Get list of certificates in certs directory"""
    try:
        import os
        import subprocess
        from pathlib import Path
        from datetime import datetime
        
        certs_dir = Path("certs")
        certificates = []
        
        if certs_dir.exists():
            for file_path in certs_dir.iterdir():
                if file_path.is_file() and file_path.suffix in ['.crt', '.key', '.pem']:
                    stat = file_path.stat()
                    file_type = 'cert' if file_path.suffix in ['.crt', '.pem'] else 'key'
                    
                    cert_info = {
                        'name': file_path.name,
                        'type': file_type,
                        'size': f"{stat.st_size} bytes",
                        'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # For certificate files, try to get validity period
                    if file_type == 'cert':
                        try:
                            # Use openssl to get certificate validity
                            result = subprocess.run([
                                'openssl', 'x509', '-in', str(file_path), '-noout', '-dates'
                            ], capture_output=True, text=True, check=True)
                            
                            # Parse the output to extract dates
                            output = result.stdout
                            not_before = None
                            not_after = None
                            
                            for line in output.split('\n'):
                                if line.startswith('notBefore='):
                                    not_before = line.split('=', 1)[1].strip()
                                elif line.startswith('notAfter='):
                                    not_after = line.split('=', 1)[1].strip()
                            
                            if not_after:
                                # Parse the date and check if it's expired
                                try:
                                    # OpenSSL date format: Oct  2 19:42:59 2025 GMT
                                    from datetime import datetime
                                    parsed_date = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z')
                                    now = datetime.now()
                                    
                                    cert_info['valid_until'] = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                                    cert_info['is_expired'] = parsed_date < now
                                    
                                    # Calculate days until expiration
                                    days_left = (parsed_date - now).days
                                    if days_left < 0:
                                        cert_info['days_left'] = f"Expired {abs(days_left)} days ago"
                                    elif days_left == 0:
                                        cert_info['days_left'] = "Expires today"
                                    else:
                                        cert_info['days_left'] = f"{days_left} days left"
                                        
                                except ValueError:
                                    cert_info['valid_until'] = not_after
                                    cert_info['days_left'] = "Unknown"
                                    cert_info['is_expired'] = False
                                    
                        except (subprocess.CalledProcessError, FileNotFoundError):
                            # If openssl is not available or fails, skip validity info
                            pass
                    
                    certificates.append(cert_info)
        
        return {"certificates": certificates}
        
    except Exception as e:
        logger.error(f"Failed to get certificate list: {e}")
        raise HTTPException(status_code=500, detail="Failed to get certificate list")


@auth_router.post("/generate-certificate")
async def generate_certificate(request: Request, user: User = Depends(get_current_user)):
    """Generate temporary SSL certificate"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")
    
    try:
        data = await request.json()
        platform = data.get('platform', 'linux')
        
        import os
        import subprocess
        from pathlib import Path
        
        # Create certs directory if it doesn't exist
        certs_dir = Path("certs")
        certs_dir.mkdir(exist_ok=True)
        
        # Change to certs directory
        os.chdir(certs_dir)
        
        try:
            # Generate private key
            subprocess.run([
                'openssl', 'genrsa', '-out', 'server.key', '2048'
            ], check=True, capture_output=True)
            
            # Generate CSR
            subprocess.run([
                'openssl', 'req', '-new', '-key', 'server.key', '-out', 'server.csr',
                '-subj', '/C=US/ST=State/L=City/O=Organization/CN=localhost'
            ], check=True, capture_output=True)
            
            # Generate self-signed certificate
            subprocess.run([
                'openssl', 'x509', '-req', '-days', '365', '-in', 'server.csr',
                '-signkey', 'server.key', '-out', 'server.crt'
            ], check=True, capture_output=True)
            
            # Set proper permissions (Linux/Unix)
            if platform == 'linux':
                os.chmod('server.key', 0o600)
                os.chmod('server.crt', 0o644)
            
            # Clean up CSR file
            if Path('server.csr').exists():
                Path('server.csr').unlink()
            
            logger.info(f"Certificate generated successfully by user {_mask_username(user.username)}")
            return {"success": True, "message": "Certificate generated successfully"}
            
        except subprocess.CalledProcessError as e:
            logger.error(f"OpenSSL command failed: {e}")
            return {"success": False, "message": f"Certificate generation failed: {e.stderr.decode() if e.stderr else str(e)}"}
        
        finally:
            # Change back to original directory
            os.chdir('..')
            
    except Exception as e:
        logger.error(f"Certificate generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Certificate generation failed: {str(e)}")
