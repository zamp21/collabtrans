from typing import runtime_checkable

from typing import Protocol
from docutranslate.converter.interfaces import Converter
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument



@runtime_checkable
class X2MarkdownConverter(Converter,Protocol):
    """
    负责将其它格式的文件转换为markdown
    """
    def convert(self, document: Document) -> MarkdownDocument:
        ...

    async def convert_async(self, document: Document) -> MarkdownDocument:
        ...

    def support_format(self)->list[str]:
        ...