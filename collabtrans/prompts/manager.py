# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import PromptFile, PromptItem, UserPromptSelection
from .storage import get_prompt_storage

logger = logging.getLogger(__name__)


class PromptManager:
    """提示词管理器"""
    
    def __init__(self):
        self.storage = get_prompt_storage()
    
    def get_global_prompts(self) -> List[PromptFile]:
        """获取全局提示词列表"""
        return self.storage.get_global_prompts()
    
    def get_user_personal_prompt(self, username: str) -> Optional[PromptFile]:
        """获取用户个人提示词"""
        return self.storage.get_user_personal_prompt(username)
    
    def get_user_selection(self, username: str) -> UserPromptSelection:
        """获取用户提示词选择"""
        return self.storage.get_user_selection(username)
    
    def save_user_selection(self, selection: UserPromptSelection):
        """保存用户提示词选择"""
        self.storage.save_user_selection(selection)
    
    def create_global_prompt(
        self, 
        name: str, 
        prompts_dict: Dict[str, str], 
        owner: str,
        description: Optional[str] = None
    ) -> PromptFile:
        """创建全局提示词"""
        return self.storage.create_global_prompt(name, prompts_dict, owner, description)
    
    def update_global_prompt(
        self, 
        prompt_id: str, 
        prompts_dict: Dict[str, str], 
        updated_by: str
    ) -> bool:
        """更新全局提示词"""
        return self.storage.update_global_prompt(prompt_id, prompts_dict, updated_by)
    
    def delete_global_prompt(self, prompt_id: str) -> bool:
        """删除全局提示词"""
        return self.storage.delete_global_prompt(prompt_id)
    
    def save_user_personal_prompt(
        self, 
        username: str, 
        prompts_dict: Dict[str, str]
    ) -> bool:
        """保存用户个人提示词"""
        return self.storage.save_user_personal_prompt(username, prompts_dict)
    
    def get_all_versions(self) -> Dict[str, List[dict]]:
        """获取所有版本信息"""
        return self.storage.get_all_versions()
    
    def get_prompt_versions(self, prompt_id: str) -> List:
        """获取提示词版本列表"""
        return self.storage.get_prompt_versions(prompt_id)
    
    def validate_prompt_dict(self, prompts_dict: Dict[str, str]) -> Tuple[bool, str]:
        """验证提示词字典"""
        if not prompts_dict:
            return False, "提示词不能为空"
        
        # 检查是否有重复的提示词名称
        names = list(prompts_dict.keys())
        if len(names) != len(set(names)):
            return False, "提示词名称不能重复"
        
        # 检查提示词名称和内容
        for name, content in prompts_dict.items():
            if not name or not name.strip():
                return False, "提示词名称不能为空"
            if not content or not content.strip():
                return False, f"提示词 '{name}' 的内容不能为空"
            
            # 检查名称长度
            if len(name.strip()) > 100:
                return False, f"提示词名称 '{name}' 过长（最大100字符）"
            
            # 检查内容长度
            if len(content.strip()) > 10000:
                return False, f"提示词 '{name}' 的内容过长（最大10000字符）"
        
        return True, "验证通过"
    
    def get_merged_prompts(self, username: str) -> Dict[str, str]:
        """获取用户合并后的提示词（包括选择的全局提示词和个人提示词）"""
        user_selection = self.get_user_selection(username)
        merged_prompts = {}
        
        # 添加选择的全局提示词
        for prompt_id in user_selection.selected_global_prompts:
            global_prompts = self.get_global_prompts()
            for prompt_file in global_prompts:
                if prompt_file.id == prompt_id:
                    prompts_dict = self.storage.load_prompts_from_json(
                        self.storage.global_dir / self.storage.global_prompts[prompt_id]['file_path']
                    )
                    # 添加前缀以避免冲突
                    for name, content in prompts_dict.items():
                        prefixed_name = f"[{prompt_file.name}] {name}"
                        merged_prompts[prefixed_name] = content
                    break
        
        # 添加个人提示词（优先级更高，会覆盖同名的全局提示词）
        if user_selection.personal_prompt:
            personal_prompt = self.get_user_personal_prompt(username)
            if personal_prompt:
                prompts_dict = self.storage.load_prompts_from_json(
                    self.storage.users_dir / f"{username}_prompts.json"
                )
                merged_prompts.update(prompts_dict)
        
        return merged_prompts
    
    def get_prompt_statistics(self) -> Dict[str, int]:
        """获取提示词统计信息"""
        global_prompts = self.get_global_prompts()
        total_global_items = sum(p.item_count for p in global_prompts)
        
        return {
            "global_prompt_count": len(global_prompts),
            "total_global_items": total_global_items,
            "total_users": len(self.storage.user_selections)
        }


# 全局管理器实例
_prompt_manager = None


def get_prompt_manager() -> PromptManager:
    """获取提示词管理器实例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager
