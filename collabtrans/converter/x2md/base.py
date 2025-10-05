# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from abc import abstractmethod
from dataclasses import dataclass
from typing import Hashable

from collabtrans.converter.base import Converter, ConverterConfig
from collabtrans.ir.document import Document
from collabtrans.ir.markdown_document import MarkdownDocument

@dataclass(kw_only=True)
class X2MarkdownConverterConfig(ConverterConfig):
    ...
    @abstractmethod
    def gethash(self) ->Hashable:
        ...

class X2MarkdownConverter(Converter):
    """
    Responsible for converting files from other formats to markdown
    """

    @abstractmethod
    def convert(self, document: Document) -> MarkdownDocument:
        ...

    @abstractmethod
    async def convert_async(self, document: Document) -> MarkdownDocument:
        ...

    @abstractmethod
    def support_format(self)->list[str]:
        ...