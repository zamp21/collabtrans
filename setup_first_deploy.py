#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CollabTrans 首次部署设置脚本
自动完成首次部署所需的基本配置
"""

import os
import shutil
import json
import secrets
import string
from pathlib import Path


def generate_random_key(length=32):
    """生成随机密钥"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def setup_first_deploy():
    """首次部署设置"""
    print("🚀 CollabTrans 首次部署设置")
    print("=" * 50)
    
    # 1. 创建 local_secrets.json
    local_secrets_path = "local_secrets.json"
    local_secrets_template_path = "local_secrets.json.template"
    
    if not os.path.exists(local_secrets_path) and os.path.exists(local_secrets_template_path):
        try:
            shutil.copy2(local_secrets_template_path, local_secrets_path)
            print("✅ 已创建 local_secrets.json 配置文件")
            
            # 生成随机密钥
            with open(local_secrets_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # 移除模板说明字段，避免进入生产文件
            for k in ['_comment', '_warning']:
                if k in config:
                    config.pop(k, None)
            
            # 生成随机会话密钥
            config['auth_secrets']['session_secret_key'] = generate_random_key(64)
            
            # 设置默认管理员密码
            config['auth_secrets']['default_password'] = "admin123"
            
            with open(local_secrets_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print("✅ 已生成随机会话密钥")
            print("✅ 已设置默认管理员密码: admin123")
            
        except Exception as e:
            print(f"❌ 创建 local_secrets.json 失败: {e}")
    else:
        print("ℹ️  local_secrets.json 已存在，跳过创建")
    
    # 2. 检查并创建必要的目录
    directories = ['logs', 'output', 'certs', 'glossaries', 'user_profiles']
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"✅ 已创建目录: {directory}")
    
    # 3. 检查配置文件
    config_files = ['auth_config.json', 'global_config.json', 'app_config.json']
    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"✅ 配置文件存在: {config_file}")
        else:
            print(f"⚠️  配置文件缺失: {config_file}")
    
    # 4. 显示下一步操作指南
    print("\n" + "=" * 50)
    print("🎉 首次部署设置完成！")
    print("\n📋 下一步操作：")
    print("1. 编辑 local_secrets.json 文件，设置您的API密钥")
    print("2. 安装Redis服务（用于会话管理）")
    print("3. 启动CollabTrans服务")
    print("\n🔧 启动命令：")
    print("   .venv\\Scripts\\python.exe -m collabtrans.cli -i")
    print("\n🌐 访问地址：")
    print("   http://127.0.0.1:8010")
    print("\n👤 默认登录信息：")
    print("   用户名: admin")
    print("   密码: admin123")
    print("\n📚 更多信息请查看 doc/ 目录下的文档")


if __name__ == "__main__":
    setup_first_deploy()
