#!/usr/bin/env python3
"""
初始化本地用户数据
Initialize local user data
"""

import json
import os
import sys
import hashlib
import hmac
import time
from datetime import datetime

def hash_password(password: str, salt: str = None) -> str:
    """哈希密码"""
    if salt is None:
        salt = os.urandom(32).hex()
    
    # 使用HMAC-SHA256进行密码哈希
    password_hash = hmac.new(
        salt.encode('utf-8'),
        password.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"{salt}:{password_hash}"

def initialize_local_users():
    """初始化本地用户数据"""
    template_file = "local_users.json.template"
    output_file = "local_users.json"
    
    if not os.path.exists(template_file):
        print(f"❌ 模板文件不存在: {template_file}")
        return False
    
    # 读取模板
    with open(template_file, 'r', encoding='utf-8') as f:
        template_data = json.load(f)
    
    # 生成时间戳
    timestamp = datetime.now().isoformat()
    
    # 处理用户数据
    for user in template_data["users"]:
        username = user["username"]
        
        # 获取默认密码
        default_password = template_data["metadata"]["default_passwords"].get(username, "password123")
        
        # 生成密码哈希
        password_hash = hash_password(default_password)
        
        # 替换模板变量
        user["password_hash"] = password_hash
        user["created_at"] = timestamp
    
    # 更新元数据
    template_data["metadata"]["created_at"] = timestamp
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 本地用户数据初始化完成: {output_file}")
    print("📋 默认用户账户:")
    for username, password in template_data["metadata"]["default_passwords"].items():
        print(f"  - 用户名: {username}, 密码: {password}")
    
    return True

if __name__ == "__main__":
    if initialize_local_users():
        print("🎉 初始化成功！")
        sys.exit(0)
    else:
        print("❌ 初始化失败！")
        sys.exit(1)
