from typing import Protocol, TypeVar

from docutranslate.agents import Agent
from docutranslate.ir.document import Document

T=TypeVar('T',bound=Document)
V=TypeVar('V',bound=Agent)

class Translator(Protocol[T,V]):
    """
    翻译中间文本（原地替换），Translator不做格式转换
    """
    def translate(self, document:T) -> Document:
        ...

    async def translate_async(self, document: T) -> Document:
        ...

    def log(self,info:str):
        ...