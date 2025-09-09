#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

"""
配置管理脚本
用于管理DocuTranslate的用户配置模板和实际配置
"""

import os
import sys
import json
import shutil
from pathlib import Path

def get_project_root():
    """获取项目根目录"""
    return Path(__file__).parent

def get_template_path():
    """获取模板文件路径"""
    return get_project_root() / "docutranslate" / "config" / "templates" / "default_profile.json"

def get_profiles_dir():
    """获取用户配置目录"""
    return get_project_root() / "user_profiles"

def backup_template():
    """备份当前模板"""
    template_path = get_template_path()
    backup_path = template_path.with_suffix('.json.backup')
    
    if template_path.exists():
        shutil.copy2(template_path, backup_path)
        print(f"✅ 模板已备份到: {backup_path}")
        return True
    else:
        print("❌ 模板文件不存在")
        return False

def restore_template():
    """从备份恢复模板"""
    template_path = get_template_path()
    backup_path = template_path.with_suffix('.json.backup')
    
    if backup_path.exists():
        shutil.copy2(backup_path, template_path)
        print(f"✅ 模板已从备份恢复: {backup_path}")
        return True
    else:
        print("❌ 备份文件不存在")
        return False

def update_template_from_admin():
    """从管理员配置更新模板"""
    template_path = get_template_path()
    admin_profile_path = get_profiles_dir() / "admin_profile.json"
    
    if not admin_profile_path.exists():
        print("❌ 管理员配置文件不存在")
        return False
    
    try:
        # 读取管理员配置
        with open(admin_profile_path, 'r', encoding='utf-8') as f:
            admin_config = json.load(f)
        
        # 移除元数据字段
        metadata_fields = ['created_at', 'updated_at']
        for field in metadata_fields:
            admin_config.pop(field, None)
        
        # 备份当前模板
        backup_template()
        
        # 更新模板
        with open(template_path, 'w', encoding='utf-8') as f:
            json.dump(admin_config, f, indent=2, ensure_ascii=False)
        
        print("✅ 模板已从管理员配置更新")
        return True
    except Exception as e:
        print(f"❌ 更新模板失败: {e}")
        return False

def list_users():
    """列出所有用户配置"""
    profiles_dir = get_profiles_dir()
    
    if not profiles_dir.exists():
        print("❌ 用户配置目录不存在")
        return
    
    profiles = []
    for file in profiles_dir.glob("*_profile.json"):
        username = file.stem.replace("_profile", "")
        profiles.append(username)
    
    if profiles:
        print("📋 用户配置列表:")
        for username in sorted(profiles):
            print(f"  - {username}")
    else:
        print("📋 没有找到用户配置")

def create_user_from_template(username):
    """从模板创建用户配置"""
    template_path = get_template_path()
    user_profile_path = get_profiles_dir() / f"{username}_profile.json"
    
    if not template_path.exists():
        print("❌ 模板文件不存在")
        return False
    
    if user_profile_path.exists():
        print(f"❌ 用户 {username} 的配置已存在")
        return False
    
    try:
        # 确保目录存在
        get_profiles_dir().mkdir(parents=True, exist_ok=True)
        
        # 复制模板文件
        shutil.copy2(template_path, user_profile_path)
        print(f"✅ 用户 {username} 的配置已创建")
        return True
    except Exception as e:
        print(f"❌ 创建用户配置失败: {e}")
        return False

def show_template_info():
    """显示模板信息"""
    template_path = get_template_path()
    
    if not template_path.exists():
        print("❌ 模板文件不存在")
        return
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_data = json.load(f)
        
        print("📋 模板信息:")
        print(f"  文件路径: {template_path}")
        print(f"  配置项数量: {len(template_data)}")
        print(f"  默认语言: {template_data.get('ui_language', 'N/A')}")
        print(f"  默认目标语言: {template_data.get('translator_target_language', 'N/A')}")
        print(f"  默认工作流: {template_data.get('translator_last_workflow', 'N/A')}")
        print(f"  默认主题: {template_data.get('theme', 'N/A')}")
    except Exception as e:
        print(f"❌ 读取模板信息失败: {e}")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("""
🔧 DocuTranslate 配置管理工具

用法: python manage_config.py <命令> [参数]

命令:
  list                    - 列出所有用户配置
  info                    - 显示模板信息
  backup                  - 备份当前模板
  restore                 - 从备份恢复模板
  update-from-admin       - 从管理员配置更新模板
  create-user <username>  - 从模板创建用户配置

示例:
  python manage_config.py list
  python manage_config.py info
  python manage_config.py create-user john
  python manage_config.py update-from-admin
        """)
        return
    
    command = sys.argv[1]
    
    if command == "list":
        list_users()
    elif command == "info":
        show_template_info()
    elif command == "backup":
        backup_template()
    elif command == "restore":
        restore_template()
    elif command == "update-from-admin":
        update_template_from_admin()
    elif command == "create-user":
        if len(sys.argv) < 3:
            print("❌ 请指定用户名")
            return
        username = sys.argv[2]
        create_user_from_template(username)
    else:
        print(f"❌ 未知命令: {command}")

if __name__ == "__main__":
    main()
