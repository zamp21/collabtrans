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
        "ldap_uri": config.ldap_uri,
        "ldap_bind_dn_template": config.ldap_bind_dn_template,
        "ldap_base_dn": config.ldap_base_dn,
        "ldap_user_filter": config.ldap_user_filter,
        "ldap_tls_cacertfile": config.ldap_tls_cacertfile,
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
    
    # 合并配置：用户配置 + 全局配置
    config_dict = {**global_config_dict, **user_config}
    
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
            'translator_platform_models', 'glossary_agent_platform_models'
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
        
        
        # 脱敏Mineru Token
        if config_dict.get('translator_mineru_token'):
            config_dict['translator_mineru_token'] = config_dict['translator_mineru_token'][:8] + "***" if len(config_dict['translator_mineru_token']) > 8 else "***"
        
        return config_dict


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
        
        # 防止覆盖脱敏的API密钥
        if 'platform_api_keys' in config_data:
            for platform, key in config_data['platform_api_keys'].items():
                if key and not key.endswith('***'):
                    app_config.update_platform_api_key(platform, key)
            del config_data['platform_api_keys']
        
        
        # 防止覆盖脱敏的Mineru Token
        if 'translator_mineru_token' in config_data:
            if config_data['translator_mineru_token'] and not config_data['translator_mineru_token'].endswith('***'):
                app_config.translator_mineru_token = config_data['translator_mineru_token']
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
        
        profile_manager = get_user_profile_manager()
        global_config = get_global_config()

        # 定义全局配置键（只有管理员可以修改）
        global_config_keys = [
            'translator_convert_engin', 'translator_mineru_token', 'translator_mineru_model_version',
            'translator_formula_ocr', 'translator_code_ocr', 'translator_skip_translate',
            'platform_urls', 'platform_api_keys', 'platform_models', 'active_task_ids'
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
        if key in global_config_keys:
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
        if key in global_config_keys:
            # 更新全局配置
            if key.startswith('platform_') and key.endswith('_apikey'):
                # 处理平台API密钥
                platform = key.replace('translator_platform_', '').replace('_apikey', '')
                global_config.update_platform_api_key(platform, value)
            elif key.startswith('platform_') and key.endswith('_model_id'):
                # 处理平台模型
                platform = key.replace('translator_platform_', '').replace('_model_id', '')
                global_config.update_platform_model(platform, value)
            elif key.startswith('glossary_agent_platform_') and key.endswith('_apikey'):
                # 处理术语表平台API密钥
                platform = key.replace('glossary_agent_platform_', '').replace('_apikey', '')
                global_config.update_glossary_platform_api_key(platform, value)
            elif key.startswith('glossary_agent_platform_') and key.endswith('_model_id'):
                # 处理术语表平台模型
                platform = key.replace('glossary_agent_platform_', '').replace('_model_id', '')
                global_config.update_glossary_platform_model(platform, value)
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
