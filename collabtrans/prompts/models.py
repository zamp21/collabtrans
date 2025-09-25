# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import uuid
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class PromptItem:
    """提示词项"""
    name: str  # 提示词名称
    content: str  # 提示词内容


@dataclass
class PromptFile:
    """提示词文件"""
    id: str  # 唯一标识
    name: str  # 提示词集名称
    file_path: str  # 文件路径
    owner: str  # 所有者
    is_global: bool = False  # 是否为全局提示词集
    created_at: datetime = None  # 创建时间
    updated_at: datetime = None  # 更新时间
    item_count: int = 0  # 提示词数量
    description: Optional[str] = None  # 描述


@dataclass
class UserPromptSelection:
    """用户提示词选择"""
    username: str  # 用户名
    selected_global_prompts: List[str]  # 选择的全局提示词集ID列表
    personal_prompt: Optional[str] = None  # 个人提示词集ID


@dataclass
class PromptVersion:
    """提示词版本信息"""
    prompt_id: str
    version: int
    updated_by: str
    updated_at: datetime


def generate_prompt_id() -> str:
    """生成提示词ID"""
    return str(uuid.uuid4())


def create_prompt_file(
    name: str,
    file_path: str,
    owner: str,
    is_global: bool = False,
    description: Optional[str] = None
) -> PromptFile:
    """创建提示词文件对象"""
    now = datetime.now()
    return PromptFile(
        id=generate_prompt_id(),
        name=name,
        file_path=file_path,
        owner=owner,
        is_global=is_global,
        created_at=now,
        updated_at=now,
        item_count=0,
        description=description
    )
