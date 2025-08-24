from dataclasses import dataclass
from typing import Hashable

from docutranslate.converter.base import Converter, ConverterConfig
from docutranslate.ir.document import Document


class ConverterIdentity(Converter):

    def convert(self, document: Document) -> Document:
        return Document.from_bytes(content=document.content, suffix=document.suffix, stem=document.stem)

    async def convert_async(self, document: Document) -> Document:
        return Document.from_bytes(content=document.content, suffix=document.suffix, stem=document.stem)
