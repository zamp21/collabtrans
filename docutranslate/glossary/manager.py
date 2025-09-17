# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import GlossaryFile, GlossaryItem, UserGlossarySelection
from .storage import get_glossary_storage

logger = logging.getLogger(__name__)


class GlossaryManager:
    """术语表管理器"""
    
    def __init__(self):
        self.storage = get_glossary_storage()
    
    def get_global_glossaries(self) -> List[GlossaryFile]:
        """获取全局术语表列表"""
        return self.storage.get_global_glossaries()
    
    def get_user_personal_glossary(self, username: str) -> Optional[GlossaryFile]:
        """获取用户个人术语表"""
        return self.storage.get_user_personal_glossary(username)
    
    def get_user_selection(self, username: str) -> UserGlossarySelection:
        """获取用户术语表选择"""
        return self.storage.get_user_selection(username)
    
    def save_user_selection(self, selection: UserGlossarySelection):
        """保存用户术语表选择"""
        self.storage.save_user_selection(selection)
    
    def create_global_glossary(
        self, 
        name: str, 
        glossary_dict: Dict[str, str], 
        owner: str,
        description: Optional[str] = None
    ) -> GlossaryFile:
        """创建全局术语表"""
        return self.storage.create_global_glossary(name, glossary_dict, owner, description)
    
    def update_global_glossary(
        self, 
        glossary_id: str, 
        glossary_dict: Dict[str, str], 
        updated_by: str
    ) -> bool:
        """更新全局术语表"""
        return self.storage.update_global_glossary(glossary_id, glossary_dict, updated_by)
    
    def delete_global_glossary(self, glossary_id: str) -> bool:
        """删除全局术语表"""
        return self.storage.delete_global_glossary(glossary_id)
    
    def save_user_personal_glossary(
        self, 
        username: str, 
        glossary_dict: Dict[str, str]
    ) -> bool:
        """保存用户个人术语表"""
        return self.storage.save_user_personal_glossary(username, glossary_dict)
    
    def get_glossary_content(self, glossary_id: str) -> Optional[Dict[str, str]]:
        """获取术语表内容"""
        try:
            # 检查是否为全局术语表
            if glossary_id.startswith('global_'):
                global_glossaries = self.get_global_glossaries()
                for glossary in global_glossaries:
                    if glossary.id == glossary_id:
                        return self.storage.load_glossary_from_csv(glossary.file_path)
            
            # 检查是否为个人术语表
            elif glossary_id.startswith('personal_'):
                username = glossary_id.replace('personal_', '')
                personal_glossary = self.get_user_personal_glossary(username)
                if personal_glossary:
                    return self.storage.load_glossary_from_csv(personal_glossary.file_path)
            
            return None
        except Exception as e:
            logger.error(f"获取术语表内容失败 {glossary_id}: {e}")
            return None
    
    def merge_user_glossaries(self, username: str) -> Dict[str, str]:
        """合并用户选择的术语表"""
        selection = self.get_user_selection(username)
        merged_glossary = {}
        
        # 1. 添加选中的全局术语表（优先级低）
        for global_id in selection.selected_global_glossaries:
            global_content = self.get_glossary_content(global_id)
            if global_content:
                merged_glossary.update(global_content)
        
        # 2. 添加个人术语表（优先级高，会覆盖冲突项）
        if selection.personal_glossary:
            personal_content = self.get_glossary_content(selection.personal_glossary)
            if personal_content:
                merged_glossary.update(personal_content)
        
        return merged_glossary
    
    def get_all_versions(self) -> Dict[str, float]:
        """获取所有术语表版本"""
        return self.storage.get_all_versions()
    
    def get_glossary_version(self, glossary_id: str) -> float:
        """获取术语表版本"""
        return self.storage.get_glossary_version(glossary_id)
    
    def update_glossary_version(self, glossary_id: str, updated_by: str):
        """更新术语表版本"""
        self.storage.update_glossary_version(glossary_id, updated_by)
    
    def validate_glossary_dict(self, glossary_dict: Dict[str, str]) -> Tuple[bool, str]:
        """验证术语表字典"""
        if not isinstance(glossary_dict, dict):
            return False, "术语表必须是字典格式"
        
        if len(glossary_dict) == 0:
            return False, "术语表不能为空"
        
        for src, dst in glossary_dict.items():
            if not isinstance(src, str) or not isinstance(dst, str):
                return False, "术语表的键和值都必须是字符串"
            
            if not src.strip() or not dst.strip():
                return False, "术语表的键和值不能为空"
        
        return True, "验证通过"
    
    def get_glossary_statistics(self) -> Dict[str, int]:
        """获取术语表统计信息"""
        global_glossaries = self.get_global_glossaries()
        total_global_items = sum(glossary.item_count for glossary in global_glossaries)
        
        return {
            "global_glossaries_count": len(global_glossaries),
            "total_global_items": total_global_items,
            "average_items_per_glossary": total_global_items // len(global_glossaries) if global_glossaries else 0
        }


# 全局管理器实例
_glossary_manager = None


def get_glossary_manager() -> GlossaryManager:
    """获取术语表管理器实例"""
    global _glossary_manager
    if _glossary_manager is None:
        _glossary_manager = GlossaryManager()
    return _glossary_manager
