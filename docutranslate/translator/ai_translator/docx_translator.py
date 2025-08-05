import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

import docx
from docx.document import Document as DocumentObject
from docx.table import _Cell

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig
from docutranslate.translator.base import Translator


@dataclass
class DocxTranslatorConfig(AiTranslatorConfig):
    """
    DocxTranslator 的配置类。
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class DocxTranslator(Translator):
    """
    用于翻译 .docx 文件的翻译器。
    """

    def __init__(self, config: DocxTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        agent_config = SegmentsTranslateAgentConfig(
            custom_prompt=config.custom_prompt,
            to_lang=config.to_lang,
            baseurl=config.base_url,
            key=config.api_key,
            model_id=config.model_id,
            system_prompt=None,
            temperature=config.temperature,
            thinking=config.thinking,
            max_concurrent=config.concurrent,
            timeout=config.timeout,
            logger=self.logger
        )
        self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        """
        预处理 .docx 文件，提取所有需要翻译的文本。

        :param document: 包含 .docx 文件内容的 Document 对象。
        :return: 一个元组，包含：
                 - docx.Document 对象
                 - 一个包含文本元素信息的列表 (e.g., paragraph, cell)
                 - 一个包含所有待翻译原文的列表
        """
        doc = docx.Document(BytesIO(document.content))
        elements_to_translate = []
        original_texts = []

        # 遍历所有段落
        for para in doc.paragraphs:
            if para.text.strip():  # 确保段落有实际内容
                elements_to_translate.append({"type": "paragraph", "element": para})
                original_texts.append(para.text)

        # 遍历所有表格
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():  # 确保单元格有实际内容
                        elements_to_translate.append({"type": "cell", "element": cell})
                        original_texts.append(cell.text)

        return doc, elements_to_translate, original_texts

    def _after_translate(self, doc: DocumentObject, elements_to_translate: List[Dict[str, Any]],
                         translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        将翻译后的文本写回到 .docx 对象中。

        :param doc: docx.Document 对象。
        :param elements_to_translate: 包含文本元素信息的列表。
        :param translated_texts: 翻译后的文本列表。
        :param original_texts: 原始文本列表。
        :return: 更新后的 .docx 文件内容的字节流。
        """
        for i, element_info in enumerate(elements_to_translate):
            element = element_info["element"]
            original_text = original_texts[i]
            translated_text = translated_texts[i]

            # 清空原有内容并写入新内容
            if isinstance(element, docx.text.paragraph.Paragraph):
                # 清空段落内容
                element.clear()
                # 根据插入模式添加文本
                if self.insert_mode == "replace":
                    element.add_run(translated_text)
                elif self.insert_mode == "append":
                    element.add_run(original_text + self.separator + translated_text)
                elif self.insert_mode == "prepend":
                    element.add_run(translated_text + self.separator + original_text)
                else:
                    self.logger.error("不正确的DocxTranslatorConfig参数")

            elif isinstance(element, _Cell):
                # 根据插入模式设置单元格文本
                if self.insert_mode == "replace":
                    element.text = translated_text
                elif self.insert_mode == "append":
                    element.text = original_text + self.separator + translated_text
                elif self.insert_mode == "prepend":
                    element.text = translated_text + self.separator + original_text
                else:
                    self.logger.error("不正确的DocxTranslatorConfig参数")

        # 将修改后的文档保存到 BytesIO 流
        doc_output_stream = BytesIO()
        doc.save(doc_output_stream)
        return doc_output_stream.getvalue()

    def translate(self, document: Document) -> Self:
        """
        同步翻译 .docx 文件。
        """
        doc, elements_to_translate, original_texts = self._pre_translate(document)
        if not elements_to_translate:
            print("\n文件中没有找到需要翻译的文本内容。")
            return self

        # 调用翻译 agent
        translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)

        # 将翻译结果写回文档
        document.content = self._after_translate(doc, elements_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译 .docx 文件。
        """
        doc, elements_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)
        if not elements_to_translate:
            print("\n文件中没有找到需要翻译的文本内容。")
            return self

        # 异步调用翻译 agent
        translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)

        # 将翻译结果写回文档
        document.content = await asyncio.to_thread(self._after_translate, doc, elements_to_translate, translated_texts,
                                                   original_texts)
        return self