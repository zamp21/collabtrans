# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime
import uuid


@dataclass
class GlossaryItem:
    """术语表项"""
    src: str  # 原文
    dst: str  # 译文


@dataclass
class GlossaryFile:
    """术语表文件"""
    id: str  # 唯一标识
    name: str  # 显示名称
    file_path: str  # 文件路径
    owner: str  # 所有者（用户名）
    is_global: bool  # 是否为全局术语表
    created_at: datetime
    updated_at: datetime
    item_count: int  # 术语数量
    description: Optional[str] = None  # 描述


@dataclass
class UserGlossarySelection:
    """用户术语表选择"""
    username: str
    selected_global_glossaries: List[str]  # 选中的全局术语表ID列表
    personal_glossary: Optional[str] = None  # 个人术语表ID


@dataclass
class GlossaryVersion:
    """术语表版本信息"""
    glossary_id: str
    version: float  # 时间戳
    updated_by: str  # 更新者
    updated_at: datetime


def generate_glossary_id() -> str:
    """生成术语表ID"""
    return str(uuid.uuid4())


def create_glossary_file(
    name: str,
    file_path: str,
    owner: str,
    is_global: bool = False,
    description: Optional[str] = None
) -> GlossaryFile:
    """创建术语表文件对象"""
    now = datetime.now()
    return GlossaryFile(
        id=generate_glossary_id(),
        name=name,
        file_path=file_path,
        owner=owner,
        is_global=is_global,
        created_at=now,
        updated_at=now,
        item_count=0,
        description=description
    )
