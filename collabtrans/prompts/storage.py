# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import json
import csv
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import PromptFile, PromptItem, UserPromptSelection, PromptVersion

logger = logging.getLogger(__name__)


class PromptStorage:
    """提示词存储管理器"""
    
    def __init__(self, base_dir: str = "prompts"):
        self.base_dir = Path(base_dir)
        self.global_dir = self.base_dir / "global"
        self.users_dir = self.base_dir / "users"
        self.metadata_dir = self.base_dir / "metadata"
        
        # 元数据文件
        self.global_prompts_file = self.metadata_dir / "global_prompts.json"
        self.user_selections_file = self.metadata_dir / "user_selections.json"
        self.versions_file = self.metadata_dir / "versions.json"
        
        # 创建目录结构
        self._ensure_directories()
        
        # 加载元数据
        self.global_prompts = self._load_global_prompts()
        self.user_selections = self._load_user_selections()
        self.versions = self._load_versions()
    
    def _ensure_directories(self):
        """确保目录结构存在"""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_global_prompts(self) -> Dict[str, dict]:
        """加载全局提示词元数据"""
        if self.global_prompts_file.exists():
            try:
                with open(self.global_prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载全局提示词元数据失败: {e}")
        return {}
    
    def _save_global_prompts(self):
        """保存全局提示词元数据"""
        try:
            with open(self.global_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(self.global_prompts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存全局提示词元数据失败: {e}")
    
    def _load_user_selections(self) -> Dict[str, dict]:
        """加载用户选择"""
        if self.user_selections_file.exists():
            try:
                with open(self.user_selections_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载用户选择失败: {e}")
        return {}
    
    def _save_user_selections(self):
        """保存用户选择"""
        try:
            with open(self.user_selections_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_selections, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户选择失败: {e}")
    
    def _load_versions(self) -> Dict[str, List[dict]]:
        """加载版本信息"""
        if self.versions_file.exists():
            try:
                with open(self.versions_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载版本信息失败: {e}")
        return {}
    
    def _save_versions(self):
        """保存版本信息"""
        try:
            with open(self.versions_file, 'w', encoding='utf-8') as f:
                json.dump(self.versions, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存版本信息失败: {e}")
    
    def get_global_prompts(self) -> List[PromptFile]:
        """获取全局提示词列表"""
        result = []
        for prompt_id, metadata in self.global_prompts.items():
            file_path = self.global_dir / metadata['file_path']
            if file_path.exists():
                # 读取提示词内容计算数量
                prompts_dict = self.load_prompts_from_json(file_path)
                item_count = len(prompts_dict)
                
                result.append(PromptFile(
                    id=prompt_id,
                    name=metadata['name'],
                    file_path=str(file_path),
                    owner=metadata['owner'],
                    is_global=True,
                    created_at=datetime.fromisoformat(metadata['created_at']),
                    updated_at=datetime.fromisoformat(metadata['updated_at']),
                    item_count=item_count,
                    description=metadata.get('description')
                ))
        return result
    
    def get_user_personal_prompt(self, username: str) -> Optional[PromptFile]:
        """获取用户个人提示词"""
        file_path = self.users_dir / f"{username}_prompts.json"
        if file_path.exists():
            prompts_dict = self.load_prompts_from_json(file_path)
            if prompts_dict:
                return PromptFile(
                    id=f"personal_{username}",
                    name=f"{username}'s Personal Prompts",
                    file_path=str(file_path),
                    owner=username,
                    is_global=False,
                    created_at=datetime.fromtimestamp(file_path.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(file_path.stat().st_mtime),
                    item_count=len(prompts_dict),
                    description="Personal prompt collection"
                )
        return None
    
    def delete_user_personal_prompt(self, username: str) -> bool:
        """删除用户个人提示词"""
        try:
            file_path = self.users_dir / f"{username}_prompts.json"
            if file_path.exists():
                file_path.unlink()
                logger.info(f"已删除用户 {username} 的个人提示词文件")
                return True
            return False
        except Exception as e:
            logger.error(f"删除用户 {username} 个人提示词失败: {e}")
            return False
    
    def get_user_selection(self, username: str) -> UserPromptSelection:
        """获取用户提示词选择"""
        selection_data = self.user_selections.get(username, {})
        return UserPromptSelection(
            username=username,
            selected_global_prompts=selection_data.get('selected_global_prompts', []),
            personal_prompt=selection_data.get('personal_prompt')
        )
    
    def save_user_selection(self, selection: UserPromptSelection):
        """保存用户提示词选择"""
        self.user_selections[selection.username] = {
            'selected_global_prompts': selection.selected_global_prompts,
            'personal_prompt': selection.personal_prompt
        }
        self._save_user_selections()
    
    def load_prompts_from_json(self, file_path: Path) -> Dict[str, str]:
        """从JSON文件加载提示词"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载提示词文件失败 {file_path}: {e}")
            return {}
    
    def save_prompts_to_json(self, prompts_dict: Dict[str, str], file_path: Path):
        """保存提示词到JSON文件"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(prompts_dict, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存提示词文件失败 {file_path}: {e}")
            raise
    
    def create_global_prompt(
        self, 
        name: str, 
        prompts_dict: Dict[str, str], 
        owner: str,
        description: Optional[str] = None
    ) -> PromptFile:
        """创建全局提示词"""
        # 生成文件名
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        file_path = f"{safe_name}.json"
        
        # 保存文件
        full_path = self.global_dir / file_path
        self.save_prompts_to_json(prompts_dict, full_path)
        
        # 创建元数据
        prompt_id = f"global_{int(time.time())}"
        now = datetime.now()
        
        prompt_metadata = {
            'name': name,
            'file_path': file_path,
            'owner': owner,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'description': description
        }
        
        self.global_prompts[prompt_id] = prompt_metadata
        self._save_global_prompts()
        
        # 更新版本
        self.update_prompt_version(prompt_id, owner)
        
        return PromptFile(
            id=prompt_id,
            name=name,
            file_path=str(full_path),
            owner=owner,
            is_global=True,
            created_at=now,
            updated_at=now,
            item_count=len(prompts_dict),
            description=description
        )
    
    def update_global_prompt(
        self, 
        prompt_id: str, 
        prompts_dict: Dict[str, str], 
        updated_by: str
    ) -> bool:
        """更新全局提示词"""
        if prompt_id not in self.global_prompts:
            return False
        
        metadata = self.global_prompts[prompt_id]
        file_path = self.global_dir / metadata['file_path']
        
        # 保存文件
        self.save_prompts_to_json(prompts_dict, file_path)
        
        # 更新元数据
        metadata['updated_at'] = datetime.now().isoformat()
        self._save_global_prompts()
        
        # 更新版本
        self.update_prompt_version(prompt_id, updated_by)
        
        return True
    
    def delete_global_prompt(self, prompt_id: str) -> bool:
        """删除全局提示词"""
        if prompt_id not in self.global_prompts:
            return False
        
        metadata = self.global_prompts[prompt_id]
        file_path = self.global_dir / metadata['file_path']
        
        # 删除文件
        if file_path.exists():
            file_path.unlink()
        
        # 删除元数据
        del self.global_prompts[prompt_id]
        self._save_global_prompts()
        
        # 删除版本信息
        if prompt_id in self.versions:
            del self.versions[prompt_id]
            self._save_versions()
        
        return True
    
    def save_user_personal_prompt(
        self, 
        username: str, 
        prompts_dict: Dict[str, str]
    ) -> bool:
        """保存用户个人提示词"""
        try:
            file_path = self.users_dir / f"{username}_prompts.json"
            self.save_prompts_to_json(prompts_dict, file_path)
            return True
        except Exception as e:
            logger.error(f"保存用户个人提示词失败: {e}")
            return False
    
    def update_prompt_version(self, prompt_id: str, updated_by: str):
        """更新提示词版本"""
        if prompt_id not in self.versions:
            self.versions[prompt_id] = []
        
        # 获取当前版本号
        current_version = len(self.versions[prompt_id])
        new_version = current_version + 1
        
        # 添加新版本记录
        version_record = {
            'version': new_version,
            'updated_by': updated_by,
            'updated_at': datetime.now().isoformat()
        }
        
        self.versions[prompt_id].append(version_record)
        self._save_versions()
    
    def get_all_versions(self) -> Dict[str, List[dict]]:
        """获取所有版本信息"""
        return self.versions.copy()
    
    def get_prompt_versions(self, prompt_id: str) -> List[PromptVersion]:
        """获取提示词版本列表"""
        versions_data = self.versions.get(prompt_id, [])
        return [
            PromptVersion(
                prompt_id=prompt_id,
                version=v['version'],
                updated_by=v['updated_by'],
                updated_at=datetime.fromisoformat(v['updated_at'])
            )
            for v in versions_data
        ]


# 全局存储实例
_prompt_storage = None


def get_prompt_storage() -> PromptStorage:
    """获取提示词存储实例"""
    global _prompt_storage
    if _prompt_storage is None:
        _prompt_storage = PromptStorage()
    return _prompt_storage
