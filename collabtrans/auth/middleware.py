# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from fastapi import Request, Response, HTTPException
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .session_manager import AuthSessionManager
from .config import AuthConfig


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware"""
    
    def __init__(self, app: ASGIApp, session_manager: AuthSessionManager, config: AuthConfig):
        super().__init__(app)
        self.session_manager = session_manager
        self.config = config
        
        # Paths that don't require authentication
        self.exempt_paths = {
            "/login",
            "/logout", 
            "/static",
            "/i18n",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        }
        
        # API paths that don't require authentication (GET requests only)
        self.exempt_api_paths = {
            "/auth/message-config"
        }
    
    async def dispatch(self, request: Request, call_next):
        """Handle request"""
        path = request.url.path
        method = request.method
        
        # Check if it's an exempt path
        if self._is_exempt_path(path):
            return await call_next(request)
        
        # Check if it's an exempt API path (GET requests only)
        if self._is_exempt_api_path(path, method):
            return await call_next(request)
        
        # Check if user is authenticated
        if not await self.session_manager.is_authenticated(request):
            # Build login URL with next parameter
            login_url = f"/login?next={path}"
            return RedirectResponse(url=login_url, status_code=302)
        
        # User is authenticated, continue processing request
        return await call_next(request)
    
    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from authentication"""
        # Exact match
        if path in self.exempt_paths:
            return True
        
        # Static file path matching
        if path.startswith("/static/") or path.startswith("/i18n/"):
            return True
        
        # API documentation path matching
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True
        
        return False
    
    def _is_exempt_api_path(self, path: str, method: str) -> bool:
        """Check if API path is exempt from authentication (GET requests only)"""
        if method.upper() == "GET" and path in self.exempt_api_paths:
            return True
        return False
