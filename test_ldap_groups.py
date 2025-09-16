#!/usr/bin/env python3
"""
LDAP组查询测试脚本
用于验证testuser1是否属于admingrp组
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docutranslate.auth.config import AuthConfig
from docutranslate.auth.ldap_client import LDAPClient
from docutranslate.auth.models import UserRole

def test_ldap_groups():
    """测试LDAP组查询功能"""
    print("=== LDAP组查询测试 ===")
    
    # 加载配置
    config = AuthConfig.load_from_file("auth_config.json")
    print(f"LDAP配置:")
    print(f"  协议: {config.ldap_protocol}")
    print(f"  主机: {config.ldap_host}:{config.ldap_port}")
    print(f"  基础DN: {config.ldap_base_dn}")
    print(f"  组搜索基础DN: {config.ldap_group_base_dn}")
    print(f"  管理员组查询启用: {config.ldap_admin_group_enabled}")
    print(f"  用户组查询启用: {config.ldap_user_group_enabled}")
    print(f"  管理员组名: {config.ldap_admin_group}")
    print(f"  用户组名: {config.ldap_user_group}")
    print()
    
    # 创建LDAP客户端
    client = LDAPClient(config)
    
    # 测试用户
    test_username = "testuser1"
    test_password = input(f"请输入 {test_username} 的密码: ")
    
    try:
        print(f"正在认证用户: {test_username}")
        user = client.authenticate(test_username, test_password)
        print(f"认证成功!")
        print(f"  用户名: {user.username}")
        print(f"  显示名: {user.display_name}")
        print(f"  邮箱: {user.email}")
        print(f"  角色: {user.role.value}")
        print(f"  是否管理员: {user.is_admin()}")
        print()
        
        # 手动测试组查询
        print("=== 手动组查询测试 ===")
        conn = client._get_connection()
        
        # 搜索用户信息
        user_filter = config.ldap_user_filter.format(username=test_username)
        print(f"搜索用户过滤器: {user_filter}")
        
        result = conn.search_s(
            config.ldap_base_dn,
            ldap.SCOPE_SUBTREE,
            user_filter,
            ['sAMAccountName', 'displayName', 'mail', 'cn', 'memberOf']
        )
        
        if result:
            dn, attrs = result[0]
            print(f"找到用户: {dn}")
            
            # 检查memberOf属性
            if 'memberOf' in attrs:
                member_of_groups = [group.decode('utf-8') for group in attrs['memberOf']]
                print(f"用户直接成员组: {member_of_groups}")
                
                # 检查是否在管理员组中
                for group_dn in member_of_groups:
                    if config.ldap_admin_group.lower() in group_dn.lower():
                        print(f"✓ 用户是管理员组成员: {group_dn}")
                    elif config.ldap_user_group.lower() in group_dn.lower():
                        print(f"✓ 用户是普通用户组成员: {group_dn}")
            else:
                print("用户没有memberOf属性")
            
            # 测试组查询方法
            print("\n=== 测试组查询方法 ===")
            if config.ldap_admin_group_enabled:
                is_admin_member = client._check_admin_group_membership(conn, dn, attrs)
                print(f"管理员组成员检查结果: {is_admin_member}")
            
            if config.ldap_user_group_enabled:
                is_user_member = client._check_user_group_membership(conn, dn, attrs)
                print(f"用户组成员检查结果: {is_user_member}")
        
        else:
            print("未找到用户")
            
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    import ldap
    test_ldap_groups()
