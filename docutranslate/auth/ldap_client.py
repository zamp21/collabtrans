# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import ssl
import logging
from typing import Optional, Dict, Any
import ldap
from ldap import LDAPError

from .config import AuthConfig
from .models import User, UserRole

# 创建LDAP专用的日志记录器
logger = logging.getLogger(__name__)


def _mask_username(name: str) -> str:
    """用户名脱敏：保留首尾字符，中间用×"""
    try:
        if not name:
            return ""
        if len(name) <= 2:
            return name[0] + ("×" if len(name) == 2 else "")
        return name[0] + ("×" * (len(name) - 2)) + name[-1]
    except Exception:
        return "***"


class InvalidCredentials(Exception):
    """无效凭据异常"""
    pass


class LDAPClient:
    """LDAP 客户端"""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self._connection: Optional[ldap.ldapobject.LDAPObject] = None
    
    def _get_connection(self) -> ldap.ldapobject.LDAPObject:
        """获取LDAP连接"""
        if self._connection is None:
            logger.info(f"正在初始化LDAP连接到: {self.config.ldap_uri}")
            
            try:
                # 创建LDAP连接
                conn = ldap.initialize(self.config.ldap_uri)
                logger.info(f"LDAP连接对象创建成功")
                
                # 设置TLS选项
                if self.config.ldap_tls_cacertfile:
                    logger.info(f"设置TLS证书文件: {self.config.ldap_tls_cacertfile}")
                    conn.set_option(ldap.OPT_X_TLS_CACERTFILE, self.config.ldap_tls_cacertfile)
                else:
                    # 开发环境忽略证书验证
                    logger.info("未设置TLS证书文件，忽略证书验证")
                    conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
                
                # 设置协议版本
                conn.protocol_version = ldap.VERSION3
                logger.info("设置LDAP协议版本为VERSION3")
                
                # 设置网络超时
                conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)
                logger.info("设置网络超时为10秒")
                
                self._connection = conn
                logger.info("LDAP连接初始化完成")
                
            except Exception as e:
                logger.error(f"LDAP连接初始化失败: {e}")
                raise
        
        return self._connection
    
    def authenticate(self, username: str, password: str) -> User:
        """验证用户凭据"""
        if not self.config.ldap_enabled:
            raise ValueError("LDAP is not enabled")
        
        logger.info(f"开始LDAP认证用户: {_mask_username(username)}")
        logger.info(f"LDAP配置信息:")
        logger.info(f"  - LDAP URI: {self.config.ldap_uri}")
        logger.info(f"  - Bind DN Template: {self.config.ldap_bind_dn_template}")
        logger.info(f"  - Base DN: {self.config.ldap_base_dn}")
        logger.info(f"  - User Filter: {self.config.ldap_user_filter}")
        logger.info(f"  - TLS Cert File: {self.config.ldap_tls_cacertfile}")
        
        try:
            conn = self._get_connection()
            
            # 构建绑定DN
            bind_dn = self.config.ldap_bind_dn_template.format(username=username)
            logger.info(f"构建的绑定DN: {_mask_username(bind_dn)}")
            
            # 尝试绑定
            logger.info("正在尝试LDAP绑定...")
            conn.simple_bind_s(bind_dn, password)
            logger.info("LDAP绑定成功")
            
            # 搜索用户信息
            user_filter = self.config.ldap_user_filter.format(username=username)
            logger.info(f"搜索用户过滤器: {user_filter}")
            logger.info(f"搜索基础DN: {self.config.ldap_base_dn}")
            
            result = conn.search_s(
                self.config.ldap_base_dn,
                ldap.SCOPE_SUBTREE,
                user_filter,
                ['sAMAccountName', 'displayName', 'mail', 'cn']
            )
            
            logger.info(f"搜索返回结果数量: {len(result)}")
            if result:
                logger.info(f"找到用户，DN: {result[0][0]}")
                logger.info(f"用户属性: {list(result[0][1].keys())}")
            
            if not result:
                logger.warning("未找到匹配的用户")
                raise InvalidCredentials("User not found")
            
            # 解析用户信息
            dn, attrs = result[0]
            display_name = None
            email = None
            
            if 'displayName' in attrs:
                display_name = attrs['displayName'][0].decode('utf-8')
                logger.info(f"用户显示名称: {display_name}")
            elif 'cn' in attrs:
                display_name = attrs['cn'][0].decode('utf-8')
                logger.info(f"用户CN: {display_name}")
            
            if 'mail' in attrs:
                email = attrs['mail'][0].decode('utf-8')
                logger.info(f"用户邮箱: {email}")
            
            user = User(
                username=username,
                display_name=display_name,
                email=email,
                is_authenticated=True,
                role=UserRole.LDAP_USER  # LDAP用户设置为普通用户角色
            )
            
            logger.info(f"LDAP认证成功，用户: {_mask_username(username)}")
            return user
            
        except LDAPError as e:
            logger.error(f"LDAP错误: {e}")
            logger.error(f"LDAP错误类型: {type(e)}")
            logger.error(f"LDAP错误详情: {str(e)}")
            
            if "invalidCredentials" in str(e).lower() or "invalid credentials" in str(e).lower():
                logger.warning("LDAP认证失败：无效凭据")
                raise InvalidCredentials("Invalid username or password")
            else:
                logger.error(f"LDAP认证失败：{e}")
                raise Exception(f"LDAP authentication error: {e}")
        except Exception as e:
            logger.error(f"认证过程中发生异常: {e}")
            logger.error(f"异常类型: {type(e)}")
            raise Exception(f"Authentication error: {e}")
    
    def close(self):
        """关闭LDAP连接"""
        if self._connection:
            try:
                self._connection.unbind_s()
            except:
                pass
            self._connection = None
    
    def __del__(self):
        """析构函数，确保连接被关闭"""
        self.close()
