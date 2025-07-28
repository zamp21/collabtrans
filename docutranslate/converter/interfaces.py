from typing import Protocol, runtime_checkable

from docutranslate.ir.document import Document


@runtime_checkable
class Converter(Protocol):
    def convert(self, document: Document) -> Document:
        ...

    async def convert_async(self, document: Document) -> Document:
        ...
