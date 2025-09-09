# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import json
import time
import uuid
from typing import Optional, Dict, Any
import redis
from fastapi import Request, Response

from .config import AuthConfig
from .models import User


class AuthSessionManager:
    """会话管理器"""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.redis_client = redis.Redis(
            host=config.redis_host,
            port=config.redis_port,
            db=config.redis_db,
            password=config.redis_password,
            decode_responses=True
        )
    
    def create_session_id(self) -> str:
        """创建会话ID"""
        return str(uuid.uuid4())
    
    def set_session_cookie(self, response: Response, session_id: str):
        """设置会话Cookie"""
        response.set_cookie(
            key=self.config.session_cookie_name,
            value=session_id,
            max_age=self.config.session_max_age,
            httponly=True,
            samesite="lax",
            secure=False  # 开发环境设为False，生产环境应设为True
        )
    
    def get_session_id(self, request: Request) -> Optional[str]:
        """从请求中获取会话ID"""
        return request.cookies.get(self.config.session_cookie_name)
    
    def clear_session_cookie(self, response: Response):
        """清除会话Cookie"""
        response.delete_cookie(
            key=self.config.session_cookie_name,
            httponly=True,
            samesite="lax"
        )
    
    async def create_session(self, request: Request, response: Response, user: User) -> str:
        """创建用户会话"""
        session_id = self.create_session_id()
        
        # 存储用户信息到Redis
        user_data = {
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "is_authenticated": user.is_authenticated,
            "role": user.role.value,  # 保存用户角色
            "created_at": time.time()
        }
        
        self.redis_client.setex(
            f"session:{session_id}",
            self.config.session_max_age,
            json.dumps(user_data)
        )
        
        # 设置Cookie
        self.set_session_cookie(response, session_id)
        
        return session_id
    
    async def get_user(self, request: Request) -> Optional[User]:
        """从会话中获取用户信息"""
        session_id = self.get_session_id(request)
        if not session_id:
            return None
        
        # 从Redis获取用户数据
        user_data_str = self.redis_client.get(f"session:{session_id}")
        if not user_data_str:
            return None
        
        try:
            user_data = json.loads(user_data_str)
            from .models import UserRole
            return User(
                username=user_data["username"],
                display_name=user_data.get("display_name"),
                email=user_data.get("email"),
                is_authenticated=user_data.get("is_authenticated", True),
                role=UserRole(user_data.get("role", "ldap_user"))  # 恢复用户角色，默认为ldap_user
            )
        except (json.JSONDecodeError, KeyError):
            return None
    
    async def destroy_session(self, request: Request, response: Response) -> bool:
        """销毁用户会话"""
        session_id = self.get_session_id(request)
        if not session_id:
            return False
        
        # 从Redis删除会话数据
        self.redis_client.delete(f"session:{session_id}")
        
        # 清除Cookie
        self.clear_session_cookie(response)
        
        return True
    
    async def is_authenticated(self, request: Request) -> bool:
        """检查用户是否已认证"""
        user = await self.get_user(request)
        return user is not None and user.is_authenticated
    
    def get_login_attempts(self, ip_address: str) -> int:
        """获取IP地址的登录尝试次数"""
        key = f"login_attempts:{ip_address}"
        attempts = self.redis_client.get(key)
        return int(attempts) if attempts else 0
    
    def increment_login_attempts(self, ip_address: str) -> int:
        """增加IP地址的登录尝试次数"""
        key = f"login_attempts:{ip_address}"
        attempts = self.redis_client.incr(key)
        self.redis_client.expire(key, self.config.login_attempt_window)
        return attempts
    
    def reset_login_attempts(self, ip_address: str):
        """重置IP地址的登录尝试次数"""
        key = f"login_attempts:{ip_address}"
        self.redis_client.delete(key)
