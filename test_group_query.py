#!/usr/bin/env python3
"""
简化的LDAP组查询测试
直接测试组查询逻辑，验证testuser1是否属于admingrp组
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docutranslate.auth.config import AuthConfig
import ldap

def test_group_query():
    """测试组查询逻辑"""
    print("=== LDAP组查询逻辑测试 ===")
    
    # 加载配置
    config = AuthConfig.load_from_file("auth_config.json")
    print(f"配置信息:")
    print(f"  LDAP URI: {config.get_ldap_uri()}")
    print(f"  组搜索基础DN: {config.ldap_group_base_dn}")
    print(f"  管理员组名: {config.ldap_admin_group}")
    print()
    
    try:
        # 创建LDAP连接
        conn = ldap.initialize(config.get_ldap_uri())
        
        # 设置TLS选项
        if config.ldap_protocol == "ldaps":
            if config.ldap_tls_cacertfile:
                conn.set_option(ldap.OPT_X_TLS_CACERTFILE, config.ldap_tls_cacertfile)
            if config.ldap_tls_verify:
                conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_DEMAND)
            else:
                conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
        
        conn.protocol_version = ldap.VERSION3
        conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)
        
        print("LDAP连接创建成功")
        
        # 搜索管理员组
        admin_group_filter = f"(&(objectClass=group)(cn={config.ldap_admin_group}))"
        print(f"搜索管理员组过滤器: {admin_group_filter}")
        print(f"搜索基础DN: {config.ldap_group_base_dn}")
        
        admin_group_result = conn.search_s(
            config.ldap_group_base_dn,
            ldap.SCOPE_SUBTREE,
            admin_group_filter,
            ['member', 'cn']
        )
        
        print(f"搜索结果数量: {len(admin_group_result)}")
        
        if admin_group_result:
            admin_group_dn, admin_group_attrs = admin_group_result[0]
            print(f"找到管理员组: {admin_group_dn}")
            
            if 'member' in admin_group_attrs:
                admin_members = [member.decode('utf-8') for member in admin_group_attrs['member']]
                print(f"管理员组成员数量: {len(admin_members)}")
                print("管理员组成员:")
                for member in admin_members:
                    print(f"  - {member}")
                    if "testuser1" in member:
                        print(f"    ✓ 找到testuser1!")
            else:
                print("管理员组没有member属性")
        else:
            print("未找到管理员组")
            
        # 搜索用户
        user_filter = f"(sAMAccountName=testuser1)"
        print(f"\n搜索用户过滤器: {user_filter}")
        print(f"搜索基础DN: {config.ldap_base_dn}")
        
        user_result = conn.search_s(
            config.ldap_base_dn,
            ldap.SCOPE_SUBTREE,
            user_filter,
            ['sAMAccountName', 'displayName', 'memberOf']
        )
        
        print(f"用户搜索结果数量: {len(user_result)}")
        
        if user_result:
            user_dn, user_attrs = user_result[0]
            print(f"找到用户: {user_dn}")
            
            if 'memberOf' in user_attrs:
                member_of_groups = [group.decode('utf-8') for group in user_attrs['memberOf']]
                print(f"用户直接成员组:")
                for group in member_of_groups:
                    print(f"  - {group}")
                    if config.ldap_admin_group.lower() in group.lower():
                        print(f"    ✓ 用户是管理员组成员!")
            else:
                print("用户没有memberOf属性")
        
        conn.unbind_s()
        print("\n测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_group_query()
