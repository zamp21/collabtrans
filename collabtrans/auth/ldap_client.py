# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import ssl
import logging
from typing import Optional, Dict, Any
from ldap3 import Server, Connection, ALL, SUBTREE, Tls
from ldap3.core.exceptions import LDAPException, LDAPBindError, LDAPInvalidCredentialsResult

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
    """LDAP 客户端 - 使用ldap3库"""
    
    def __init__(self, config: AuthConfig):
        self.config = config
        self._connection: Optional[Connection] = None
    
    def _get_connection(self) -> Connection:
        """获取LDAP连接"""
        if self._connection is None:
            ldap_uri = self.config.get_ldap_uri()
            logger.info(f"正在初始化LDAP连接到: {ldap_uri}")
            logger.info(f"LDAP协议: {self.config.ldap_protocol}")
            logger.info(f"LDAP主机: {self.config.ldap_host}:{self.config.ldap_port}")
            
            try:
                # 创建LDAP服务器对象
                server = Server(
                    host=self.config.ldap_host,
                    port=self.config.ldap_port,
                    use_ssl=(self.config.ldap_protocol == "ldaps"),
                    get_info=ALL
                )
                logger.info(f"LDAP服务器对象创建成功")
                
                # 创建连接对象
                self._connection = Connection(
                    server,
                    auto_bind=False,
                    receive_timeout=10,
                    auto_referrals=False
                )
                logger.info("LDAP连接对象创建成功")
                
                # 配置TLS选项
                if self.config.ldap_protocol == "ldaps":
                    logger.info("使用LDAPS协议，配置TLS选项")
                    if self.config.ldap_tls_cacertfile:
                        logger.info(f"设置TLS证书文件: {self.config.ldap_tls_cacertfile}")
                        tls = Tls(
                            local_private_key_file=None,
                            local_certificate_file=None,
                            ca_certs_file=self.config.ldap_tls_cacertfile,
                            validate=ssl.CERT_REQUIRED if self.config.ldap_tls_verify else ssl.CERT_NONE
                        )
                        server.tls = tls
                    else:
                        # 使用默认TLS配置
                        tls = Tls(validate=ssl.CERT_REQUIRED if self.config.ldap_tls_verify else ssl.CERT_NONE)
                        server.tls = tls
                else:
                    logger.info("使用LDAP协议，无需TLS配置")
                
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
            if not conn.bind(bind_dn, password):
                logger.warning(f"LDAP绑定失败: {conn.last_error}")
                raise InvalidCredentials("Invalid username or password")
            logger.info("LDAP绑定成功")
            
            # 搜索用户信息
            user_filter = self.config.ldap_user_filter.format(username=username)
            logger.info(f"搜索用户过滤器: {user_filter}")
            logger.info(f"搜索基础DN: {self.config.ldap_base_dn}")
            
            # 执行搜索
            conn.search(
                search_base=self.config.ldap_base_dn,
                search_filter=user_filter,
                search_scope=SUBTREE,
                attributes=['sAMAccountName', 'displayName', 'mail', 'cn', 'memberOf']
            )
            
            logger.info(f"搜索返回结果数量: {len(conn.entries)}")
            if conn.entries:
                logger.info(f"找到用户，DN: {conn.entries[0].entry_dn}")
                logger.info(f"用户属性: {list(conn.entries[0].entry_attributes.keys())}")
            
            if not conn.entries:
                logger.warning("未找到匹配的用户")
                raise InvalidCredentials("User not found")
            
            # 解析用户信息
            user_entry = conn.entries[0]
            display_name = None
            email = None
            
            # 获取显示名称
            if hasattr(user_entry, 'displayName') and user_entry.displayName:
                display_name = str(user_entry.displayName)
                logger.info(f"用户显示名称: {display_name}")
            elif hasattr(user_entry, 'cn') and user_entry.cn:
                display_name = str(user_entry.cn)
                logger.info(f"用户CN: {display_name}")
            
            # 获取邮箱
            if hasattr(user_entry, 'mail') and user_entry.mail:
                email = str(user_entry.mail)
                logger.info(f"用户邮箱: {email}")
            
            # 确定用户角色
            user_role = self._determine_user_role(conn, user_entry)
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
            
        except LDAPInvalidCredentialsResult as e:
            logger.warning("LDAP认证失败：无效凭据")
            raise InvalidCredentials("Invalid username or password")
        except LDAPBindError as e:
            logger.warning(f"LDAP绑定错误: {e}")
            raise InvalidCredentials("Invalid username or password")
        except LDAPException as e:
            logger.error(f"LDAP错误: {e}")
            logger.error(f"LDAP错误类型: {type(e)}")
            logger.error(f"LDAP错误详情: {str(e)}")
            raise Exception(f"LDAP authentication error: {e}")
        except Exception as e:
            logger.error(f"认证过程中发生异常: {e}")
            logger.error(f"异常类型: {type(e)}")
            raise Exception(f"Authentication error: {e}")
    
    def _determine_user_role(self, conn: Connection, user_entry) -> UserRole:
        """根据LDAP组确定用户角色"""
        logger.info("开始确定用户角色...")
        logger.info(f"管理员组查询启用: {self.config.ldap_admin_group_enabled}")
        logger.info(f"术语表组查询启用: {self.config.ldap_glossary_group_enabled}")
        logger.info(f"管理员组: {self.config.ldap_admin_group}")
        logger.info(f"术语表组: {self.config.ldap_glossary_group}")
        logger.info(f"组搜索基础DN: {self.config.ldap_group_base_dn}")
        
        # 如果两个组查询都未启用，直接返回普通用户
        if not self.config.ldap_admin_group_enabled and not self.config.ldap_glossary_group_enabled:
            logger.info("组查询均未启用，用户默认为普通用户")
            return UserRole.LDAP_USER
        
        # 如果启用了用户组（现改为术语表组）查询，仅用于赋予额外权限，不再作为登录前置条件
        if self.config.ldap_glossary_group_enabled:
            logger.info("用户组查询已启用，用于判定术语相关权限，不再阻断登录")
            is_user_group_member = self._check_user_group_membership(conn, user_entry)
            if not is_user_group_member:
                logger.info("用户不在用户组：继续作为普通用户登录")
        
        # 如果启用了管理员组查询，检查用户是否是管理员组成员
        if self.config.ldap_admin_group_enabled:
            logger.info("管理员组查询已启用，检查管理员组成员身份")
            is_admin_group_member = self._check_admin_group_membership(conn, user_entry)
            if is_admin_group_member:
                logger.info("用户是管理员组成员，分配管理员角色")
                return UserRole.LDAP_ADMIN
        
        # 如果启用了用户组（术语组）且用户是成员，则授予术语表管理权限角色
        if self.config.ldap_glossary_group_enabled:
            is_user_group_member = self._check_user_group_membership(conn, user_entry)
            if is_user_group_member:
                logger.info("用户属于术语表组，分配ldap_glossary角色")
                return UserRole.LDAP_GLOSSARY

        # 默认普通用户
        logger.info("用户分配为普通用户角色")
        return UserRole.LDAP_USER
    
    def _check_admin_group_membership(self, conn: Connection, user_entry) -> bool:
        """检查用户是否是管理员组成员"""
        try:
            # 首先检查用户的memberOf属性
            if hasattr(user_entry, 'memberOf') and user_entry.memberOf:
                member_of_groups = [str(group) for group in user_entry.memberOf]
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
                conn.search(
                    search_base=self.config.ldap_group_base_dn,
                    search_filter=admin_group_filter,
                    search_scope=SUBTREE,
                    attributes=['member']
                )
            except Exception as e:
                logger.warning(f"使用组基础DN搜索失败，尝试使用用户基础DN: {e}")
                # 如果遇到错误，尝试使用基础DN
                try:
                    conn.search(
                        search_base=self.config.ldap_base_dn,
                        search_filter=admin_group_filter,
                        search_scope=SUBTREE,
                        attributes=['member']
                    )
                    logger.info("使用基础DN搜索成功")
                except Exception as e2:
                    logger.error(f"使用基础DN搜索也失败: {e2}")
                    raise e
            
            if conn.entries:
                admin_group_entry = conn.entries[0]
                logger.info(f"找到管理员组: {admin_group_entry.entry_dn}")
                
                if hasattr(admin_group_entry, 'member') and admin_group_entry.member:
                    admin_members = [str(member) for member in admin_group_entry.member]
                    logger.info(f"管理员组成员数量: {len(admin_members)}")
                    
                    # 检查用户是否在管理员组中
                    if user_entry.entry_dn in admin_members:
                        logger.info("用户是管理员组成员")
                        return True
            
            logger.info("用户不是管理员组成员")
            return False
            
        except Exception as e:
            logger.error(f"管理员组查询过程中发生错误: {e}")
            logger.warning("管理员组查询失败，假设用户不是管理员组成员")
            return False
    
    def _check_user_group_membership(self, conn: Connection, user_entry) -> bool:
        """检查用户是否是术语表组成员（兼容旧字段）"""
        try:
            # 首先检查用户的memberOf属性
            if hasattr(user_entry, 'memberOf') and user_entry.memberOf:
                member_of_groups = [str(group) for group in user_entry.memberOf]
                logger.info(f"用户直接成员组: {member_of_groups}")
                
                # 检查是否在术语表组中
                for group_dn in member_of_groups:
                    if self.config.ldap_glossary_group.lower() in group_dn.lower():
                        logger.info(f"用户是术语表组成员: {group_dn}")
                        return True
            
            # 如果memberOf属性不存在或没有找到相关组，则通过组搜索来确定
            user_group_filter = f"(&(objectClass=group)(cn={self.config.ldap_glossary_group}))"
            logger.info(f"搜索术语表组过滤器: {user_group_filter}")
            logger.info(f"搜索基础DN: {self.config.ldap_group_base_dn}")
            
            try:
                conn.search(
                    search_base=self.config.ldap_group_base_dn,
                    search_filter=user_group_filter,
                    search_scope=SUBTREE,
                    attributes=['member']
                )
            except Exception as e:
                logger.warning(f"使用组基础DN搜索失败，尝试使用用户基础DN: {e}")
                # 如果遇到错误，尝试使用基础DN
                try:
                    conn.search(
                        search_base=self.config.ldap_base_dn,
                        search_filter=user_group_filter,
                        search_scope=SUBTREE,
                        attributes=['member']
                    )
                    logger.info("使用基础DN搜索成功")
                except Exception as e2:
                    logger.error(f"使用基础DN搜索也失败: {e2}")
                    raise e
            
            if conn.entries:
                user_group_entry = conn.entries[0]
                logger.info(f"找到术语表组: {user_group_entry.entry_dn}")
                
                if hasattr(user_group_entry, 'member') and user_group_entry.member:
                    user_members = [str(member) for member in user_group_entry.member]
                    logger.info(f"术语表组成员数量: {len(user_members)}")
                    
                    # 检查用户是否在术语表组中
                    if user_entry.entry_dn in user_members:
                        logger.info("用户是术语表组成员")
                        return True
            
            logger.info("用户不是术语表组成员")
            return False
            
        except Exception as e:
            logger.error(f"术语表组查询过程中发生错误: {e}")
            logger.warning("术语表组查询失败，假设用户不是术语表组成员")
            return False
    
    def close(self):
        """关闭LDAP连接"""
        if self._connection:
            try:
                self._connection.unbind()
            except:
                pass
            self._connection = None
    
    def __del__(self):
        """析构函数，确保连接被关闭"""
        self.close()