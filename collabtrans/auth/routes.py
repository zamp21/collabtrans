# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from fastapi import APIRouter, Request, Response, HTTPException, Form, Depends, UploadFile, File, Body
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
from .local_users import get_local_user_store, LocalUserRole

# Create authentication-specific logger
logger = logging.getLogger(__name__)

# Username masking: keep first and last characters, replace middle with ×
def _mask_username(name: str) -> str:
    try:
        if not name:
            return ""
        if len(name) <= 2:
            return name[0] + ("×" if len(name) == 2 else "")
        return name[0] + ("×" * (len(name) - 2)) + name[-1]
    except Exception:
        return "***"

# Create router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])

# Create compatibility router without prefix
auth_compat_router = APIRouter(tags=["Authentication"])

# Template directory: use resource path resolution, compatible with development and PyInstaller
from ..utils.resource_utils import resource_path
templates = Jinja2Templates(directory=str(resource_path("template")))

# Global variables (should be injected via dependency injection in actual applications)
_auth_config: Optional[AuthConfig] = None
_session_manager: Optional[AuthSessionManager] = None
_ldap_client: Optional[LDAPClient] = None


def init_auth(config: AuthConfig):
    """Initialize authentication module"""
    global _auth_config, _session_manager, _ldap_client
    _auth_config = config
    _session_manager = AuthSessionManager(config)
    if config.ldap_enabled:
        _ldap_client = LDAPClient(config)


def get_auth_config() -> AuthConfig:
    """Get authentication configuration"""
    if _auth_config is None:
        raise HTTPException(status_code=500, detail="Authentication not initialized")
    return _auth_config


def get_session_manager() -> AuthSessionManager:
    """Get session manager"""
    if _session_manager is None:
        raise HTTPException(status_code=500, detail="Session manager not initialized")
    return _session_manager


def get_ldap_client() -> Optional[LDAPClient]:
    """Get LDAP client"""
    return _ldap_client


def _refresh_ldap_client_if_endpoint_changed(old_cfg: "AuthConfig", new_cfg: "AuthConfig") -> None:
    """Safely rebuild LDAP client when LDAP endpoint-related configuration changes."""
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
            # Only rebuild when LDAP is enabled
            if new_cfg.ldap_enabled:
                _ldap_client = LDAPClient(new_cfg)
                logger.info("[LDAP] Endpoint changed, LDAP client rebuilt")
            else:
                _ldap_client = None
                logger.info("[LDAP] LDAP disabled, client released")
    except Exception as e:
        logger.warning(f"[LDAP] Exception while checking/rebuilding client: {e}")


async def get_current_user(request: Request) -> Optional[User]:
    """Get current user"""
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
            # LDAP disabled: support local users (except super admin handled above)
            from .local_users import get_local_user_store, LocalUserRole
            logger.info("Using local user authentication (LDAP disabled)")
            store = get_local_user_store()
            ok, lu = store.verify_credentials(username, password)
            if not ok or lu is None:
                logger.warning(f"Local user authentication failed: {_mask_username(username)}")
                raise InvalidCredentials("Invalid username or password")
            # Map local role to system UserRole
            mapped_role = (
                UserRole.ADMIN if lu.role == LocalUserRole.ADMIN else
                UserRole.LDAP_GLOSSARY if lu.role == LocalUserRole.APP_ADMIN else
                UserRole.LDAP_USER
            )
            user = User(
                username=lu.username,
                display_name=lu.display_name or lu.username,
                email=lu.email,
                is_authenticated=True,
                role=mapped_role
            )
            logger.info(f"Local user authenticated, role mapped: {user.role}")
        
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
        # Increment login attempts
        session_manager.increment_login_attempts(client_ip)
        logger.info(f"Incremented login attempts for IP {client_ip}")
        raise HTTPException(status_code=401, detail="Invalid username or password")
    except Exception as e:
        logger.error(f"Exception during authentication: {_mask_username(username)}, error: {e}")
        logger.error(f"Exception type: {type(e)}")
        # Increment login attempts
        session_manager.increment_login_attempts(client_ip)
        logger.info(f"Increased login attempts for IP {client_ip}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@auth_router.post("/logout", response_class=JSONResponse)
async def logout(request: Request, response: Response):
    """Handle logout request"""
    session_manager = get_session_manager()
    
    await session_manager.destroy_session(request, response)
    
    return LogoutResponse(
        success=True,
        message="Logout successful"
    )


@auth_router.get("/logout", response_class=RedirectResponse)
async def logout_get(request: Request, response: Response):
    """GET logout, redirect to login page"""
    session_manager = get_session_manager()
    
    await session_manager.destroy_session(request, response)
    
    return RedirectResponse(url="/login", status_code=302)


@auth_router.get("/user", response_model=UserInfo)
async def get_user_info(request: Request):
    """Get current user information"""
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
    """Get authentication configuration"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    config = get_auth_config()
    
    # Return configuration but exclude sensitive information like passwords
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
        "default_password": "***",  # Do not return real password
        "session_max_age": config.session_max_age,
        "max_login_attempts": config.max_login_attempts,
        "login_attempt_window": config.login_attempt_window,
    }


@auth_router.post("/config")
async def update_auth_config_api(request: Request, config_data: dict):
    """Update authentication configuration"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
        logger.info(f"Received configuration update request: {config_data}")
    
    try:
        # Get current configuration
        config = get_auth_config()
        
        # Update configuration
        config.update_from_dict(config_data)
        
        # Save to grouped local_config.json
        config_file = "local_config.json"
        if config.save_to_file(config_file):
            logger.info("Configuration saved successfully")
            return {"message": "Configuration updated successfully. Please restart the application to take effect."}
        else:
            logger.error("Configuration save failed")
            raise HTTPException(status_code=500, detail="Failed to save configuration")
            
    except Exception as e:
        logger.error(f"Error occurred while updating configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update configuration: {str(e)}")


@auth_router.post("/test-ldap")
async def test_ldap_connection(request: Request, payload: dict):
    """Test LDAP/LDAPS connection (admin only)
    Input: {"username": "testuser", "password": "***"}
    Execute a simple bind and search using current authentication configuration.
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

    # Allow temporary override with current UI values (not persisted)
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
                # Type handling
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

        
        # Construct temporary configuration, force enable LDAP for testing
        cfg_dict['ldap_enabled'] = True
        temp_config = AuthConfig(**cfg_dict)

        client = LDAPClient(temp_config)
        user = client.authenticate(username, password)
        
        # Build structured debug information (rendered by frontend i18n)
        groups_enabled = bool(temp_config.ldap_admin_group_enabled or temp_config.ldap_glossary_group_enabled)
        groups_codes = []  # ['admin', 'glossary']
        
        # Check group query status
        if groups_enabled:
            
            # Get user's group membership information (unified use of ldap3, avoid mixing with python-ldap API)
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

                    # Check admin group
                    if temp_config.ldap_admin_group_enabled:
                        is_admin_member = client._check_admin_group_membership(conn, user_entry)

                    # Check glossary group
                    if temp_config.ldap_glossary_group_enabled:
                        is_glossary_member = client._check_user_group_membership(conn, user_entry)

                    if is_admin_member:
                        groups_codes.append('admin')
                    if is_glossary_member:
                        groups_codes.append('glossary')

            except Exception as e:
                logger.warning(f"Error occurred while getting group membership information: {e}")
        
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
    """Get user permission information"""
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
    """Get application configuration (login required)"""
    from .user_profile import get_user_profile_manager
    from ..config.global_config import get_global_config
    
    # Get user personal configuration
    profile_manager = get_user_profile_manager()
    user_profile = profile_manager.get_user_profile(user.username)
    user_config = user_profile.get_config_dict()
    
    # Get global configuration
    global_config = get_global_config()
    global_config_dict = global_config.get_config_dict(include_api_keys=False, flatten=True)
    
    # Get LDAP configuration (using global configuration accessor in this module)
    auth_config = get_auth_config()
    auth_config_dict = auth_config.__dict__
    
    # Merge configurations: user config + global config + LDAP config
    config_dict = {**global_config_dict, **user_config, **auth_config_dict}
    
    # Only keep new key names in output (do not handle deprecated old keys)
    
    # Filter sensitive configuration based on user permissions
    if not user.is_admin():
        # Non-admin users, only return basic configuration
        filtered_config = {}
        # Allowed basic settings
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
            # Non-sensitive settings in global configuration
            'ai_platforms', 'translator_settings', 'default_language',
            # User dimension model override
            'translator_platform_models', 'glossary_agent_platform_models',
            # LDAP configuration (non-sensitive part)
            'ldap_enabled', 'ldap_protocol', 'ldap_host', 'ldap_port'
        ]
        for key in allowed_keys:
            if key in config_dict:
                filtered_config[key] = config_dict[key]
        return filtered_config
    else:
        # Admin users, return all configuration but hide sensitive information
        # Mask API keys (from ai_platforms)
        if 'ai_platforms' in config_dict:
            for platform_key, platform_data in config_dict['ai_platforms'].items():
                if isinstance(platform_data, dict) and 'api_key' in platform_data:
                    api_key = platform_data['api_key']
                    if api_key:
                        platform_data['api_key'] = api_key[:8] + "***" if len(api_key) > 8 else "***"
                    else:
                        platform_data['api_key'] = ""
        
        
        # Mask Mineru Token (loaded from sensitive configuration)
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
    """Get complete sensitive configuration (admin only)"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied")
    
    from ..config.secrets_manager import get_secrets_manager
    secrets_manager = get_secrets_manager()
    
    # Get complete API keys and metadata (not masked)
    api_keys_meta = secrets_manager.get_api_keys_meta()
    mineru_meta = secrets_manager.get_mineru_token_meta()
    # Maintain backward compatibility: provide old fields as well
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
        logger.error(f"Certificate upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@auth_router.post("/web/test-https")
async def test_https_available(
    request: Request,
    payload: dict,
    user: User = Depends(get_current_user)
):
    """Test current certificate and HTTPS availability (admin only)
    Logic:
    1) Read passed certificate/private key paths (use global config if not passed)
    2) Verify certificate/private key files exist and are readable
    3) Try to load into SSLContext (equivalent to Uvicorn usage)
    4) Make one HTTPS request to self (verify=False), return status code
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

        # Check if openssl is available (for auto-generation or user troubleshooting)
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

        # 3) Load into SSLContext
        try:
            ctx = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
            # Allow no password
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

        # 4) Self-test: make one HTTPS request to self (disable verification to support self-signed)
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
        logger.error(f"HTTPS test failed: {e}")
        return JSONResponse(status_code=500, content={"ok": False, "message": str(e)})


# === Glossary Management API ===

@auth_router.get("/glossaries")
async def get_glossaries_list(
    user: User = Depends(get_current_user)
):
    """Get glossary list"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    
    # Get global glossaries
    global_glossaries = manager.get_global_glossaries()
    
    # Get user personal glossary
    personal_glossary = manager.get_user_personal_glossary(user.username)
    
    # Get user selection
    user_selection = manager.get_user_selection(user.username)
    
    # Get version information
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
    """Check glossary updates"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    current_versions = manager.get_all_versions()
    
    # Get user's last checked version
    last_check = request.cookies.get('glossaries_last_check', '{}')
    try:
        last_versions = json.loads(last_check)
    except:
        last_versions = {}
    
    # Check if there are updates
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
    """Upload glossary"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    
    try:
        form = await request.form()
        file = form.get("file")
        name = form.get("name", "").strip()
        description = form.get("description", "").strip()
        is_global = form.get("is_global", "false").lower() == "true"
        
        if not file or not name:
            raise HTTPException(status_code=400, detail="File name and glossary name cannot be empty")
        
        # Check permissions
        if is_global and not user.is_admin():
            raise HTTPException(status_code=403, detail="Only administrators can upload global glossaries")
        
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8-sig')
        
        # Parse CSV
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
            raise HTTPException(status_code=400, detail="Glossary cannot be empty")
        
        # Validate glossary
        is_valid, message = manager.validate_glossary_dict(glossary_dict)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Save glossary
        if is_global:
            glossary = manager.create_global_glossary(name, glossary_dict, user.username, description)
            logger.info(f"Administrator {user.username} created global glossary: {name}")
        else:
            # Personal glossary
            success = manager.save_user_personal_glossary(user.username, glossary_dict)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to save personal glossary")
            logger.info(f"User {user.username} updated personal glossary")
        
        return {
            "success": True,
            "message": "Glossary uploaded successfully",
            "item_count": len(glossary_dict)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Glossary upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@auth_router.get("/glossaries/{glossary_id}/download")
async def download_glossary(
    glossary_id: str,
    user: User = Depends(get_current_user)
):
    """Download glossary"""
    from ..glossary.manager import get_glossary_manager
    from fastapi.responses import FileResponse
    
    manager = get_glossary_manager()
    
    # Get glossary content
    glossary_dict = manager.get_glossary_content(glossary_id)
    if not glossary_dict:
        raise HTTPException(status_code=404, detail="Glossary not found")
    
    # Generate temporary CSV file
    import tempfile
    import csv
    
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig')
    writer = csv.writer(temp_file)
    writer.writerow(['src', 'dst'])
    for src, dst in glossary_dict.items():
        writer.writerow([src, dst])
    temp_file.close()
    
    # Determine filename
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
    """Update user glossary selection"""
    from ..glossary.manager import get_glossary_manager
    from ..glossary.models import UserGlossarySelection
    
    manager = get_glossary_manager()
    
    try:
        data = await request.json()
        logger.info(f"[LDAP-API] Received update request: {data}")
        selected_global_glossaries = data.get("selected_global_glossaries", [])
        personal_glossary = data.get("personal_glossary")
        
        # Verify selected global glossaries exist
        global_glossaries = manager.get_global_glossaries()
        valid_global_ids = [g.id for g in global_glossaries]
        
        for glossary_id in selected_global_glossaries:
            if glossary_id not in valid_global_ids:
                raise HTTPException(status_code=400, detail=f"Glossary {glossary_id} not found")
        
        # Verify personal glossary
        if personal_glossary and personal_glossary != f"personal_{user.username}":
            raise HTTPException(status_code=400, detail="Invalid personal glossary ID")
        
        # Save selection
        selection = UserGlossarySelection(
            username=user.username,
            selected_global_glossaries=selected_global_glossaries,
            personal_glossary=personal_glossary
        )
        manager.save_user_selection(selection)
        
        logger.info(f"User {user.username} updated glossary selection")
        
        return {"success": True, "message": "Glossary selection updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update glossary selection: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@auth_router.delete("/glossaries/{glossary_id}")
async def delete_glossary(
    glossary_id: str,
    user: User = Depends(get_current_user)
):
    """Delete glossary"""
    from ..glossary.manager import get_glossary_manager
    
    manager = get_glossary_manager()
    
    # Check permissions
    if glossary_id.startswith('global_'):
        if not user.is_admin():
            raise HTTPException(status_code=403, detail="Only administrators can delete global glossaries")
        
        success = manager.delete_global_glossary(glossary_id)
        if success:
            logger.info(f"Administrator {user.username} deleted global glossary: {glossary_id}")
        else:
            raise HTTPException(status_code=404, detail="Glossary not found")
    else:
        # Personal glossary - users can only delete their own
        if not glossary_id.startswith(f"personal_{user.username}"):
            raise HTTPException(status_code=403, detail="Can only delete own personal glossary")
        
        # Clear personal glossary
        success = manager.save_user_personal_glossary(user.username, {})
        if success:
            logger.info(f"User {user.username} cleared personal glossary")
        else:
            raise HTTPException(status_code=500, detail="Failed to delete personal glossary")
    
    return {"success": True, "message": "Glossary deleted"}


# === Prompt Management API ===

@auth_router.get("/prompts")
async def get_prompts_list(
    user: User = Depends(get_current_user)
):
    """Get prompt list"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # Get global prompts
    global_prompts = manager.get_global_prompts()
    
    # Get user personal prompts
    personal_prompt = manager.get_user_personal_prompt(user.username)
    
    # Get user selection
    user_selection = manager.get_user_selection(user.username)
    
    # Get version information
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
    """Check prompt updates"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        # Get current version information
        current_versions = manager.get_all_versions()
        
        # More complex update checking logic can be added here
        # e.g. checking file modification time, etc.
        
        return {
            "has_updates": False,  # Simplified implementation, always returns no updates
            "current_versions": current_versions
        }
        
    except Exception as e:
        logger.error(f"Failed to check prompt updates: {e}")
        return {
            "has_updates": False,
            "current_versions": {}
        }


@auth_router.post("/prompts/upload")
async def upload_prompt(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Upload prompt"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        form = await request.form()
        file = form.get("file")
        name = form.get("name", "").strip()
        description = form.get("description", "").strip()
        is_global = form.get("is_global", "false").lower() == "true"
        
        if not file or not name:
            raise HTTPException(status_code=400, detail="File name and prompt name cannot be empty")
        
        # Check permissions
        if is_global and not user.is_admin():
            raise HTTPException(status_code=403, detail="Only administrators can upload global prompts")
        
        # Read file content
        content = await file.read()
        content_str = content.decode('utf-8-sig')
        
        # Parse JSON
        import json
        try:
            prompts_dict = json.loads(content_str)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=400, detail=f"JSON format error: {str(e)}")
        
        if not prompts_dict:
            raise HTTPException(status_code=400, detail="Prompts cannot be empty")
        
        # Validate prompts
        is_valid, message = manager.validate_prompt_dict(prompts_dict)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        
        # Save prompts
        if is_global:
            prompt = manager.create_global_prompt(name, prompts_dict, user.username, description)
            logger.info(f"Administrator {user.username} created global prompt: {name}")
        else:
            # Personal prompts
            success = manager.save_user_personal_prompt(user.username, prompts_dict)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to save personal prompt")
            logger.info(f"User {user.username} updated personal prompt")
        
        return {
            "success": True,
            "message": "Prompts uploaded successfully",
            "item_count": len(prompts_dict)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload prompts: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@auth_router.get("/prompts/{prompt_id}/download")
async def download_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user)
):
    """Download prompt"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # Get prompt file
    if prompt_id.startswith('global_'):
        global_prompts = manager.get_global_prompts()
        prompt_file = None
        for p in global_prompts:
            if p.id == prompt_id:
                prompt_file = p
                break
        
        if not prompt_file:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        # Read prompt content
        prompts_dict = manager.storage.load_prompts_from_json(
            manager.storage.global_dir / manager.storage.global_prompts[prompt_id]['file_path']
        )
        
        filename = f"{prompt_file.name}.json"
        
    elif prompt_id.startswith(f"personal_{user.username}"):
        # Personal prompt
        personal_prompt = manager.get_user_personal_prompt(user.username)
        if not personal_prompt:
            raise HTTPException(status_code=404, detail="Personal prompt not found")
        
        prompts_dict = manager.storage.load_prompts_from_json(
            manager.storage.users_dir / f"{user.username}_prompts.json"
        )
        filename = f"{user.username}_personal_prompts.json"
        
    else:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Generate JSON content
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
    """Update user prompt selection"""
    from ..prompts.manager import get_prompt_manager
    from ..prompts.models import UserPromptSelection
    
    manager = get_prompt_manager()
    
    try:
        data = await request.json()
        logger.info(f"[PROMPT-API] Received update request: {data}")
        selected_global_prompts = data.get("selected_global_prompts", [])
        personal_prompt = data.get("personal_prompt")
        
        # Verify selected global prompts exist
        global_prompts = manager.get_global_prompts()
        valid_global_ids = [p.id for p in global_prompts]
        
        for prompt_id in selected_global_prompts:
            if prompt_id not in valid_global_ids:
                raise HTTPException(status_code=400, detail=f"Prompt {prompt_id} not found")
        
        # Verify personal prompt
        if personal_prompt and personal_prompt != f"personal_{user.username}":
            raise HTTPException(status_code=400, detail="Invalid personal prompt ID")
        
        # Save selection
        selection = UserPromptSelection(
            username=user.username,
            selected_global_prompts=selected_global_prompts,
            personal_prompt=personal_prompt
        )
        manager.save_user_selection(selection)
        
        logger.info(f"User {user.username} updated prompt selection")
        
        return {"success": True, "message": "Prompt selection updated"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update prompt selection: {e}")
        raise HTTPException(status_code=500, detail=f"Update failed: {str(e)}")


@auth_router.delete("/prompts/personal")
async def delete_personal_prompt(
    user: User = Depends(get_current_user)
):
    """Delete user personal prompt"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        # Check if personal prompt exists
        personal_prompt = manager.get_user_personal_prompt(user.username)
        if not personal_prompt:
            raise HTTPException(status_code=404, detail="Personal prompt not found")
        
        # Delete personal prompt file
        success = manager.storage.delete_user_personal_prompt(user.username)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete personal prompt")
        
        logger.info(f"User {user.username} deleted personal prompt")
        
        return {"success": True, "message": "Personal prompt deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete personal prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@auth_router.delete("/prompts/{prompt_id}")
async def delete_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user)
):
    """Delete prompt"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # Check permissions
    if prompt_id.startswith('global_'):
        if not user.is_admin():
            raise HTTPException(status_code=403, detail="Only administrators can delete global prompts")
        
        success = manager.delete_global_prompt(prompt_id)
        if success:
            logger.info(f"Administrator {user.username} deleted global prompt: {prompt_id}")
        else:
            raise HTTPException(status_code=404, detail="Prompt not found")
    else:
        # Personal prompt - users can only delete their own
        if not prompt_id.startswith(f"personal_{user.username}"):
            raise HTTPException(status_code=403, detail="Can only delete own personal prompt")
        
        # Clear personal prompt
        success = manager.save_user_personal_prompt(user.username, {})
        if success:
            logger.info(f"User {user.username} cleared personal prompt")
        else:
            raise HTTPException(status_code=500, detail="Failed to delete personal prompt")
    
    return {"success": True, "message": "Prompt deleted"}


@auth_router.get("/prompts/merged")
async def get_merged_prompts(
    user: User = Depends(get_current_user)
):
    """Get user merged prompts"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    merged_prompts = manager.get_merged_prompts(user.username)
    
    return {
        "prompts": merged_prompts,
        "count": len(merged_prompts)
    }


# === Simplified Prompt Management API ===

@auth_router.get("/prompts/simple")
async def get_simple_prompts(
    user: User = Depends(get_current_user)
):
    """Get simplified global prompt list"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    # Get global prompts collection
    global_prompts = manager.get_global_prompts()
    
    # Find global prompt collection named "Simple Prompts"
    simple_prompts_collection = None
    for prompt_file in global_prompts:
        if prompt_file.name == "Simple Prompts":
            simple_prompts_collection = prompt_file
            break
    
    if simple_prompts_collection:
        # Load prompt content
        prompts_dict = manager.storage.load_prompts_from_json(
            Path(simple_prompts_collection.file_path)
        )
        
        # Convert to simplified format
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
    """Add simplified global prompt"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        content = data.get("content", "").strip()
        
        if not name or not content:
            raise HTTPException(status_code=400, detail="Prompt description and content cannot be empty")
        
        # Get global prompts collection
        global_prompts = manager.get_global_prompts()
        
        # Find global prompt collection named "Simple Prompts"
        simple_prompts_collection = None
        for prompt_file in global_prompts:
            if prompt_file.name == "Simple Prompts":
                simple_prompts_collection = prompt_file
                break
        
        if simple_prompts_collection:
            # Load existing prompts
            prompts_dict = manager.storage.load_prompts_from_json(
                Path(simple_prompts_collection.file_path)
            )
        else:
            # Create new global prompt collection
            prompts_dict = {}
            simple_prompts_collection = manager.create_global_prompt(
                name="Simple Prompts",
                prompts_dict={},
                owner=user.username,
                description="Simplified global prompt collection"
            )
        
        # Add new prompt
        prompts_dict[name] = content
        
        # Update global prompt
        success = manager.update_global_prompt(
            simple_prompts_collection.id,
            prompts_dict,
            user.username
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save prompt")
        
        logger.info(f"User {user.username} added global prompt: {name}")
        
        return {"success": True, "message": "Prompt added successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Add failed: {str(e)}")


@auth_router.delete("/prompts/simple/{prompt_id}")
async def delete_simple_prompt(
    prompt_id: str,
    user: User = Depends(get_current_user)
):
    """Delete simplified global prompt"""
    from ..prompts.manager import get_prompt_manager
    
    manager = get_prompt_manager()
    
    try:
        # Parse prompt ID
        if not prompt_id.startswith("global_"):
            raise HTTPException(status_code=400, detail="Invalid prompt ID")
        
        index = int(prompt_id.replace("global_", ""))
        
        # Get global prompts collection
        global_prompts = manager.get_global_prompts()
        
        # Find global prompt collection named "Simple Prompts"
        simple_prompts_collection = None
        for prompt_file in global_prompts:
            if prompt_file.name == "Simple Prompts":
                simple_prompts_collection = prompt_file
                break
        
        if not simple_prompts_collection:
            raise HTTPException(status_code=404, detail="Global prompt collection not found")
        
        # Load prompts
        prompts_dict = manager.storage.load_prompts_from_json(
            Path(simple_prompts_collection.file_path)
        )
        
        # Get prompt name to delete
        prompt_names = list(prompts_dict.keys())
        if index >= len(prompt_names):
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        prompt_name = prompt_names[index]
        
        # Delete prompt
        del prompts_dict[prompt_name]
        
        # Update global prompt
        success = manager.update_global_prompt(
            simple_prompts_collection.id,
            prompts_dict,
            user.username
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to save prompt")
        
        logger.info(f"User {user.username} deleted global prompt: {prompt_name}")
        
        return {"success": True, "message": "Prompt deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete prompt: {e}")
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


@auth_router.post("/app-config")
async def update_app_config_api(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Update application configuration (requires administrator or management group permissions; only super administrator can change default password)"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")
    
    try:
        config_data = await request.json()
        
        # Separate LDAP-related keys from App configuration keys to avoid LDAP keys being mistakenly included in app_config
        ldap_keys = {
            'ldap_enabled','ldap_protocol','ldap_host','ldap_port','ldap_bind_dn_template','ldap_base_dn',
            'ldap_user_filter','ldap_tls_cacertfile','ldap_tls_verify','ldap_admin_group_enabled','ldap_admin_group',
            'ldap_glossary_group_enabled','ldap_glossary_group','ldap_group_base_dn'
        }
        ldap_updates = {k: v for k, v in config_data.items() if k in ldap_keys}
        config_data = {k: v for k, v in config_data.items() if k not in ldap_keys}
        
        # First handle LDAP updates (unified to new keys) and write to auth_config
        if ldap_updates:
            try:
                from .config import get_auth_config as _get_auth_cfg, save_auth_config as _save_auth_cfg
                auth_cfg = _get_auth_cfg()
                # Backup old endpoint-related values before saving
                import copy
                old_for_endpoint = copy.deepcopy(auth_cfg)
                auth_cfg.update_from_dict(ldap_updates)
                if _save_auth_cfg():
                    logger.info(f"[APP-CONFIG] Successfully synchronized LDAP configuration: {list(ldap_updates.keys())}")
                    # Synchronously refresh in-memory instance in this module to ensure subsequent GET reads latest values
                    try:
                        global _auth_config
                        if _auth_config is not None:
                            _auth_config.update_from_dict(ldap_updates)
                            logger.info("[APP-CONFIG] Successfully synchronized _auth_config in module")
                        # Hot reload LDAP client (if endpoint changes)
                        _refresh_ldap_client_if_endpoint_changed(old_for_endpoint, auth_cfg)
                    except Exception as _e:
                        logger.warning(f"[APP-CONFIG] Failed to synchronize in-memory module: {_e}")
                else:
                    logger.warning("[APP-CONFIG] Failed to synchronize LDAP configuration")
            except Exception as _e:
                logger.error(f"[APP-CONFIG] Exception when processing LDAP configuration: {_e}")

        app_config = get_app_config()
        
        # Remove any platform_api_keys from frontend (sensitive information not saved in application configuration)
        if 'platform_api_keys' in config_data:
            del config_data['platform_api_keys']
        
        
        # Handle MinerU Token (save to sensitive configuration) - supports {key, configured}
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
        
        # Prohibit non-super administrators from modifying default password
        if not user.is_super_admin() and 'default_password' in config_data:
            del config_data['default_password']
        
        # Handle Web/HTTPS related fields and write to global configuration
        from ..config.global_config import get_global_config, save_global_config
        global_cfg = get_global_config()

        https_keys = {
            'https_enabled', 'https_force_redirect'
        }

        https_updates = {k: v for k, v in config_data.items() if k in https_keys}

        # Certificate path and private key path stored in global configuration (as regular fields storing path strings)
        if 'https_cert_file' in config_data:
            global_cfg.https_cert_file = config_data['https_cert_file'] or None
        if 'https_key_file' in config_data:
            global_cfg.https_key_file = config_data['https_key_file'] or None
        for k, v in https_updates.items():
            setattr(global_cfg, k, v)

        # If HTTPS is requested to be enabled, perform strong validation before saving (ensure it has passed testing)
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
        
        # Handle default language, write to global configuration root fields
        if 'default_language' in config_data:
            try:
                dl = str(config_data.get('default_language') or '').lower()
                if dl in ('zh', 'en'):
                    setattr(global_cfg, 'default_language', dl)
                else:
                    # Simple fallback: unexpected values default to en
                    setattr(global_cfg, 'default_language', 'en')
            except Exception as _e:
                logger.warning(f"[APP-CONFIG] Failed to update default language: {_e}")
            finally:
                # Avoid writing to user-level App configuration simultaneously
                del config_data['default_language']

        # Update other configurations (user-level App configuration)
        app_config.update_from_dict({k: v for k, v in config_data.items() if k not in https_keys and k not in ['https_cert_file','https_key_file']})
        
        # Save configuration
        # Save HTTPS private key password to sensitive configuration
        from ..config.secrets_manager import get_secrets_manager
        secrets_manager = get_secrets_manager()
        if 'https_key_password' in config_data:
            secrets_manager.update_web_tls_password(config_data.get('https_key_password') or None)

        ok1 = save_app_config()
        ok2 = save_global_config()
        if ok1 and ok2:
            logger.info(f"Application configuration updated by user {_mask_username(user.username)}")
            return {"success": True, "message": "Configuration updated successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        logger.error(f"Failed to update application configuration: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update configuration: {str(e)}")


@auth_router.post("/app-config/setting")
async def update_single_setting(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Update single setting item"""
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

        # Define sensitive configuration keys (only administrators can modify, saved to local_secrets.json)
        sensitive_config_keys = [
            'translator_mineru_token',
            'platform_api_keys',
            'default_password',
            'session_secret_key',
            'redis_password'
        ]
        
        # Define global configuration keys (only administrators can modify)
        global_config_keys = [
            'translator_convert_engine', 'translator_mineru_model_version',
            'translator_formula_ocr', 'translator_code_ocr', 'translator_skip_translate',
            'platform_urls', 'platform_models', 'active_task_ids',
            # Web/HTTPS settings
            'https_enabled', 'https_force_redirect', 'https_cert_file', 'https_key_file',
            # LDAP configuration keys
            'ldap_enabled', 'ldap_protocol', 'ldap_host', 'ldap_port', 'ldap_bind_dn_template',
            'ldap_base_dn', 'ldap_user_filter', 'ldap_tls_cacertfile', 'ldap_tls_verify'
        ]

        # Define user configuration keys (all users can modify)
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
            # User dimension model override dictionary keys
            'translator_platform_models', 'glossary_agent_platform_models'
        ]
        
        # Permission check
        if key in sensitive_config_keys:
            # Sensitive configuration, only administrators can modify
            if not user.is_admin():
                logger.warning(f"LDAP user {_mask_username(user.username)} attempted to modify sensitive configuration: {key}")
                raise HTTPException(status_code=403, detail="Access denied: Only admin can modify sensitive settings")
            # Default password can only be changed by super administrator
            if key == 'default_password' and not user.is_super_admin():
                logger.warning(f"Non-super administrator {_mask_username(user.username)} attempted to modify default password")
                raise HTTPException(status_code=403, detail="Only super admin can change default password")
        elif key in global_config_keys:
            # Global configuration, only administrators can modify
            if not user.is_admin():
                logger.warning(f"LDAP user {_mask_username(user.username)} attempted to modify global configuration: {key}")
                raise HTTPException(status_code=403, detail="Access denied: Only admin can modify global settings")
        elif key in user_config_keys:
            # User configuration, all users can modify
            pass
        else:
            # Unknown configuration key
            logger.warning(f"User {_mask_username(user.username)} attempted to modify unknown configuration: {key}")
            raise HTTPException(status_code=400, detail=f"Unknown setting key: {key}")
        
        # Update based on configuration type
        if key in sensitive_config_keys:
            # Update sensitive configuration (save to local_secrets.json)
            secrets_manager = get_secrets_manager()
            
            if key == 'translator_mineru_token':
                if secrets_manager.update_mineru_token(value):
                    logger.info(f"MinerU token updated by user {_mask_username(user.username)}")
                    return {"success": True, "message": "MinerU token updated successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to save MinerU token")
            
            elif key == 'platform_api_keys':
                # Handle platform API keys dictionary
                if isinstance(value, dict):
                    updated_any = False
                    for platform, api_key in value.items():
                        # Compatibility: value might be {platform: str} or {platform: {key, configured}}
                        configured_flag = None
                        if isinstance(api_key, dict):
                            configured_flag = api_key.get('configured')
                            api_key = api_key.get('key', '')
                        if api_key and str(api_key).strip():  # Only save non-empty keys
                            if secrets_manager.update_api_key(platform, str(api_key), configured_flag):
                                updated_any = True
                    # Synchronously refresh in-memory global configuration to ensure latest masked keys are visible after page refresh
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
                            logger.warning(f"Failed to refresh in-memory global API keys: {_e}")
                    logger.info(f"Platform API keys updated by user {_mask_username(user.username)}")
                    return {"success": True, "message": "Platform API keys updated successfully"}
                else:
                    raise HTTPException(status_code=400, detail="Platform API keys must be a dictionary")
            
            elif key in ['default_password', 'session_secret_key', 'redis_password']:
                if secrets_manager.update_auth_secret(key, value):
                    logger.info(f"Authentication sensitive configuration {key} updated by user {_mask_username(user.username)}")
                    return {"success": True, "message": f"Auth secret {key} updated successfully"}
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to save auth secret {key}")
            
            elif key == 'docling_auth':
                if isinstance(value, dict):
                    if get_secrets_manager().update_docling_auth(value):
                        logger.info(f"Docling authentication updated by user {_mask_username(user.username)}")
                        return {"success": True, "message": "Docling auth updated successfully"}
                    else:
                        raise HTTPException(status_code=500, detail="Failed to save Docling auth")
                else:
                    raise HTTPException(status_code=400, detail="Docling auth must be a dictionary")
            else:
                raise HTTPException(status_code=400, detail=f"Unknown sensitive setting key: {key}")
        
        elif key in global_config_keys:
            # Update global configuration
            if key.startswith('platform_') and key.endswith('_model_id'):
                # Handle platform models
                platform = key.replace('translator_platform_', '').replace('_model_id', '')
                global_config.update_platform_model(platform, value)
            elif key.startswith('glossary_agent_platform_') and key.endswith('_model_id'):
                # Handle glossary platform models
                platform = key.replace('glossary_agent_platform_', '').replace('_model_id', '')
                global_config.update_glossary_platform_model(platform, value)
            elif key.startswith('ldap_'):
                # Handle LDAP configuration
                from .config import get_auth_config, save_auth_config
                auth_config = get_auth_config()
                if hasattr(auth_config, key):
                    setattr(auth_config, key, value)
                    if save_auth_config():
                        logger.info(f"LDAP setting {key} updated by user {_mask_username(user.username)}")
                        return {"success": True, "message": f"LDAP setting {key} updated successfully"}
                    else:
                        raise HTTPException(status_code=500, detail="Failed to save LDAP configuration")
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown LDAP setting key: {key}")
            else:
                # Handle regular global configuration items
                if hasattr(global_config, key):
                    setattr(global_config, key, value)
                elif key in ['translator_convert_engine', 'translator_mineru_model_version', 'translator_formula_ocr', 'translator_code_ocr', 'translator_skip_translate']:
                    # Handle fields in translator_settings
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
            
            # Save global configuration
            if save_global_config():
                logger.info(f"Global setting {key} updated by user {_mask_username(user.username)}")
                return {"success": True, "message": f"Global setting {key} updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to save global configuration")
        
        else:
            # Update user configuration (including user-dimension model keys)
            if profile_manager.update_user_setting(user.username, key, value):
                logger.info(f"User setting {key} updated by user {_mask_username(user.username)}")
                return {"success": True, "message": f"User setting {key} updated successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to save user configuration")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update setting: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update setting: {str(e)}")


# === LDAP Configuration Dedicated Read/Write Interface (Unified Entry Point) ===
@auth_router.get("/ldap-config")
async def get_ldap_config_api(user: User = Depends(get_current_user)):
    """Read LDAP-related configuration (readable after login; sensitive information not returned)"""
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
    """Unified update of LDAP-related configuration (requires administrator or management group permissions)."""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")

    try:
        data = await request.json()

        # Only handle new key names

        # Only extract LDAP-related fields
        allowed = {
            'ldap_enabled', 'ldap_protocol', 'ldap_host', 'ldap_port', 'ldap_bind_dn_template', 'ldap_base_dn',
            'ldap_user_filter', 'ldap_tls_cacertfile', 'ldap_tls_verify', 'ldap_admin_group_enabled', 'ldap_admin_group',
            'ldap_glossary_group_enabled', 'ldap_glossary_group', 'ldap_group_base_dn'
        }
        update_payload = {k: v for k, v in data.items() if k in allowed}

        # Type processing
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

        # Update and save
        from .config import get_auth_config as _get_auth_cfg, save_auth_config as _save_auth_cfg
        auth_cfg = _get_auth_cfg()
        logger.info(f"[LDAP-API] Normalized update fields: {update_payload}")
        auth_cfg.update_from_dict(update_payload)
        saved = _save_auth_cfg()
        # Synchronously update in-memory global configuration in this module to avoid requiring restart
        try:
            local_cfg = get_auth_config()
            local_cfg.update_from_dict(update_payload)
            logger.info("[LDAP-API] Successfully synchronized in-memory configuration")
        except Exception:
            pass
        if saved:
            logger.info(f"LDAP configuration updated by user {_mask_username(user.username)}")
            # Synchronously refresh in-memory instance in this module to avoid reading old values after page refresh
            try:
                global _auth_config
                if _auth_config is not None:
                    _auth_config.update_from_dict(update_payload)
                    logger.info("[LDAP-API] Successfully synchronized _auth_config in module")
            except Exception as _e:
                logger.warning(f"[LDAP-API] Failed to synchronize in-memory configuration: {_e}")
            return {"success": True, "message": "LDAP configuration updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save LDAP configuration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update LDAP configuration: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update LDAP configuration: {str(e)}")


# === Message Configuration Dedicated Read/Write Interface ===
@auth_router.get("/message-config")
async def get_message_config_api():
    """Read message-related configuration (public interface, no authentication required)"""
    from .config import AuthConfig
    config = AuthConfig.get_config()
    return {
        "login_banner": config.login_banner,
        "usage_message": config.usage_message,
    }


@auth_router.post("/message-config")
async def update_message_config_api(request: Request, user: User = Depends(get_current_user)):
    """Update message-related configuration (requires administrator privileges)"""
    if not user.is_admin():
        raise HTTPException(status_code=403, detail="Access denied: Admin privileges required")

    try:
        data = await request.json()

        # Only extract message-related fields
        allowed = {'login_banner', 'usage_message'}
        update_payload = {k: v for k, v in data.items() if k in allowed}

        # Update and save
        from .config import AuthConfig
        auth_cfg = AuthConfig.get_config()
        logger.info(f"[Message-API] Update fields: {update_payload}")
        auth_cfg.update_from_dict(update_payload)
        saved = auth_cfg.save_to_file()
        
        # Synchronously update in-memory global configuration in this module
        try:
            local_cfg = get_auth_config()
            local_cfg.update_from_dict(update_payload)
            logger.info("[Message-API] Successfully synchronized in-memory configuration")
        except Exception:
            pass
            
        if saved:
            logger.info(f"Message configuration updated by user {_mask_username(user.username)}")
            return {"success": True, "message": "Message configuration updated"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save message configuration")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update message configuration: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to update message configuration: {str(e)}")

# Compatibility routes (without /auth prefix)
@auth_compat_router.get("/login")
async def login_page_compat(request: Request, next_url: Optional[str] = None):
    """Compatibility login page (without /auth prefix)"""
    return await login_page(request, next_url)


@auth_compat_router.post("/login")
async def login_compat(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    next_url: Optional[str] = Form(None)
):
    """Compatibility login handling (without /auth prefix)"""
    return await login(request, response, username, password, next_url)


@auth_compat_router.get("/logout")
async def logout_get_compat(request: Request, response: Response):
    """Compatibility logout (without /auth prefix)"""
    return await logout_get(request, response)


@auth_router.post("/test-ai-platform")
async def test_ai_platform(
    request: Request,
    user: User = Depends(get_current_user)
):
    """Test AI platform connection"""
    try:
        data = await request.json()
        platform_type = data.get('platform_type')
        base_url = data.get('base_url')
        model_name = data.get('model_name')
        
        if not platform_type or not base_url or not model_name:
            raise HTTPException(status_code=400, detail="Missing required parameters: platform_type, base_url, model_name")
        
        # Get API key
        from ..config.secrets_manager import get_secrets_manager
        secrets_manager = get_secrets_manager()
        api_keys = secrets_manager.get_api_keys()
        api_key = api_keys.get(platform_type)
        
        if not api_key:
            raise HTTPException(status_code=400, detail=f"No API key found for platform: {platform_type}")
        
        # Build test request based on platform type
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
        
        # Send test request
        async with httpx.AsyncClient(timeout=30.0) as client:
            if platform_type == "anthropic":
                # Anthropic uses different API format
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
                # Google uses different API format
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
                # Standard OpenAI format
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
    """Test MinerU connection"""
    try:
        # Check user permissions
        if not _session_manager:
            raise HTTPException(status_code=401, detail="Session manager not initialized")
        
        user = await _session_manager.get_user(request)
        if not user:
            raise HTTPException(status_code=401, detail="Not logged in or session expired")
        
        # Get MinerU token
        try:
            sm = get_secrets_manager()
            mineru_token = sm.get_mineru_token()
            
            if not mineru_token:
                return {"success": False, "message": "MinerU API Key not configured"}
            
            # Test MinerU API connection
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {mineru_token}'
            }
            
            # Use a simple test request - using PDF file type
            test_data = {
                "files": [
                    {"name": "test.pdf", "is_ocr": True}
                ]
            }
            
            logger.info("MinerU connection test: Starting API connection test")
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    'https://mineru.net/api/v4/file-urls/batch',
                    headers=headers,
                    json=test_data
                )
                
                logger.info(f"MinerU connection test: API response status {response.status_code}")
                if response.status_code != 200:
                    logger.warning(f"MinerU connection test: API request failed, status code {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("code") == 0:
                        return {"success": True, "message": "MinerU connection test successful"}
                    else:
                        error_msg = result.get('message', 'Unknown error')
                        error_code = result.get('code', 'N/A')
                        return {"success": False, "message": f"MinerU API returned error: {error_msg} (Error code: {error_code})"}
                elif response.status_code == 401:
                    return {"success": False, "message": "MinerU API Key invalid or expired"}
                else:
                    try:
                        error_detail = response.text
                        return {"success": False, "message": f"MinerU API request failed: {response.status_code} - {error_detail}"}
                    except:
                        return {"success": False, "message": f"MinerU API request failed: {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"MinerU connection test failed: {e}")
            return {"success": False, "message": f"Connection test failed: {str(e)}"}
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MinerU test connection endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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


def _require_admin(user: Optional[User]):
    if not user or not (user.is_admin() or user.is_super_admin()):
        raise HTTPException(status_code=403, detail="Admin permission required")


@auth_router.get("/local-users", response_class=JSONResponse)
async def list_local_users(current_user: Optional[User] = Depends(get_current_user)):
    """List local users (admin only)."""
    _require_admin(current_user)
    store = get_local_user_store()
    users = store.list_users()
    # Hide password hashes and convert to list format
    safe_users = []
    for user_data in users:
        if isinstance(user_data, dict):
            # If it's already a dict with user info
            safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
            safe_users.append(safe_user)
        else:
            # If it's a username string, get the full user data
            user = store.get_user(user_data)
            if user:
                safe_user = {
                    "username": user.username,
                    "role": user.role.value,
                    "display_name": user.display_name,
                    "email": user.email,
                    "created_at": getattr(user, 'created_at', None),
                    "last_login": getattr(user, 'last_login', None),
                    "is_active": getattr(user, 'is_active', True)
                }
                safe_users.append(safe_user)
    return {"users": safe_users}


@auth_router.post("/local-users", response_class=JSONResponse)
async def create_local_user(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user)
):
    """Create local user (admin only)."""
    _require_admin(current_user)
    payload = await request.json()
    username = payload.get("username")
    password = payload.get("password")
    role = payload.get("role", "user")
    display_name = payload.get("display_name")
    email = payload.get("email")
    if not username or not password:
        raise HTTPException(status_code=400, detail="username and password are required")
    try:
        store = get_local_user_store()
        store.create_user(username, password, LocalUserRole(role), display_name, email)
        return {"ok": True}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@auth_router.put("/local-users/{username}", response_class=JSONResponse)
async def update_local_user(username: str, request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Update local user basic info (admin only)."""
    _require_admin(current_user)
    payload = await request.json()
    role = payload.get("role")
    display_name = payload.get("display_name")
    email = payload.get("email")
    store = get_local_user_store()
    try:
        store.update_user(
            username,
            role=LocalUserRole(role) if role is not None else None,
            display_name=display_name,
            email=email
        )
        return {"ok": True}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@auth_router.post("/local-users/{username}/reset-password", response_class=JSONResponse)
async def reset_local_user_password(username: str, request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Reset local user password (admin only, cannot reset super admin)."""
    _require_admin(current_user)
    payload = await request.json()
    new_password = payload.get("password")
    if not new_password:
        raise HTTPException(status_code=400, detail="password is required")
    # Super admin guard
    auth_cfg = get_auth_config()
    if username == auth_cfg.default_username:
        raise HTTPException(status_code=403, detail="Cannot reset super admin password here")
    store = get_local_user_store()
    try:
        store.reset_password(username, new_password)
        return {"ok": True}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))


@auth_router.delete("/local-users/{username}", response_class=JSONResponse)
async def delete_local_user(username: str, current_user: Optional[User] = Depends(get_current_user)):
    """Delete local user (admin only, cannot delete super admin)."""
    _require_admin(current_user)
    auth_cfg = get_auth_config()
    if username == auth_cfg.default_username:
        raise HTTPException(status_code=403, detail="Cannot delete super admin")
    store = get_local_user_store()
    ok = store.delete_user(username)
    return {"ok": ok}


# Self-service change password for local users
@auth_router.post("/local-users/me/change-password", response_class=JSONResponse)
async def change_own_local_password(request: Request, current_user: Optional[User] = Depends(get_current_user)):
    """Allow authenticated local users to change their own password by providing current password.

    Rules:
    - Only works for users that exist in local user store.
    - Require current password verification against local store.
    - LDAP users (no entry in local store) are not allowed here.
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="not authenticated")

    payload = await request.json()
    current_password = payload.get("current_password")
    new_password = payload.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="current_password and new_password are required")

    store = get_local_user_store()
    # Ensure user exists in local user store
    local_user = store.get_user(current_user.username)
    if not local_user:
        raise HTTPException(status_code=403, detail="not a local user")

    ok, _ = store.verify_credentials(current_user.username, current_password)
    if not ok:
        raise HTTPException(status_code=403, detail="current password incorrect")

    store.reset_password(current_user.username, new_password)
    return {"ok": True}
