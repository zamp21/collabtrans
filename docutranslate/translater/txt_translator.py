from dataclasses import dataclass
from typing import Self

from docutranslate.agents.txt_agent import TXTTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.logger import global_logger
from docutranslate.translater.base import AiTranslateConfig
from docutranslate.translater.interfaces import Translator
from docutranslate.utils.markdown_splitter import split_markdown_text


@dataclass
class TXTTranslateConfig(AiTranslateConfig):
    ...


class TXTTranslator(Translator):
    def __init__(self, config: TXTTranslateConfig):
        self.logger = config.logger or global_logger
        self.chunk_size = config.chunk_size
        self.translate_agent = TXTTranslateAgent(custom_prompt=config.custom_prompt,
                                                 to_lang=config.to_lang,
                                                 baseurl=config.base_url,
                                                 key=config.api_key,
                                                 model_id=config.model_id,
                                                 system_prompt=None,
                                                 temperature=config.temperature,
                                                 max_concurrent=config.concurrent,
                                                 timeout=config.timeout,
                                                 logger=self.logger)

    def translate(self, document: Document) -> Self:
        self.logger.info("正在翻译txt")
        chunks: list[str] = split_markdown_text(document.content.decode(), max_block_size=self.chunk_size)
        self.logger.info(f"txt分为{len(chunks)}块")
        result: list[str] = self.translate_agent.send_prompts(chunks)
        content = "\n".join(result)
        document.content = content.encode()
        self.logger.info("翻译完成")
        return self

    async def translate_async(self, document: Document) -> Self:
        self.logger.info("正在翻译txt")
        chunks: list[str] = split_markdown_text(document.content.decode(), max_block_size=self.chunk_size)
        self.logger.info(f"txt分为{len(chunks)}块")
        result: list[str] = await self.translate_agent.send_prompts_async(chunks)
        content = "\n".join(result)
        document.content = content.encode()
        self.logger.info("翻译完成")
        return self
