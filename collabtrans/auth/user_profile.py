# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

# 创建日志记录器
logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """用户个人配置类，存储用户个性化设置"""
    
    # 基础设置
    ui_language: str = "zh"
    
    # 工作流设置
    translator_last_workflow: str = "markdown_based"
    translator_auto_workflow_enabled: bool = True
    
    # 格式特定设置
    translator_txt_insert_mode: str = "replace"
    translator_txt_separator: str = "\\n"
    translator_xlsx_insert_mode: str = "replace"
    translator_xlsx_separator: str = "\\n"
    translator_xlsx_translate_regions: str = ""
    translator_docx_insert_mode: str = "replace"
    translator_docx_separator: str = "\\n"
    translator_srt_insert_mode: str = "replace"
    translator_srt_separator: str = "\\n"
    translator_epub_insert_mode: str = "replace"
    translator_epub_separator: str = "\\n"
    translator_html_insert_mode: str = "replace"
    translator_html_separator: str = " "
    translator_json_paths: str = ""
    
    # AI翻译设置（用户个性化部分）
    translator_thinking_mode: str = "disable"
    translator_target_language: str = "英文"
    translator_custom_language: str = ""
    translator_custom_prompt: str = ""
    translator_platform_type: str = "deepseek"
    translator_temperature: float = 0.3
    translator_max_tokens: int = 4000
    translator_top_p: float = 1.0
    translator_frequency_penalty: float = 0.0
    translator_presence_penalty: float = 0.0
    chunk_size: int = 4000
    concurrent: int = 3
    
    # 术语表设置（用户个性化部分）
    glossary_generate_enable: bool = False
    glossary_agent_config_choice: str = "same"
    glossary_agent_platform_type: str = "deepseek"
    glossary_agent_thinking_mode: str = "disable"
    glossary_agent_temperature: float = 0.3
    glossary_agent_max_tokens: int = 4000
    glossary_agent_top_p: float = 1.0
    glossary_agent_frequency_penalty: float = 0.0
    glossary_agent_presence_penalty: float = 0.0
    glossary_agent_to_lang: str = "英文"
    glossary_agent_chunk_size: int = 4000
    glossary_agent_concurrent: int = 3
    
    # 按用户维度的模型覆盖（按平台类型存储）
    translator_platform_models: Dict[str, str] = field(default_factory=dict)
    glossary_agent_platform_models: Dict[str, str] = field(default_factory=dict)
    
    # 系统设置
    theme: str = "auto"
    
    # 元数据
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def load_from_file(cls, username: str, profile_dir: str = "user_profiles") -> "UserProfile":
        """从文件加载用户配置"""
        try:
            # 确保目录存在
            os.makedirs(profile_dir, exist_ok=True)
            
            profile_file = os.path.join(profile_dir, f"{username}_profile.json")
            
            if os.path.exists(profile_file):
                logger.info(f"正在从文件加载用户配置: {profile_file}")
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # 创建配置实例并更新字段
                    profile = cls()
                    profile.update_from_dict(data)
                    logger.info(f"用户 {username} 配置加载成功")
                    return profile
            else:
                logger.info(f"用户配置文件 {profile_file} 不存在，创建默认配置")
                return cls()
        except Exception as e:
            logger.error(f"加载用户配置失败: {e}")
            return cls()
    
    def save_to_file(self, username: str, profile_dir: str = "user_profiles") -> bool:
        """保存用户配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(profile_dir, exist_ok=True)
            
            profile_file = os.path.join(profile_dir, f"{username}_profile.json")
            
            # 更新修改时间
            self.updated_at = datetime.now().isoformat()
            
            # 保存到文件
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
            
            logger.info(f"用户 {username} 配置已保存到: {profile_file}")
            return True
        except Exception as e:
            logger.error(f"保存用户配置失败: {e}")
            return False
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """从字典更新配置"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_config_dict(self) -> Dict[str, Any]:
        """获取配置字典"""
        return asdict(self)
    
    def update_setting(self, key: str, value: Any) -> bool:
        """更新单个设置，支持动态平台模型键：
        - translator_platform_{type}_model_id
        - glossary_agent_platform_{type}_model_id
        """
        try:
            if hasattr(self, key):
                setattr(self, key, value)
                self.updated_at = datetime.now().isoformat()
                return True
            # 动态键处理：翻译主模块模型
            if key.startswith('translator_platform_') and key.endswith('_model_id'):
                platform = key.replace('translator_platform_', '').replace('_model_id', '')
                if not isinstance(self.translator_platform_models, dict):
                    self.translator_platform_models = {}
                self.translator_platform_models[platform] = value
                self.updated_at = datetime.now().isoformat()
                return True
            # 动态键处理：术语表模型
            if key.startswith('glossary_agent_platform_') and key.endswith('_model_id'):
                platform = key.replace('glossary_agent_platform_', '').replace('_model_id', '')
                if not isinstance(self.glossary_agent_platform_models, dict):
                    self.glossary_agent_platform_models = {}
                self.glossary_agent_platform_models[platform] = value
                self.updated_at = datetime.now().isoformat()
                return True
        except Exception as e:
            logger.error(f"update_setting 动态键处理失败: {e}")
        return False


class UserProfileManager:
    """用户配置管理器"""
    
    def __init__(self, profile_dir: str = "user_profiles"):
        self.profile_dir = profile_dir
        # 确保目录存在
        os.makedirs(profile_dir, exist_ok=True)
    
    def get_user_profile(self, username: str) -> UserProfile:
        """获取用户配置"""
        return UserProfile.load_from_file(username, self.profile_dir)
    
    def save_user_profile(self, username: str, profile: UserProfile) -> bool:
        """保存用户配置"""
        return profile.save_to_file(username, self.profile_dir)
    
    def create_default_profile(self, username: str) -> UserProfile:
        """为用户创建默认配置，使用统一模板"""
        # 使用统一的默认模板
        template_file = "collabtrans/config/templates/default_profile.json"
        
        try:
            # 从模板文件加载配置
            if os.path.exists(template_file):
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                # 创建配置实例并应用模板数据
                profile = UserProfile()
                profile.update_from_dict(template_data)
                
                if self.save_user_profile(username, profile):
                    logger.info(f"为用户 {username} 从统一模板创建了配置")
                return profile
            else:
                # 如果模板文件不存在，使用默认配置
                logger.warning(f"模板文件 {template_file} 不存在，使用默认配置")
                profile = UserProfile()
                if self.save_user_profile(username, profile):
                    logger.info(f"为用户 {username} 创建了默认配置")
                return profile
        except Exception as e:
            logger.error(f"从模板创建用户配置失败: {e}")
            # 降级到默认配置
            profile = UserProfile()
            if self.save_user_profile(username, profile):
                logger.info(f"为用户 {username} 创建了默认配置（降级）")
            return profile
    
    def update_user_setting(self, username: str, key: str, value: Any) -> bool:
        """更新用户单个设置"""
        profile = self.get_user_profile(username)
        if profile.update_setting(key, value):
            return self.save_user_profile(username, profile)
        return False
    
    def get_user_setting(self, username: str, key: str, default_value: Any = None) -> Any:
        """获取用户单个设置"""
        profile = self.get_user_profile(username)
        return getattr(profile, key, default_value)
    
    def list_user_profiles(self) -> List[str]:
        """列出所有用户配置文件名"""
        try:
            if not os.path.exists(self.profile_dir):
                return []
            
            profiles = []
            for file in os.listdir(self.profile_dir):
                if file.endswith('_profile.json'):
                    username = file.replace('_profile.json', '')
                    profiles.append(username)
            return profiles
        except Exception as e:
            logger.error(f"列出用户配置失败: {e}")
            return []


# 全局用户配置管理器实例
_user_profile_manager: Optional[UserProfileManager] = None

def get_user_profile_manager() -> UserProfileManager:
    """获取全局用户配置管理器"""
    global _user_profile_manager
    if _user_profile_manager is None:
        _user_profile_manager = UserProfileManager()
    return _user_profile_manager
