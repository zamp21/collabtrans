# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from typing import Self

from docutranslate.agents.txt_agent import TXTTranslateAgent, TXTTranslateAgentConfig
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator
from docutranslate.utils.markdown_splitter import split_markdown_text


@dataclass
class TXTTranslatorConfig(AiTranslatorConfig):
    ...


class TXTTranslator(AiTranslator):
    def __init__(self, config: TXTTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent =None
        if not self.skip_translate:
            agent_config = TXTTranslateAgentConfig(custom_prompt=config.custom_prompt,
                                                   to_lang=config.to_lang,
                                                   baseurl=config.base_url,
                                                   key=config.api_key,
                                                   model_id=config.model_id,
                                                   temperature=config.temperature,
                                                   thinking=config.thinking,
                                                   max_concurrent=config.concurrent,
                                                   timeout=config.timeout,
                                                   logger=self.logger,
                                                   glossary_dict=config.glossary_dict)
            self.translate_agent = TXTTranslateAgent(agent_config)

    def translate(self, document: Document) -> Self:
        self.logger.info("正在翻译txt")
        chunks: list[str] = split_markdown_text(document.content.decode(), max_block_size=self.chunk_size)
        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(chunks, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        self.logger.info(f"txt分为{len(chunks)}块")
        if self.translate_agent:
            result: list[str] = self.translate_agent.send_chunks(chunks)
        else:
            result=chunks
        content = "\n".join(result)
        document.content = content.encode()
        self.logger.info("翻译完成")
        return self

    async def translate_async(self, document: Document) -> Self:
        self.logger.info("正在翻译txt")
        chunks: list[str] = split_markdown_text(document.content.decode(), max_block_size=self.chunk_size)

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(chunks, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        self.logger.info(f"txt分为{len(chunks)}块")
        if self.translate_agent:
            result: list[str] = await self.translate_agent.send_chunks_async(chunks)
        else:
            result=chunks
        content = "\n".join(result)
        document.content = content.encode()
        self.logger.info("翻译完成")
        return self
