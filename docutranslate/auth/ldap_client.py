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
            ldap_uri = self.config.get_ldap_uri()
            logger.info(f"正在初始化LDAP连接到: {ldap_uri}")
            logger.info(f"LDAP协议: {self.config.ldap_protocol}")
            logger.info(f"LDAP主机: {self.config.ldap_host}:{self.config.ldap_port}")
            
            try:
                # 创建LDAP连接
                conn = ldap.initialize(ldap_uri)
                logger.info(f"LDAP连接对象创建成功")
                
                # 设置TLS选项
                if self.config.ldap_protocol == "ldaps":
                    logger.info("使用LDAPS协议，配置TLS选项")
                    if self.config.ldap_tls_cacertfile:
                        logger.info(f"设置TLS证书文件: {self.config.ldap_tls_cacertfile}")
                        conn.set_option(ldap.OPT_X_TLS_CACERTFILE, self.config.ldap_tls_cacertfile)
                    
                    if self.config.ldap_tls_verify:
                        logger.info("启用TLS证书验证")
                        conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
                    else:
                        logger.info("禁用TLS证书验证")
                        conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
                else:
                    logger.info("使用LDAP协议，无需TLS配置")
                
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
        logger.info(f"  - LDAP URI: {self.config.get_ldap_uri()}")
        logger.info(f"  - 协议: {self.config.ldap_protocol}")
        logger.info(f"  - 主机: {self.config.ldap_host}:{self.config.ldap_port}")
        logger.info(f"  - Bind DN Template: {self.config.ldap_bind_dn_template}")
        logger.info(f"  - Base DN: {self.config.ldap_base_dn}")
        logger.info(f"  - User Filter: {self.config.ldap_user_filter}")
        logger.info(f"  - TLS Cert File: {self.config.ldap_tls_cacertfile}")
        logger.info(f"  - TLS Verify: {self.config.ldap_tls_verify}")
        
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
                ['sAMAccountName', 'displayName', 'mail', 'cn', 'memberOf']
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
            
            # 确定用户角色
            user_role = self._determine_user_role(conn, dn, attrs)
            logger.info(f"用户角色: {user_role}")
            
            user = User(
                username=username,
                display_name=display_name,
                email=email,
                is_authenticated=True,
                role=user_role
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
    
    def _determine_user_role(self, conn: ldap.ldapobject.LDAPObject, user_dn: str, user_attrs: Dict[str, Any]) -> UserRole:
        """根据LDAP组确定用户角色"""
        logger.info("开始确定用户角色...")
        logger.info(f"管理员组查询启用: {self.config.ldap_admin_group_enabled}")
        logger.info(f"用户组查询启用: {self.config.ldap_user_group_enabled}")
        logger.info(f"管理员组: {self.config.ldap_admin_group}")
        logger.info(f"用户组: {self.config.ldap_user_group}")
        logger.info(f"组搜索基础DN: {self.config.ldap_group_base_dn}")
        
        # 如果两个组查询都未启用，直接返回普通用户
        if not self.config.ldap_admin_group_enabled and not self.config.ldap_user_group_enabled:
            logger.info("组查询均未启用，用户默认为普通用户")
            return UserRole.LDAP_USER
        
        # 如果启用了用户组查询，需要验证用户是否在用户组中
        if self.config.ldap_user_group_enabled:
            logger.info("用户组查询已启用，需要验证用户组成员身份")
            is_user_group_member = self._check_user_group_membership(conn, user_dn, user_attrs)
            if not is_user_group_member:
                logger.warning("用户不在用户组中，拒绝登录")
                raise InvalidCredentials("User is not a member of the required user group")
        
        # 如果启用了管理员组查询，检查用户是否是管理员组成员
        if self.config.ldap_admin_group_enabled:
            logger.info("管理员组查询已启用，检查管理员组成员身份")
            is_admin_group_member = self._check_admin_group_membership(conn, user_dn, user_attrs)
            if is_admin_group_member:
                logger.info("用户是管理员组成员，分配管理员角色")
                return UserRole.LDAP_ADMIN
        
        # 如果启用了用户组查询且用户是用户组成员，或者只启用了管理员组查询但用户不是管理员组成员
        logger.info("用户分配为普通用户角色")
        return UserRole.LDAP_USER
    
    def _check_admin_group_membership(self, conn: ldap.ldapobject.LDAPObject, user_dn: str, user_attrs: Dict[str, Any]) -> bool:
        """检查用户是否是管理员组成员"""
        try:
            # 首先检查用户的memberOf属性
            if 'memberOf' in user_attrs:
                member_of_groups = [group.decode('utf-8') for group in user_attrs['memberOf']]
                logger.info(f"用户直接成员组: {member_of_groups}")
                
                # 检查是否在管理员组中
                for group_dn in member_of_groups:
                    if self.config.ldap_admin_group.lower() in group_dn.lower():
                        logger.info(f"用户是管理员组成员: {group_dn}")
                        return True
            
            # 如果memberOf属性不存在或没有找到相关组，则通过组搜索来确定
            admin_group_filter = f"(&(objectClass=group)(cn={self.config.ldap_admin_group}))"
            logger.info(f"搜索管理员组过滤器: {admin_group_filter}")
            logger.info(f"搜索基础DN: {self.config.ldap_group_base_dn}")
            
            try:
                admin_group_result = conn.search_s(
                    self.config.ldap_group_base_dn,
                    ldap.SCOPE_SUBTREE,
                    admin_group_filter,
                    ['member']
                )
            except ldap.REFERRAL as e:
                logger.warning(f"LDAP Referral错误，尝试使用基础DN: {e}")
                # 如果遇到Referral错误，尝试使用基础DN
                try:
                    admin_group_result = conn.search_s(
                        self.config.ldap_base_dn,
                        ldap.SCOPE_SUBTREE,
                        admin_group_filter,
                        ['member']
                    )
                    logger.info("使用基础DN搜索成功")
                except Exception as e2:
                    logger.error(f"使用基础DN搜索也失败: {e2}")
                    raise e
            
            if admin_group_result:
                admin_group_dn, admin_group_attrs = admin_group_result[0]
                logger.info(f"找到管理员组: {admin_group_dn}")
                
                if 'member' in admin_group_attrs:
                    admin_members = [member.decode('utf-8') for member in admin_group_attrs['member']]
                    logger.info(f"管理员组成员数量: {len(admin_members)}")
                    
                    # 检查用户是否在管理员组中
                    if user_dn in admin_members:
                        logger.info("用户是管理员组成员")
                        return True
            
            logger.info("用户不是管理员组成员")
            return False
            
        except Exception as e:
            logger.error(f"管理员组查询过程中发生错误: {e}")
            logger.warning("管理员组查询失败，假设用户不是管理员组成员")
            return False
    
    def _check_user_group_membership(self, conn: ldap.ldapobject.LDAPObject, user_dn: str, user_attrs: Dict[str, Any]) -> bool:
        """检查用户是否是用户组成员"""
        try:
            # 首先检查用户的memberOf属性
            if 'memberOf' in user_attrs:
                member_of_groups = [group.decode('utf-8') for group in user_attrs['memberOf']]
                logger.info(f"用户直接成员组: {member_of_groups}")
                
                # 检查是否在用户组中
                for group_dn in member_of_groups:
                    if self.config.ldap_user_group.lower() in group_dn.lower():
                        logger.info(f"用户是普通用户组成员: {group_dn}")
                        return True
            
            # 如果memberOf属性不存在或没有找到相关组，则通过组搜索来确定
            user_group_filter = f"(&(objectClass=group)(cn={self.config.ldap_user_group}))"
            logger.info(f"搜索普通用户组过滤器: {user_group_filter}")
            logger.info(f"搜索基础DN: {self.config.ldap_group_base_dn}")
            
            try:
                user_group_result = conn.search_s(
                    self.config.ldap_group_base_dn,
                    ldap.SCOPE_SUBTREE,
                    user_group_filter,
                    ['member']
                )
            except ldap.REFERRAL as e:
                logger.warning(f"LDAP Referral错误，尝试使用基础DN: {e}")
                # 如果遇到Referral错误，尝试使用基础DN
                try:
                    user_group_result = conn.search_s(
                        self.config.ldap_base_dn,
                        ldap.SCOPE_SUBTREE,
                        user_group_filter,
                        ['member']
                    )
                    logger.info("使用基础DN搜索成功")
                except Exception as e2:
                    logger.error(f"使用基础DN搜索也失败: {e2}")
                    raise e
            
            if user_group_result:
                user_group_dn, user_group_attrs = user_group_result[0]
                logger.info(f"找到普通用户组: {user_group_dn}")
                
                if 'member' in user_group_attrs:
                    user_members = [member.decode('utf-8') for member in user_group_attrs['member']]
                    logger.info(f"普通用户组成员数量: {len(user_members)}")
                    
                    # 检查用户是否在普通用户组中
                    if user_dn in user_members:
                        logger.info("用户是普通用户组成员")
                        return True
            
            logger.info("用户不是普通用户组成员")
            return False
            
        except Exception as e:
            logger.error(f"用户组查询过程中发生错误: {e}")
            logger.warning("用户组查询失败，假设用户不是用户组成员")
            return False
    
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
