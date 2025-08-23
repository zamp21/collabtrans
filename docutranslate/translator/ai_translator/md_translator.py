import asyncio
from dataclasses import dataclass
from typing import Self

from docutranslate.agents import MDTranslateAgent
from docutranslate.agents.markdown_agent import MDTranslateAgentConfig
from docutranslate.context.md_mask_context import MDMaskUrisContext
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.translator.ai_translator.base import AiTranslatorConfig
from docutranslate.translator.base import Translator
from docutranslate.utils.markdown_splitter import split_markdown_text, join_markdown_texts


@dataclass
class MDTranslatorConfig(AiTranslatorConfig):
    ...


class MDTranslator(Translator):
    def __init__(self, config: MDTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        agent_config = MDTranslateAgentConfig(custom_prompt=config.custom_prompt,
                                              to_lang=config.to_lang,
                                              baseurl=config.base_url,
                                              key=config.api_key,
                                              model_id=config.model_id,
                                              system_prompt=None,
                                              temperature=config.temperature,
                                              thinking=config.thinking,
                                              max_concurrent=config.concurrent,
                                              timeout=config.timeout,
                                              logger=self.logger)
        self.translate_agent = MDTranslateAgent(agent_config)

    def translate(self, document: MarkdownDocument) -> Self:
        self.logger.info("正在翻译markdown")
        with MDMaskUrisContext(document):
            chunks: list[str] = split_markdown_text(document.content.decode(), self.chunk_size)
            self.logger.info(f"markdown分为{len(chunks)}块")
            result: list[str] = self.translate_agent.send_prompts(chunks)
            content = join_markdown_texts(result)
            # 做一些加强鲁棒性的操作
            content = content.replace(r'\（', r'\(')
            content = content.replace(r'\）', r'\)')

            document.content = content.encode()
        self.logger.info("翻译完成")
        return self

    async def translate_async(self, document: MarkdownDocument) -> Self:
        self.logger.info("正在翻译markdown")
        with MDMaskUrisContext(document):
            chunks: list[str] = split_markdown_text(document.content.decode(), self.chunk_size)
            self.logger.info(f"markdown分为{len(chunks)}块")
            result: list[str] = await self.translate_agent.send_prompts_async(chunks)

            def run():
                content = join_markdown_texts(result)
                # 做一些加强鲁棒性的操作
                content = content.replace(r'\（', r'\(')
                content = content.replace(r'\）', r'\)')
                document.content = content.encode()

            await asyncio.to_thread(run)
        self.logger.info("翻译完成")
        return self