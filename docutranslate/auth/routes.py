# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from fastapi import APIRouter, Request, Response, HTTPException, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import time
import logging
import os

from .config import AuthConfig
from .ldap_client import LDAPClient, InvalidCredentials
from .session_manager import AuthSessionManager
from .models import LoginRequest, LoginResponse, LogoutResponse, UserInfo, User, UserRole
from ..config import get_app_config, save_app_config

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

# 模板目录
templates = Jinja2Templates(directory="docutranslate/template")

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
    """登录页面"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "next_url": next_url,
        "error": error,
        "ldap_enabled": get_auth_config().ldap_enabled
    })


@auth_router.post("/login", response_class=JSONResponse)
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None)
):
    """处理登录请求"""
    config = get_auth_config()
    session_manager = get_session_manager()
    ldap_client = get_ldap_client()
    
    # 获取客户端IP
    client_ip = request.client.host if request.client else "unknown"
    
    logger.info(f"收到登录请求 - 用户: {_mask_username(username)}, IP: {client_ip}")
    logger.info(f"认证配置 - LDAP启用: {config.ldap_enabled}, LDAP客户端: {ldap_client is not None}")
    
    # 检查登录尝试次数
    attempts = session_manager.get_login_attempts(client_ip)
    logger.info(f"当前登录尝试次数: {attempts}/{config.max_login_attempts}")
    
    if attempts >= config.max_login_attempts:
        logger.warning(f"IP {client_ip} 登录尝试次数过多，已锁定")
        raise HTTPException(
            status_code=429,
            detail=f"Too many login attempts. Please try again in {config.login_attempt_window // 60} minutes."
        )
    
    try:
        user: User
        
        # 混合认证策略：
        # 1. 如果用户名是admin，始终使用本地认证，获得ADMIN角色
        # 2. 如果LDAP启用且用户名不是admin，使用LDAP认证，获得LDAP_USER角色
        # 3. 如果LDAP禁用，只使用本地admin认证
        
        if username == config.default_username:
            # admin用户始终使用本地认证
            logger.info(f"使用本地认证admin用户: {_mask_username(username)}")
            if password == config.default_password:
                user = User(
                    username=username,
                    display_name="Administrator",
                    email=None,
                    is_authenticated=True,
                    role=UserRole.ADMIN  # admin用户始终是管理员
                )
                logger.info(f"admin用户认证成功: {_mask_username(username)}")
            else:
                logger.warning(f"admin用户认证失败: {_mask_username(username)}")
                raise InvalidCredentials("Invalid username or password")
        elif config.ldap_enabled and ldap_client:
            # 非admin用户使用LDAP认证
            logger.info(f"使用LDAP认证用户: {_mask_username(username)}")
            user = ldap_client.authenticate(username, password)
            logger.info(f"LDAP认证成功，用户: {_mask_username(username)}")
        else:
            # LDAP禁用且不是admin用户
            logger.warning(f"LDAP禁用且非admin用户尝试登录: {_mask_username(username)}")
            raise InvalidCredentials("LDAP authentication is disabled and only admin user is allowed")
        
        # 创建会话
        logger.info(f"为用户 {_mask_username(username)} 创建会话")
        await session_manager.create_session(request, response, user)
        
        # 确保用户有个人配置Profile
        from .user_profile import get_user_profile_manager
        profile_manager = get_user_profile_manager()
        
        # 检查用户是否已有Profile，如果没有则创建
        if not os.path.exists(f"user_profiles/{username}_profile.json"):
            logger.info(f"为用户 {_mask_username(username)} 创建默认Profile")
            profile_manager.create_default_profile(username)
        else:
            logger.info(f"用户 {_mask_username(username)} 已有Profile，跳过创建")
        
        # 重置登录尝试次数
        session_manager.reset_login_attempts(client_ip)
        logger.info(f"重置IP {client_ip} 的登录尝试次数")
        
        # 确定跳转URL
        redirect_url = next_url if next_url and next_url.startswith('/') else "/"
        logger.info(f"登录成功，跳转URL: {redirect_url}")
        
        return LoginResponse(
            success=True,
            message="Login successful",
            next_url=redirect_url
        )
        
    except InvalidCredentials as e:
        logger.warning(f"认证失败 - 无效凭据: {_mask_username(username)}, 错误: {e}")
        # 增加登录尝试次数
        session_manager.increment_login_attempts(client_ip)
        logger.info(f"增加IP {client_ip} 的登录尝试次数")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    except Exception as e:
        logger.error(f"认证过程中发生异常: {_mask_username(username)}, 错误: {e}")
        logger.error(f"异常类型: {type(e)}")
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
        
        # 保存到文件
        config_file = "auth_config.json"
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
    if not base_config.ldap_enabled:
        return JSONResponse(status_code=400, content={"ok": False, "message": "LDAP is disabled"})

    # 允许用当前UI中的值临时覆盖（不持久化）
    try:
        from dataclasses import asdict
        override = payload or {}
        cfg_dict = asdict(base_config)
        for key in [
            'ldap_protocol', 'ldap_host', 'ldap_port', 'ldap_bind_dn_template', 'ldap_base_dn',
            'ldap_user_filter', 'ldap_admin_group_enabled', 'ldap_user_group_enabled',
            'ldap_admin_group', 'ldap_user_group', 'ldap_group_base_dn',
            'ldap_tls_cacertfile', 'ldap_tls_verify'
        ]:
            if key in override and override[key] not in (None, ""):
                # 类型处理
                if key == 'ldap_port':
                    try:
                        cfg_dict[key] = int(override[key])
                    except Exception:
                        pass
                elif key in ['ldap_tls_verify', 'ldap_admin_group_enabled', 'ldap_user_group_enabled']:
                    val = override[key]
                    if isinstance(val, str):
                        cfg_dict[key] = val.lower() in ("true", "1", "yes", "on")
                    else:
                        cfg_dict[key] = bool(val)
                else:
                    cfg_dict[key] = override[key]

        # 构造临时配置
        temp_config = AuthConfig(**cfg_dict)

        client = LDAPClient(temp_config)
        user = client.authenticate(username, password)
        
        # 构建详细的响应消息
        message_parts = ["连接成功"]
        
        # 检查组查询状态
        if temp_config.ldap_admin_group_enabled or temp_config.ldap_user_group_enabled:
            message_parts.append("组查询已启用")
            
            # 获取用户的组成员信息
            try:
                import ldap
                conn = client._get_connection()
                user_filter = temp_config.ldap_user_filter.format(username=username)
                result = conn.search_s(
                    temp_config.ldap_base_dn,
                    ldap.SCOPE_SUBTREE,
                    user_filter,
                    ['sAMAccountName', 'displayName', 'mail', 'cn', 'memberOf']
                )
                
                if result:
                    dn, attrs = result[0]
                    groups_info = []
                    
                    # 检查管理员组
                    if temp_config.ldap_admin_group_enabled:
                        is_admin_member = client._check_admin_group_membership(conn, dn, attrs)
                        if is_admin_member:
                            groups_info.append(f"管理员组({temp_config.ldap_admin_group})")
                    
                    # 检查用户组
                    if temp_config.ldap_user_group_enabled:
                        is_user_member = client._check_user_group_membership(conn, dn, attrs)
                        if is_user_member:
                            groups_info.append(f"用户组({temp_config.ldap_user_group})")
                    
                    if groups_info:
                        message_parts.append(f"用户属于: {', '.join(groups_info)}")
                    else:
                        message_parts.append("用户不属于任何配置的组")
                        
            except Exception as e:
                logger.warning(f"获取组成员信息时发生错误: {e}")
                message_parts.append("无法获取组成员信息")
        else:
            message_parts.append("组查询未启用，用户将作为普通用户登录")
        
        return JSONResponse(content={
            "ok": True, 
            "message": " | ".join(message_parts),
            "user_role": user.role.value,
            "is_admin": user.is_admin()
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
        "can_access_admin_settings": user.can_access_admin_settings(),
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
    global_config_dict = global_config.get_config_dict()
    
    # 获取LDAP配置（使用本模块中的全局配置访问器）
    auth_config = get_auth_config()
    auth_config_dict = auth_config.__dict__
    
    # 合并配置：用户配置 + 全局配置 + LDAP配置
    config_dict = {**global_config_dict, **user_config, **auth_config_dict}
    
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
            'translator_convert_engin', 'translator_mineru_model_version', 
            'translator_formula_ocr', 'translator_code_ocr', 'translator_skip_translate',
            'platform_urls', 'platform_models',
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
        # 脱敏API密钥
        if 'platform_api_keys' in config_dict:
            masked_keys = {}
            for platform, key in config_dict['platform_api_keys'].items():
                if key:
                    masked_keys[platform] = key[:8] + "***" if len(key) > 8 else "***"
                else:
                    masked_keys[platform] = ""
            config_dict['platform_api_keys'] = masked_keys
        
        
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
    
    # 获取完整的API密钥（不脱敏）
    api_keys = secrets_manager.get_api_keys()
    mineru_token = secrets_manager.get_mineru_token()
    
    return {
        "platform_api_keys": api_keys,
        "translator_mineru_token": mineru_token or ""
    }


@auth_router.post("/app-config")
async def update_app_config_api(
    request: Request,
    user: User = Depends(get_current_user)
):
    """更新应用配置（需要管理员权限）"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")
    
    try:
        config_data = await request.json()
        app_config = get_app_config()
        
        # 移除任何来自前端的 platform_api_keys（敏感信息不保存在应用配置）
        if 'platform_api_keys' in config_data:
            del config_data['platform_api_keys']
        
        
        # 处理Mineru Token（保存到敏感配置）
        if 'translator_mineru_token' in config_data:
            token = config_data['translator_mineru_token']
            if token and not token.endswith('***'):
                from ..config.secrets_manager import get_secrets_manager
                secrets_manager = get_secrets_manager()
                secrets_manager.update_mineru_token(token)
            del config_data['translator_mineru_token']
        
        # 更新其他配置
        app_config.update_from_dict(config_data)
        
        # 保存配置
        if save_app_config():
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
            'translator_convert_engin', 'translator_mineru_model_version',
            'translator_formula_ocr', 'translator_code_ocr', 'translator_skip_translate',
            'platform_urls', 'platform_models', 'active_task_ids',
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
                        if api_key and api_key.strip():  # 只保存非空密钥
                            if secrets_manager.update_api_key(platform, api_key):
                                updated_any = True
                    # 同步刷新内存中的全局配置，确保刷新页面即可看到最新脱敏密钥
                    if updated_any:
                        try:
                            from ..config.global_config import get_global_config
                            global_config = get_global_config()
                            for platform, api_key in value.items():
                                if api_key and api_key.strip():
                                    global_config.update_platform_api_key(platform, api_key)
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
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown global setting key: {key}")
            
            # 保存全局配置
            if save_global_config():
                logger.info(f"全局设置项 {key} 已由用户 {_mask_username(user.username)} 更新")
                return {"success": True, "message": f"Global setting {key} updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to save global configuration")
        
        else:
            # 更新用户配置（包括按用户维度的模型键）
            if profile_manager.update_user_setting(user.username, key, value):
                logger.info(f"用户设置项 {key} 已由用户 {_mask_username(user.username)} 更新")
                return {"success": True, "message": f"User setting {key} updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to save user configuration")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新设置项失败: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update setting: {str(e)}")


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
