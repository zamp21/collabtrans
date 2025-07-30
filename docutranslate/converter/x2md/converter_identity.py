from docutranslate.converter.x2md.base import X2MarkdownConverter
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument


class ConverterIdentity(X2MarkdownConverter):
    #TODO:支持markdown_zip格式输入
    def convert(self, document: Document) -> MarkdownDocument:
        return MarkdownDocument.from_bytes(content=document.content, suffix=".md", stem=document.stem)

    async def convert_async(self, document: Document) -> MarkdownDocument:
        return MarkdownDocument.from_bytes(content=document.content, suffix=".md", stem=document.stem)

    def support_format(self) -> list[str]:
        return [".md"]
