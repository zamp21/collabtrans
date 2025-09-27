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
from ..utils.redis_manager import get_redis_client


class AuthSessionManager:
    """会话管理器"""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self.redis_client = None
        self._init_redis_client()
    
    def _init_redis_client(self):
        """初始化Redis客户端"""
        try:
            # 首先尝试使用本地Redis管理器
            self.redis_client = get_redis_client()
            if self.redis_client:
                print("✅ Using local Redis service for session management")
                return
        except Exception as e:
            print(f"⚠️  Local Redis startup failed: {e}")
        
        # 如果本地Redis不可用，尝试连接外部Redis
        try:
            self.redis_client = redis.Redis(
                host=self.config.redis_host,
                port=self.config.redis_port,
                db=self.config.redis_db,
                password=self.config.redis_password,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2
            )
            # 测试连接
            self.redis_client.ping()
            print("✅ Using external Redis service for session management")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            print("📝 Session management will be unavailable, please check Redis service")
            self.redis_client = None
    
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
        
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"session:{session_id}",
                    self.config.session_max_age,
                    json.dumps(user_data)
                )
            except Exception as e:
                print(f"⚠️  Failed to store session to Redis: {e}")
        
        # 设置Cookie
        self.set_session_cookie(response, session_id)
        
        return session_id
    
    async def get_user(self, request: Request) -> Optional[User]:
        """从会话中获取用户信息"""
        session_id = self.get_session_id(request)
        if not session_id:
            return None
        
        if not self.redis_client:
            return None
        
        try:
            # 从Redis获取用户数据
            user_data_str = self.redis_client.get(f"session:{session_id}")
            if not user_data_str:
                return None
            
            user_data = json.loads(user_data_str)
            from .models import UserRole
            return User(
                username=user_data["username"],
                display_name=user_data.get("display_name"),
                email=user_data.get("email"),
                is_authenticated=user_data.get("is_authenticated", True),
                role=UserRole(user_data.get("role", "ldap_user"))  # 恢复用户角色，默认为ldap_user
            )
        except (json.JSONDecodeError, KeyError, Exception) as e:
            print(f"⚠️  Failed to get user session: {e}")
            return None
    
    async def destroy_session(self, request: Request, response: Response) -> bool:
        """销毁用户会话"""
        session_id = self.get_session_id(request)
        if not session_id:
            return False
        
        # 从Redis删除会话数据
        if self.redis_client:
            try:
                self.redis_client.delete(f"session:{session_id}")
            except Exception as e:
                print(f"⚠️  Failed to delete session: {e}")
        
        # 清除Cookie
        self.clear_session_cookie(response)
        
        return True
    
    async def is_authenticated(self, request: Request) -> bool:
        """检查用户是否已认证"""
        user = await self.get_user(request)
        return user is not None and user.is_authenticated
    
    def get_login_attempts(self, ip_address: str) -> int:
        """获取IP地址的登录尝试次数"""
        if not self.redis_client:
            return 0
        
        try:
            key = f"login_attempts:{ip_address}"
            attempts = self.redis_client.get(key)
            return int(attempts) if attempts else 0
        except Exception as e:
            print(f"⚠️  Failed to get login attempt count: {e}")
            return 0
    
    def increment_login_attempts(self, ip_address: str) -> int:
        """增加IP地址的登录尝试次数"""
        if not self.redis_client:
            return 1
        
        try:
            key = f"login_attempts:{ip_address}"
            attempts = self.redis_client.incr(key)
            self.redis_client.expire(key, self.config.login_attempt_window)
            return attempts
        except Exception as e:
            print(f"⚠️  Failed to increment login attempt count: {e}")
            return 1
    
    def reset_login_attempts(self, ip_address: str):
        """重置IP地址的登录尝试次数"""
        if not self.redis_client:
            return
        
        try:
            key = f"login_attempts:{ip_address}"
            self.redis_client.delete(key)
        except Exception as e:
            print(f"⚠️  Failed to reset login attempt count: {e}")
