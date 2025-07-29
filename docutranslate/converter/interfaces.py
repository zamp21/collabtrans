from typing import Protocol

from docutranslate.ir.document import Document


class Converter(Protocol):
    def convert(self, document: Document) -> Document:
        ...

    async def convert_async(self, document: Document) -> Document:
        ...
