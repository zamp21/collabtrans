from abc import abstractmethod
from dataclasses import dataclass
from typing import TypeVar

from docutranslate.agents.agent import ThinkingMode
from docutranslate.agents.glossary_agent import GlossaryAgentConfig, GlossaryAgent
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
    glossary_generate_enable: bool = True
    glossary_agent_config: GlossaryAgentConfig | None = None


T = TypeVar('T', bound=Document)


class AiTranslator(Translator[T]):
    """
    翻译中间文本（原地替换），Translator不做格式转换
    """

    def __init__(self, config: AiTranslatorConfig):
        super().__init__(config=config)
        self.glossary_agent = None
        if config.glossary_generate_enable:
            if config.glossary_agent_config:
                self.glossary_agent = GlossaryAgent(config.glossary_agent_config)
            else:
                glossary_agent_config = GlossaryAgentConfig(
                    to_lang=config.to_lang,
                    baseurl=config.base_url,
                    key=config.api_key,
                    model_id=config.model_id,
                    system_prompt=None,
                    temperature=config.temperature,
                    thinking=config.thinking,
                    max_concurrent=config.concurrent,
                    timeout=config.timeout,
                    logger=self.logger,
                )
                self.glossary_agent = GlossaryAgent(glossary_agent_config)

    @abstractmethod
    def translate(self, document: T) -> Document:
        ...

    @abstractmethod
    async def translate_async(self, document: T) -> Document:
        ...
