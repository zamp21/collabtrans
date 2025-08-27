from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar

from docutranslate.agents.agent import ThinkingMode
from docutranslate.ir.document import Document
from docutranslate.translator.base import Translator, TranslatorConfig


@dataclass(kw_only=True)
class AiTranslatorConfig(TranslatorConfig):
    base_url: str
    api_key: str
    model_id: str
    to_lang: str
    custom_prompt: str | None = None
    temperature: float = 0.7
    thinking: ThinkingMode = "default"
    timeout: int = 2000
    chunk_size: int = 3000
    concurrent: int = 30
    glossary_dict: dict[str:str] | None = None


T = TypeVar('T', bound=Document)


class AiTranslator(Translator[T]):
    """
    翻译中间文本（原地替换），Translator不做格式转换
    """

    def __init__(self, config: AiTranslatorConfig):
        super().__init__(config=config)


    @abstractmethod
    def translate(self, document: T) -> Document:
        ...

    @abstractmethod
    async def translate_async(self, document: T) -> Document:
        ...
