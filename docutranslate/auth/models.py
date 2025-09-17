# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from dataclasses import dataclass
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class UserRole(str, Enum):
    """用户角色枚举"""
    ADMIN = "admin"
    LDAP_ADMIN = "ldap_admin"
    LDAP_GLOSSARY = "ldap_glossary"
    LDAP_USER = "ldap_user"


@dataclass
class User:
    """用户信息"""
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_authenticated: bool = True
    role: UserRole = UserRole.LDAP_USER
    
    def is_admin(self) -> bool:
        """判断是否为管理员"""
        return self.role in [UserRole.ADMIN, UserRole.LDAP_ADMIN]
    
    def is_super_admin(self) -> bool:
        """判断是否为超级管理员"""
        return self.role == UserRole.ADMIN
    
    def can_access_admin_settings(self) -> bool:
        """判断是否可以访问管理员设置"""
        return self.is_admin()
    
    def can_access_glossary_management(self) -> bool:
        """判断是否可以访问术语表管理"""
        return self.role in [UserRole.ADMIN, UserRole.LDAP_ADMIN, UserRole.LDAP_GLOSSARY]
    
    def get_allowed_settings(self) -> List[str]:
        """获取允许访问的设置项"""
        if self.is_admin():
            return [
                "workflow_settings",
                "parsing_settings", 
                "ai_settings",
                "translation_settings",
                "auth_settings",
                "system_settings",
                "glossary_settings"
            ]
        elif self.role == UserRole.LDAP_GLOSSARY:
            # Glossary Group用户可以访问术语表管理
            return [
                "workflow_settings",
                "translation_settings",
                "glossary_settings"
            ]
        else:
            # 普通LDAP用户只能访问基础设置
            return [
                "workflow_settings",
                "translation_settings"
            ]


class LoginRequest(BaseModel):
    """登录请求模型"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")
    next_url: Optional[str] = Field(None, description="登录后跳转的URL")


class LoginResponse(BaseModel):
    """登录响应模型"""
    success: bool = Field(..., description="登录是否成功")
    message: str = Field(..., description="响应消息")
    next_url: Optional[str] = Field(None, description="跳转URL")


class LogoutResponse(BaseModel):
    """登出响应模型"""
    success: bool = Field(..., description="登出是否成功")
    message: str = Field(..., description="响应消息")


class UserInfo(BaseModel):
    """用户信息响应模型"""
    username: str = Field(..., description="用户名")
    display_name: Optional[str] = Field(None, description="显示名称")
    email: Optional[str] = Field(None, description="邮箱")
