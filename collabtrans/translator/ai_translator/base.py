# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import TypeVar

from collabtrans.agents.agent import AgentConfig
from collabtrans.agents.glossary_agent import GlossaryAgentConfig, GlossaryAgent
from collabtrans.ir.document import Document
from collabtrans.translator.base import Translator, TranslatorConfig


@dataclass(kw_only=True)
class AiTranslatorConfig(TranslatorConfig, AgentConfig):
    base_url: str | None = field(default=None,
                                 metadata={"description": "OpenAI compatible address, required when skip_translate is False"})
    model_id: str | None = field(default=None, metadata={"description": "Required when skip_translate is False"})
    to_lang: str = "Chinese"
    custom_prompt: str | None = None
    chunk_size: int = 3000
    glossary_dict: dict[str:str] | None = field(default=None)
    glossary_generate_enable: bool = False
    glossary_agent_config: GlossaryAgentConfig | None = None
    skip_translate: bool = False  # When skip_translate is False, base_url and model_id are required


T = TypeVar('T', bound=Document)


class AiTranslator(Translator[T]):
    """
    Translate intermediate text (in-place replacement), Translator does not perform format conversion
    """

    def __init__(self, config: AiTranslatorConfig):
        super().__init__(config=config)
        self.skip_translate = config.skip_translate
        self.glossary_agent = None
        self.glossary_dict_gen = None
        if not self.skip_translate and (config.base_url is None or config.api_key is None or config.model_id is None):
            raise ValueError("When skip_translate is not false, base_url, api_key, and model_id are required")

        if config.glossary_generate_enable:
            if config.glossary_agent_config:
                self.glossary_agent = GlossaryAgent(config.glossary_agent_config)
            else:
                glossary_agent_config = GlossaryAgentConfig(
                    to_lang=config.to_lang,
                    base_url=config.base_url,
                    api_key=config.api_key,
                    model_id=config.model_id,
                    temperature=config.temperature,
                    thinking=config.thinking,
                    concurrent=config.concurrent,
                    timeout=config.timeout,
                    logger=self.logger,
                    retry=config.retry
                )
                self.glossary_agent = GlossaryAgent(glossary_agent_config)

    @abstractmethod
    def translate(self, document: T) -> Document:
        ...

    @abstractmethod
    async def translate_async(self, document: T) -> Document:
        ...
