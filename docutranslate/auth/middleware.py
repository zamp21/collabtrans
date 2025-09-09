# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .session_manager import AuthSessionManager
from .config import AuthConfig


class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件"""
    
    def __init__(self, app: ASGIApp, session_manager: AuthSessionManager, config: AuthConfig):
        super().__init__(app)
        self.session_manager = session_manager
        self.config = config
        
        # 不需要认证的路径
        self.exempt_paths = {
            "/login",
            "/logout", 
            "/static",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        }
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        path = request.url.path
        
        # 检查是否为豁免路径
        if self._is_exempt_path(path):
            return await call_next(request)
        
        # 检查用户是否已认证
        if not await self.session_manager.is_authenticated(request):
            # 构建登录URL，包含next参数
            login_url = f"/login?next={path}"
            return RedirectResponse(url=login_url, status_code=302)
        
        # 用户已认证，继续处理请求
        return await call_next(request)
    
    def _is_exempt_path(self, path: str) -> bool:
        """检查路径是否豁免认证"""
        # 精确匹配
        if path in self.exempt_paths:
            return True
        
        # 静态文件路径匹配
        if path.startswith("/static/"):
            return True
        
        # API文档路径匹配
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        
        return False
