# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import json
import logging
from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

# Create logger
logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    """User personal configuration class, stores user personalized settings"""
    
    # Basic settings
    ui_language: str = "zh"
    
    # Workflow settings
    translator_last_workflow: str = "markdown_based"
    translator_auto_workflow_enabled: bool = True
    
    # Format-specific settings
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
    
    # AI translation settings (user personalization part)
    translator_thinking_mode: str = "disable"
    translator_target_language: str = "English"
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
    
    # Glossary settings (user personalization part)
    glossary_generate_enable: bool = False
    glossary_agent_config_choice: str = "same"
    glossary_agent_platform_type: str = "deepseek"
    glossary_agent_thinking_mode: str = "disable"
    glossary_agent_temperature: float = 0.3
    glossary_agent_max_tokens: int = 4000
    glossary_agent_top_p: float = 1.0
    glossary_agent_frequency_penalty: float = 0.0
    glossary_agent_presence_penalty: float = 0.0
    glossary_agent_to_lang: str = "English"
    glossary_agent_chunk_size: int = 4000
    glossary_agent_concurrent: int = 3
    
    # Model overrides by user dimension (stored by platform type)
    translator_platform_models: Dict[str, str] = field(default_factory=dict)
    glossary_agent_platform_models: Dict[str, str] = field(default_factory=dict)
    
    # System settings
    theme: str = "auto"
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @classmethod
    def load_from_file(cls, username: str, profile_dir: str = "user_profiles") -> "UserProfile":
        """Load user configuration from file"""
        try:
            # Ensure directory exists
            os.makedirs(profile_dir, exist_ok=True)
            
            profile_file = os.path.join(profile_dir, f"{username}_profile.json")
            
            if os.path.exists(profile_file):
                logger.info(f"Loading user configuration from file: {profile_file}")
                with open(profile_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Create configuration instance and update fields
                    profile = cls()
                    profile.update_from_dict(data)
                    logger.info(f"User {username} configuration loaded successfully")
                    return profile
            else:
                logger.info(f"User profile file {profile_file} does not exist, creating default configuration")
                return cls()
        except Exception as e:
            logger.error(f"Failed to load user configuration: {e}")
            return cls()
    
    def save_to_file(self, username: str, profile_dir: str = "user_profiles") -> bool:
        """Save user configuration to file"""
        try:
            # Ensure directory exists
            os.makedirs(profile_dir, exist_ok=True)
            
            profile_file = os.path.join(profile_dir, f"{username}_profile.json")
            
            # Update modification time
            self.updated_at = datetime.now().isoformat()
            
            # Save to file
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
            
            logger.info(f"User {username} configuration saved to: {profile_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save user configuration: {e}")
            return False
    
    def update_from_dict(self, data: Dict[str, Any]) -> None:
        """Update configuration from dictionary"""
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def get_config_dict(self) -> Dict[str, Any]:
        """Get configuration dictionary"""
        return asdict(self)
    
    def update_setting(self, key: str, value: Any) -> bool:
        """Update single setting, supports dynamic platform model keys:
        - translator_platform_{type}_model_id
        - glossary_agent_platform_{type}_model_id
        """
        try:
            if hasattr(self, key):
                setattr(self, key, value)
                self.updated_at = datetime.now().isoformat()
                return True
            # Dynamic key handling: translation main module model
            if key.startswith('translator_platform_') and key.endswith('_model_id'):
                platform = key.replace('translator_platform_', '').replace('_model_id', '')
                if not isinstance(self.translator_platform_models, dict):
                    self.translator_platform_models = {}
                self.translator_platform_models[platform] = value
                self.updated_at = datetime.now().isoformat()
                return True
            # Dynamic key handling: glossary model
            if key.startswith('glossary_agent_platform_') and key.endswith('_model_id'):
                platform = key.replace('glossary_agent_platform_', '').replace('_model_id', '')
                if not isinstance(self.glossary_agent_platform_models, dict):
                    self.glossary_agent_platform_models = {}
                self.glossary_agent_platform_models[platform] = value
                self.updated_at = datetime.now().isoformat()
                return True
        except Exception as e:
            logger.error(f"update_setting dynamic key handling failed: {e}")
        return False


class UserProfileManager:
    """User profile manager"""
    
    def __init__(self, profile_dir: str = "user_profiles"):
        self.profile_dir = profile_dir
        # Ensure directory exists
        os.makedirs(profile_dir, exist_ok=True)
    
    def get_user_profile(self, username: str) -> UserProfile:
        """Get user profile"""
        return UserProfile.load_from_file(username, self.profile_dir)
    
    def save_user_profile(self, username: str, profile: UserProfile) -> bool:
        """Save user profile"""
        return profile.save_to_file(username, self.profile_dir)
    
    def create_default_profile(self, username: str) -> UserProfile:
        """Create default profile for user using unified template"""
        # Use unified default template
        template_file = "collabtrans/config/templates/default_profile.json"
        
        try:
            # Load configuration from template file
            if os.path.exists(template_file):
                with open(template_file, 'r', encoding='utf-8') as f:
                    template_data = json.load(f)
                
                # Create configuration instance and apply template data
                profile = UserProfile()
                profile.update_from_dict(template_data)
                
                if self.save_user_profile(username, profile):
                    logger.info(f"Created configuration for user {username} from unified template")
                return profile
            else:
                # If template file doesn't exist, use default configuration
                logger.warning(f"Template file {template_file} does not exist, using default configuration")
                profile = UserProfile()
                if self.save_user_profile(username, profile):
                    logger.info(f"Created default configuration for user {username}")
                return profile
        except Exception as e:
            logger.error(f"Failed to create user configuration from template: {e}")
            # Fallback to default configuration
            profile = UserProfile()
            if self.save_user_profile(username, profile):
                logger.info(f"Created default configuration for user {username} (fallback)")
            return profile
    
    def update_user_setting(self, username: str, key: str, value: Any) -> bool:
        """Update user single setting"""
        profile = self.get_user_profile(username)
        if profile.update_setting(key, value):
            return self.save_user_profile(username, profile)
        return False
    
    def get_user_setting(self, username: str, key: str, default_value: Any = None) -> Any:
        """Get user single setting"""
        profile = self.get_user_profile(username)
        return getattr(profile, key, default_value)
    
    def list_user_profiles(self) -> List[str]:
        """List all user profile file names"""
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
            logger.error(f"Failed to list user profiles: {e}")
            return []


# Global user profile manager instance
_user_profile_manager: Optional[UserProfileManager] = None

def get_user_profile_manager() -> UserProfileManager:
    """Get global user profile manager"""
    global _user_profile_manager
    if _user_profile_manager is None:
        _user_profile_manager = UserProfileManager()
    return _user_profile_manager
