# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from dataclasses import dataclass
from typing import Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration"""
    ADMIN = "admin"
    LDAP_ADMIN = "ldap_admin"
    LDAP_GLOSSARY = "ldap_glossary"
    LDAP_USER = "ldap_user"


@dataclass
class User:
    """User information"""
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    is_authenticated: bool = True
    role: UserRole = UserRole.LDAP_USER
    
    def is_admin(self) -> bool:
        """Check if user is administrator"""
        return self.role in [UserRole.ADMIN, UserRole.LDAP_ADMIN]
    
    def is_super_admin(self) -> bool:
        """Check if user is super administrator"""
        return self.role == UserRole.ADMIN
    
    def can_access_admin_settings(self) -> bool:
        """Check if user can access administrator settings"""
        return self.is_admin()
    
    def can_access_glossary_management(self) -> bool:
        """Check if user can access glossary management"""
        return self.role in [UserRole.ADMIN, UserRole.LDAP_ADMIN, UserRole.LDAP_GLOSSARY]
    
    def get_allowed_settings(self) -> List[str]:
        """Get allowed settings items"""
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
            # Glossary Group users can access glossary management
            return [
                "workflow_settings",
                "translation_settings",
                "glossary_settings"
            ]
        else:
            # Regular LDAP users can only access basic settings
            return [
                "workflow_settings",
                "translation_settings"
            ]


class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    next_url: Optional[str] = Field(None, description="URL to redirect after login")


class LoginResponse(BaseModel):
    """Login response model"""
    success: bool = Field(..., description="Whether login is successful")
    message: str = Field(..., description="Response message")
    next_url: Optional[str] = Field(None, description="Redirect URL")


class LogoutResponse(BaseModel):
    """Logout response model"""
    success: bool = Field(..., description="Whether logout is successful")
    message: str = Field(..., description="Response message")


class UserInfo(BaseModel):
    """User information response model"""
    username: str = Field(..., description="Username")
    display_name: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email")
