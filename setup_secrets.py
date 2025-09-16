#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

"""
敏感配置初始化脚本
用于首次部署时设置API密钥等敏感信息
"""

import json
import os
import sys
from pathlib import Path

def main():
    """主函数"""
    print("🔐 DocuTranslate 敏感配置初始化")
    print("=" * 50)
    
    # 检查是否已存在敏感配置文件
    secrets_file = Path("local_secrets.json")
    if secrets_file.exists():
        print(f"⚠️  敏感配置文件 {secrets_file} 已存在")
        response = input("是否要重新配置？(y/N): ").strip().lower()
        if response != 'y':
            print("取消配置")
            return
    
    # 创建配置模板
    template_file = Path("local_secrets.json.template")
    if not template_file.exists():
        print(f"❌ 模板文件 {template_file} 不存在")
        return
    
    print("\n📋 请配置以下敏感信息（按回车跳过）：")
    print("=" * 50)
    
    # 读取模板
    with open(template_file, 'r', encoding='utf-8') as f:
        secrets = json.load(f)
    
    # 配置API密钥
    print("\n🔑 API密钥配置：")
    api_keys = secrets.get("platform_api_keys", {})
    for platform, placeholder in api_keys.items():
        if placeholder.startswith("your-"):
            current_value = input(f"  {platform}: ").strip()
            if current_value:
                api_keys[platform] = current_value
            else:
                api_keys[platform] = ""
    
    # 配置MinerU令牌
    print("\n🔧 MinerU令牌配置：")
    mineru_token = input("  MinerU Token: ").strip()
    if mineru_token:
        secrets["translator_mineru_token"] = mineru_token
    else:
        secrets["translator_mineru_token"] = ""
    
    # 配置认证敏感信息
    print("\n🔐 认证敏感信息配置：")
    auth_secrets = secrets.get("auth_secrets", {})
    
    # 默认密码
    default_password = input("  默认管理员密码 (默认: admin123): ").strip()
    if default_password:
        auth_secrets["default_password"] = default_password
    else:
        auth_secrets["default_password"] = "admin123"
    
    # 会话密钥
    session_secret = input("  会话密钥 (默认: 自动生成): ").strip()
    if session_secret:
        auth_secrets["session_secret_key"] = session_secret
    else:
        import secrets as secrets_module
        auth_secrets["session_secret_key"] = secrets_module.token_urlsafe(32)
        print(f"    自动生成会话密钥: {auth_secrets['session_secret_key'][:8]}...")
    
    # Redis密码
    redis_password = input("  Redis密码 (可选): ").strip()
    if redis_password:
        auth_secrets["redis_password"] = redis_password
    else:
        auth_secrets["redis_password"] = None
    
    # 保存配置
    try:
        with open(secrets_file, 'w', encoding='utf-8') as f:
            json.dump(secrets, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 敏感配置已保存到: {secrets_file}")
        print("🔒 此文件包含敏感信息，请勿提交到git仓库")
        
        # 设置文件权限（仅所有者可读写）
        os.chmod(secrets_file, 0o600)
        print("🔐 已设置文件权限为仅所有者可读写")
        
    except Exception as e:
        print(f"❌ 保存配置失败: {e}")
        return
    
    print("\n📝 配置摘要：")
    print("=" * 50)
    
    # 统计配置的API密钥数量
    configured_keys = sum(1 for key in api_keys.values() if key and key.strip())
    print(f"  API密钥: {configured_keys}/{len(api_keys)} 个已配置")
    
    # 显示其他配置状态
    print(f"  MinerU令牌: {'已配置' if secrets.get('translator_mineru_token') else '未配置'}")
    print(f"  默认密码: {'已配置' if auth_secrets.get('default_password') else '未配置'}")
    print(f"  会话密钥: {'已配置' if auth_secrets.get('session_secret_key') else '未配置'}")
    print(f"  Redis密码: {'已配置' if auth_secrets.get('redis_password') else '未配置'}")
    
    print("\n🚀 配置完成！现在可以启动DocuTranslate服务了")
    print("💡 提示：管理员登录后可以在Web界面中继续配置API密钥")

if __name__ == "__main__":
    main()
