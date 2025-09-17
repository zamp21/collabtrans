# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import json
import csv
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .models import GlossaryFile, GlossaryItem, UserGlossarySelection, GlossaryVersion

logger = logging.getLogger(__name__)


class GlossaryStorage:
    """术语表存储管理器"""
    
    def __init__(self, base_dir: str = "glossaries"):
        self.base_dir = Path(base_dir)
        self.global_dir = self.base_dir / "global"
        self.users_dir = self.base_dir / "users"
        self.metadata_dir = self.base_dir / "metadata"
        
        # 元数据文件
        self.global_glossaries_file = self.metadata_dir / "global_glossaries.json"
        self.user_selections_file = self.metadata_dir / "user_selections.json"
        self.versions_file = self.metadata_dir / "versions.json"
        
        # 创建目录结构
        self._ensure_directories()
        
        # 加载元数据
        self.global_glossaries = self._load_global_glossaries()
        self.user_selections = self._load_user_selections()
        self.versions = self._load_versions()
    
    def _ensure_directories(self):
        """确保目录结构存在"""
        self.global_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_global_glossaries(self) -> Dict[str, dict]:
        """加载全局术语表元数据"""
        if self.global_glossaries_file.exists():
            try:
                with open(self.global_glossaries_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载全局术语表元数据失败: {e}")
        return {}
    
    def _save_global_glossaries(self):
        """保存全局术语表元数据"""
        try:
            with open(self.global_glossaries_file, 'w', encoding='utf-8') as f:
                json.dump(self.global_glossaries, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"保存全局术语表元数据失败: {e}")
    
    def _load_user_selections(self) -> Dict[str, dict]:
        """加载用户选择元数据"""
        if self.user_selections_file.exists():
            try:
                with open(self.user_selections_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载用户选择元数据失败: {e}")
        return {}
    
    def _save_user_selections(self):
        """保存用户选择元数据"""
        try:
            with open(self.user_selections_file, 'w', encoding='utf-8') as f:
                json.dump(self.user_selections, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"保存用户选择元数据失败: {e}")
    
    def _load_versions(self) -> Dict[str, float]:
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
                json.dump(self.versions, f, indent=2)
        except Exception as e:
            logger.error(f"保存版本信息失败: {e}")
    
    def update_glossary_version(self, glossary_id: str, updated_by: str):
        """更新术语表版本"""
        self.versions[glossary_id] = time.time()
        self._save_versions()
        logger.info(f"术语表 {glossary_id} 版本已更新，更新者: {updated_by}")
    
    def get_glossary_version(self, glossary_id: str) -> float:
        """获取术语表版本"""
        return self.versions.get(glossary_id, 0)
    
    def get_all_versions(self) -> Dict[str, float]:
        """获取所有术语表版本"""
        return self.versions.copy()
    
    def load_glossary_from_csv(self, file_path: Path) -> Dict[str, str]:
        """从CSV文件加载术语表"""
        glossary_dict = {}
        try:
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    src = row.get('src', '').strip()
                    dst = row.get('dst', '').strip()
                    if src and dst:
                        glossary_dict[src] = dst
        except Exception as e:
            logger.error(f"加载CSV文件失败 {file_path}: {e}")
            raise
        return glossary_dict
    
    def save_glossary_to_csv(self, glossary_dict: Dict[str, str], file_path: Path):
        """保存术语表到CSV文件"""
        try:
            with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['src', 'dst'])
                for src, dst in glossary_dict.items():
                    writer.writerow([src, dst])
        except Exception as e:
            logger.error(f"保存CSV文件失败 {file_path}: {e}")
            raise
    
    def get_global_glossaries(self) -> List[GlossaryFile]:
        """获取全局术语表列表"""
        glossaries = []
        for glossary_id, metadata in self.global_glossaries.items():
            file_path = self.global_dir / metadata['file_path']
            if file_path.exists():
                # 计算术语数量
                try:
                    glossary_dict = self.load_glossary_from_csv(file_path)
                    item_count = len(glossary_dict)
                except:
                    item_count = 0
                
                glossary = GlossaryFile(
                    id=glossary_id,
                    name=metadata['name'],
                    file_path=str(file_path),
                    owner=metadata['owner'],
                    is_global=True,
                    created_at=datetime.fromisoformat(metadata['created_at']),
                    updated_at=datetime.fromisoformat(metadata['updated_at']),
                    item_count=item_count,
                    description=metadata.get('description')
                )
                glossaries.append(glossary)
        return glossaries
    
    def get_user_personal_glossary(self, username: str) -> Optional[GlossaryFile]:
        """获取用户个人术语表"""
        user_dir = self.users_dir / username
        personal_file = user_dir / "personal_glossary.csv"
        
        if personal_file.exists():
            try:
                glossary_dict = self.load_glossary_from_csv(personal_file)
                return GlossaryFile(
                    id=f"personal_{username}",
                    name="个人术语表",
                    file_path=str(personal_file),
                    owner=username,
                    is_global=False,
                    created_at=datetime.fromtimestamp(personal_file.stat().st_ctime),
                    updated_at=datetime.fromtimestamp(personal_file.stat().st_mtime),
                    item_count=len(glossary_dict),
                    description="用户个人术语表"
                )
            except Exception as e:
                logger.error(f"获取用户个人术语表失败 {username}: {e}")
        return None
    
    def get_user_selection(self, username: str) -> UserGlossarySelection:
        """获取用户术语表选择"""
        selection_data = self.user_selections.get(username, {})
        return UserGlossarySelection(
            username=username,
            selected_global_glossaries=selection_data.get('selected_global_glossaries', []),
            personal_glossary=selection_data.get('personal_glossary')
        )
    
    def save_user_selection(self, selection: UserGlossarySelection):
        """保存用户术语表选择"""
        self.user_selections[selection.username] = {
            'selected_global_glossaries': selection.selected_global_glossaries,
            'personal_glossary': selection.personal_glossary
        }
        self._save_user_selections()
    
    def create_global_glossary(
        self, 
        name: str, 
        glossary_dict: Dict[str, str], 
        owner: str,
        description: Optional[str] = None
    ) -> GlossaryFile:
        """创建全局术语表"""
        # 生成文件名
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')
        file_path = f"{safe_name}.csv"
        
        # 保存文件
        full_path = self.global_dir / file_path
        self.save_glossary_to_csv(glossary_dict, full_path)
        
        # 创建元数据
        glossary_id = f"global_{int(time.time())}"
        now = datetime.now()
        
        glossary_metadata = {
            'name': name,
            'file_path': file_path,
            'owner': owner,
            'created_at': now.isoformat(),
            'updated_at': now.isoformat(),
            'description': description
        }
        
        self.global_glossaries[glossary_id] = glossary_metadata
        self._save_global_glossaries()
        
        # 更新版本
        self.update_glossary_version(glossary_id, owner)
        
        return GlossaryFile(
            id=glossary_id,
            name=name,
            file_path=str(full_path),
            owner=owner,
            is_global=True,
            created_at=now,
            updated_at=now,
            item_count=len(glossary_dict),
            description=description
        )
    
    def update_global_glossary(
        self, 
        glossary_id: str, 
        glossary_dict: Dict[str, str], 
        updated_by: str
    ) -> bool:
        """更新全局术语表"""
        if glossary_id not in self.global_glossaries:
            return False
        
        metadata = self.global_glossaries[glossary_id]
        file_path = self.global_dir / metadata['file_path']
        
        # 保存文件
        self.save_glossary_to_csv(glossary_dict, file_path)
        
        # 更新元数据
        metadata['updated_at'] = datetime.now().isoformat()
        self._save_global_glossaries()
        
        # 更新版本
        self.update_glossary_version(glossary_id, updated_by)
        
        return True
    
    def delete_global_glossary(self, glossary_id: str) -> bool:
        """删除全局术语表"""
        if glossary_id not in self.global_glossaries:
            return False
        
        metadata = self.global_glossaries[glossary_id]
        file_path = self.global_dir / metadata['file_path']
        
        # 删除文件
        if file_path.exists():
            file_path.unlink()
        
        # 删除元数据
        del self.global_glossaries[glossary_id]
        self._save_global_glossaries()
        
        # 删除版本信息
        if glossary_id in self.versions:
            del self.versions[glossary_id]
            self._save_versions()
        
        return True
    
    def save_user_personal_glossary(
        self, 
        username: str, 
        glossary_dict: Dict[str, str]
    ) -> bool:
        """保存用户个人术语表"""
        user_dir = self.users_dir / username
        user_dir.mkdir(parents=True, exist_ok=True)
        
        personal_file = user_dir / "personal_glossary.csv"
        self.save_glossary_to_csv(glossary_dict, personal_file)
        
        # 更新版本
        personal_id = f"personal_{username}"
        self.update_glossary_version(personal_id, username)
        
        return True


# 全局存储实例
_glossary_storage = None


def get_glossary_storage() -> GlossaryStorage:
    """获取术语表存储实例"""
    global _glossary_storage
    if _glossary_storage is None:
        _glossary_storage = GlossaryStorage()
    return _glossary_storage
