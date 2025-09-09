# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import shutil
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ProfileManager:
    """配置管理器，用于管理用户配置模板和实际配置"""
    
    def __init__(self, 
                 templates_dir: str = "templates",
                 profiles_dir: str = "../../user_profiles"):
        self.templates_dir = Path(templates_dir)
        self.profiles_dir = Path(profiles_dir)
        
        # 确保目录存在
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
    
    def get_template_path(self, template_name: str = "default") -> Path:
        """获取模板文件路径"""
        return self.templates_dir / f"{template_name}_profile.json"
    
    def get_profile_path(self, username: str) -> Path:
        """获取用户配置文件路径"""
        return self.profiles_dir / f"{username}_profile.json"
    
    def list_templates(self) -> List[str]:
        """列出所有可用的配置模板"""
        templates = []
        if self.templates_dir.exists():
            for file in self.templates_dir.glob("*_profile.json"):
                template_name = file.stem.replace("_profile", "")
                templates.append(template_name)
        return templates
    
    def list_profiles(self) -> List[str]:
        """列出所有用户配置"""
        profiles = []
        if self.profiles_dir.exists():
            for file in self.profiles_dir.glob("*_profile.json"):
                username = file.stem.replace("_profile", "")
                profiles.append(username)
        return profiles
    
    def create_profile_from_template(self, username: str, template_name: str = "default") -> bool:
        """从模板创建用户配置"""
        # 使用统一的默认模板
        
        template_path = self.get_template_path(template_name)
        profile_path = self.get_profile_path(username)
        
        if not template_path.exists():
            logger.error(f"模板文件不存在: {template_path}")
            return False
        
        try:
            # 复制模板文件到用户配置目录
            shutil.copy2(template_path, profile_path)
            logger.info(f"为用户 {username} 从模板 {template_name} 创建了配置")
            return True
        except Exception as e:
            logger.error(f"创建用户配置失败: {e}")
            return False
    
    def delete_profile(self, username: str) -> bool:
        """删除用户配置"""
        profile_path = self.get_profile_path(username)
        
        if not profile_path.exists():
            logger.warning(f"用户配置不存在: {profile_path}")
            return False
        
        try:
            profile_path.unlink()
            logger.info(f"已删除用户 {username} 的配置")
            return True
        except Exception as e:
            logger.error(f"删除用户配置失败: {e}")
            return False
    
    def backup_profile(self, username: str, backup_dir: str = "backups") -> bool:
        """备份用户配置"""
        profile_path = self.get_profile_path(username)
        backup_path = Path(backup_dir)
        backup_path.mkdir(parents=True, exist_ok=True)
        
        if not profile_path.exists():
            logger.warning(f"用户配置不存在: {profile_path}")
            return False
        
        try:
            backup_file = backup_path / f"{username}_profile_backup.json"
            shutil.copy2(profile_path, backup_file)
            logger.info(f"已备份用户 {username} 的配置到 {backup_file}")
            return True
        except Exception as e:
            logger.error(f"备份用户配置失败: {e}")
            return False
    
    def restore_profile(self, username: str, backup_dir: str = "backups") -> bool:
        """从备份恢复用户配置"""
        backup_path = Path(backup_dir) / f"{username}_profile_backup.json"
        profile_path = self.get_profile_path(username)
        
        if not backup_path.exists():
            logger.error(f"备份文件不存在: {backup_path}")
            return False
        
        try:
            shutil.copy2(backup_path, profile_path)
            logger.info(f"已从备份恢复用户 {username} 的配置")
            return True
        except Exception as e:
            logger.error(f"恢复用户配置失败: {e}")
            return False
    
    def get_profile_info(self, username: str) -> Dict[str, Any]:
        """获取用户配置信息"""
        profile_path = self.get_profile_path(username)
        
        if not profile_path.exists():
            return {"exists": False}
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 获取文件信息
            stat = profile_path.stat()
            
            return {
                "exists": True,
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "settings_count": len(data),
                "has_created_at": "created_at" in data,
                "has_updated_at": "updated_at" in data
            }
        except Exception as e:
            logger.error(f"获取用户配置信息失败: {e}")
            return {"exists": False, "error": str(e)}
    
    def validate_profile(self, username: str) -> Dict[str, Any]:
        """验证用户配置的完整性"""
        profile_path = self.get_profile_path(username)
        
        if not profile_path.exists():
            return {"valid": False, "error": "配置文件不存在"}
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 检查必需的字段
            required_fields = [
                "ui_language", "translator_last_workflow", "translator_target_language",
                "translator_temperature", "theme"
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in data:
                    missing_fields.append(field)
            
            return {
                "valid": len(missing_fields) == 0,
                "missing_fields": missing_fields,
                "total_fields": len(data)
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}


def main():
    """命令行工具入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description="用户配置管理工具")
    parser.add_argument("action", choices=["list", "create", "delete", "backup", "restore", "info", "validate"],
                       help="操作类型")
    parser.add_argument("--username", help="用户名")
    parser.add_argument("--template", default="default", help="模板名称 (默认: default)")
    parser.add_argument("--backup-dir", default="backups", help="备份目录")
    
    args = parser.parse_args()
    
    manager = ProfileManager()
    
    if args.action == "list":
        print("可用模板:", manager.list_templates())
        print("用户配置:", manager.list_profiles())
    
    elif args.action == "create":
        if not args.username:
            print("错误: 需要指定用户名")
            return
        success = manager.create_profile_from_template(args.username, args.template)
        print(f"创建配置: {'成功' if success else '失败'}")
    
    elif args.action == "delete":
        if not args.username:
            print("错误: 需要指定用户名")
            return
        success = manager.delete_profile(args.username)
        print(f"删除配置: {'成功' if success else '失败'}")
    
    elif args.action == "backup":
        if not args.username:
            print("错误: 需要指定用户名")
            return
        success = manager.backup_profile(args.username, args.backup_dir)
        print(f"备份配置: {'成功' if success else '失败'}")
    
    elif args.action == "restore":
        if not args.username:
            print("错误: 需要指定用户名")
            return
        success = manager.restore_profile(args.username, args.backup_dir)
        print(f"恢复配置: {'成功' if success else '失败'}")
    
    elif args.action == "info":
        if not args.username:
            print("错误: 需要指定用户名")
            return
        info = manager.get_profile_info(args.username)
        print(json.dumps(info, indent=2, ensure_ascii=False))
    
    elif args.action == "validate":
        if not args.username:
            print("错误: 需要指定用户名")
            return
        result = manager.validate_profile(args.username)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
