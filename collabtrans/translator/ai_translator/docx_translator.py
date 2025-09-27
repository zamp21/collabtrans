# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

import docx
from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from collabtrans.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from collabtrans.ir.document import Document
from collabtrans.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


def is_image_run(run: Run) -> bool:
    """Check if a run contains an image."""
    # w:drawing is the flag for embedded images, w:pict is the flag for VML images
    return '<w:drawing' in run.element.xml or '<w:pict' in run.element.xml


def get_font_for_language(target_language: str) -> str:
    """
    Return appropriate font based on target language.
    
    Args:
        target_language: Target language name
        
    Returns:
        Recommended font name
    """
    # Language to font mapping
    language_font_map = {
        # Chinese
        "中文": "Microsoft YaHei",  # Microsoft YaHei
        "简体中文": "Microsoft YaHei",
        "繁体中文": "Microsoft JhengHei",  # Microsoft JhengHei
        
        # English
        "English": "Calibri",
        
        # Japanese
        "日文": "Yu Gothic",  # Yu Gothic
        "日本語": "Yu Gothic",
        "Japanese": "Yu Gothic",
        
        # Korean
        "韩文": "Malgun Gothic",  # Malgun Gothic
        "한국어": "Malgun Gothic",
        "Korean": "Malgun Gothic",
        
        # Russian
        "俄文": "Times New Roman",  # Common Russian font
        "Русский": "Times New Roman",
        "Russian": "Times New Roman",
        
        # Arabic
        "阿拉伯文": "Arial Unicode MS",  # Supports Arabic characters
        "العَرَبِيَّة": "Arial Unicode MS",
        "Arabic": "Arial Unicode MS",
        
        # Other European languages
        "西班牙文": "Calibri",
        "Español": "Calibri",
        "Spanish": "Calibri",
        
        "法文": "Calibri",
        "Français": "Calibri",
        "French": "Calibri",
        
        "德文": "Calibri",
        "Deutsch": "Calibri",
        "German": "Calibri",
        
        "葡萄牙文": "Calibri",
        "Português": "Calibri",
        "Portuguese": "Calibri",
        
        # Vietnamese
        "越南文": "Arial Unicode MS",  # Supports Vietnamese characters
        "tiếng Việt": "Arial Unicode MS",
        "Vietnamese": "Arial Unicode MS",
        
        # Hebrew
        "希伯来文": "Arial Unicode MS",  # Supports Hebrew characters
        "Hebrew": "Arial Unicode MS",
        "עברית": "Arial Unicode MS",
        
        # Thai
        "泰文": "Arial Unicode MS",  # Supports Thai characters
        "Thai": "Arial Unicode MS",
        "ไทย": "Arial Unicode MS",
        
        # Hindi
        "印地文": "Arial Unicode MS",  # Supports Hindi characters
        "Hindi": "Arial Unicode MS",
        "हिन्दी": "Arial Unicode MS",
    }
    
    # Find matching font
    font = language_font_map.get(target_language)
    
    # If no matching font found, return default font
    if not font:
        # Intelligent selection based on language characteristics
        if any(char in target_language for char in ['中文', 'Chinese', '简体', '繁体']):
            font = "Microsoft YaHei"
        elif any(char in target_language for char in ['日文', 'Japanese', '日本語']):
            font = "Yu Gothic"
        elif any(char in target_language for char in ['韩文', 'Korean', '한국어']):
            font = "Malgun Gothic"
        elif any(char in target_language for char in ['俄文', 'Russian', 'Русский']):
            font = "Times New Roman"
        elif any(char in target_language for char in ['阿拉伯文', 'Arabic', 'العَرَبِيَّة']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['越南文', 'Vietnamese', 'tiếng Việt']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['希伯来文', 'Hebrew', 'עברית']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['泰文', 'Thai', 'ไทย']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['印地文', 'Hindi', 'हिन्दी']):
            font = "Arial Unicode MS"
        else:
            # Default to Calibri (suitable for most Latin alphabet languages)
            font = "Calibri"
    
    return font


@dataclass
class DocxTranslatorConfig(AiTranslatorConfig):
    """
    DocxTranslator 的配置类。
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class DocxTranslator(AiTranslator):
    """
    用于翻译 .docx 文件的翻译器。
    此版本经过优化，可以处理图文混排的段落而不会丢失图片。
    """

    def __init__(self, config: DocxTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt,
                to_lang=config.to_lang,
                base_url=config.base_url,
                api_key=config.api_key,
                model_id=config.model_id,
                temperature=config.temperature,
                thinking=config.thinking,
                concurrent=config.concurrent,
                timeout=config.timeout,
                logger=self.logger,
                glossary_dict=config.glossary_dict,
                retry=config.retry
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        """
        [已重构] 预处理 .docx 文件，在 Run 级别上提取文本，以避免破坏图片。
        :param document: 包含 .docx 文件内容的 Document 对象。
        :return: 一个元组，包含：
                 - docx.Document 对象
                 - 一个包含文本块信息的列表 (每个元素代表一组连续的文本 run)
                 - 一个包含所有待翻译原文的列表
        """
        doc = docx.Document(BytesIO(document.content))
        elements_to_translate = []
        original_texts = []

        def process_paragraph(para: Paragraph):
            nonlocal elements_to_translate, original_texts
            current_text_segment = ""
            current_runs = []

            for run in para.runs:
                if is_image_run(run):
                    # 遇到图片，将之前累积的文本作为一个翻译单元
                    if current_text_segment.strip():
                        elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                        original_texts.append(current_text_segment)
                    # 重置累加器
                    current_text_segment = ""
                    current_runs = []
                else:
                    # 累积文本 run
                    current_runs.append(run)
                    current_text_segment += run.text

            # 处理段落末尾的最后一个文本块
            if current_text_segment.strip():
                elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                original_texts.append(current_text_segment)

        # 遍历所有段落
        for para in doc.paragraphs:
            process_paragraph(para)

        # 遍历所有表格
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        process_paragraph(para)

        return doc, elements_to_translate, original_texts

    def _after_translate(self, doc: DocumentObject, elements_to_translate: List[Dict[str, Any]],
                         translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        [已重构] 将翻译后的文本写回到对应的 text runs 中，保留图片和样式。
        """
        translation_map = dict(zip(original_texts, translated_texts))

        for i, element_info in enumerate(elements_to_translate):
            runs = element_info["runs"]
            original_text = original_texts[i]
            translated_text = translated_texts[i]

            # Determine final text based on insert mode
            if self.insert_mode == "replace":
                final_text = translated_text
            elif self.insert_mode == "append":
                final_text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                final_text = translated_text + self.separator + original_text
            else:
                self.logger.error("Invalid DocxTranslatorConfig parameter")
                final_text = translated_text

            if not runs:
                continue

            # --- Core modification section ---
            # 1. Write complete translated text to the first run
            first_run = runs[0]
            first_run.text = final_text
            
            # 2. Set appropriate font based on target language to avoid font compatibility issues
            if first_run.font:
                # Select font based on target language
                target_font = get_font_for_language(self.config.to_lang)
                first_run.font.name = target_font
                
                # If primary font is not available, try fallback fonts
                if not first_run.font.name:
                    # Select fallback fonts based on language type
                    if any(char in self.config.to_lang for char in ['中文', 'Chinese', '简体', '繁体']):
                        # Chinese fallback fonts
                        fallback_fonts = ['SimSun', 'SimHei', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['日文', 'Japanese', '日本語']):
                        # Japanese fallback fonts
                        fallback_fonts = ['MS Gothic', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['韩文', 'Korean', '한국어']):
                        # Korean fallback fonts
                        fallback_fonts = ['Gulim', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['俄文', 'Russian', 'Русский']):
                        # Russian fallback fonts
                        fallback_fonts = ['Times New Roman', 'Arial', 'Calibri']
                    elif any(char in self.config.to_lang for char in ['阿拉伯文', 'Arabic', 'العَرَبِيَّة']):
                        # Arabic fallback fonts
                        fallback_fonts = ['Arial Unicode MS', 'Times New Roman', 'Arial']
                    else:
                        # Fallback fonts for other languages
                        fallback_fonts = ['Calibri', 'Times New Roman', 'Arial']
                    
                    # Try fallback fonts
                    for fallback_font in fallback_fonts:
                        first_run.font.name = fallback_font
                        if first_run.font.name:
                            break

            # 3. Clear content of remaining runs in this text block while preserving run structure
            #    This prevents duplicate text while maintaining document structure
            for run in runs[1:]:
                run.text = ""
            # --- End of modification ---

        # Save the modified document to BytesIO stream
        doc_output_stream = BytesIO()
        doc.save(doc_output_stream)
        return doc_output_stream.getvalue()

    def translate(self, document: Document) -> Self:
        """
        Synchronously translate .docx file.
        """
        doc, elements_to_translate, original_texts = self._pre_translate(document)
        if not original_texts:
            # Use i18n logger for translation messages
            from collabtrans.logger.logger import i18n_logger
            i18n_logger.info("backend.translation.task.no_text_found")
            output_stream = BytesIO()
            doc.save(output_stream)
            document.content = output_stream.getvalue()
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # Call translation agent
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        # Write translation results back to document
        document.content = self._after_translate(doc, elements_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        Asynchronously translate .docx file.
        """
        doc, elements_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)
        if not original_texts:
            # Use i18n logger for translation messages
            from collabtrans.logger.logger import i18n_logger
            i18n_logger.info("backend.translation.task.no_text_found")
            # Correctly save and return in async environment
            output_stream = BytesIO()
            doc.save(output_stream)
            document.content = output_stream.getvalue()
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # Asynchronously call translation agent
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # Write translation results back to document
        document.content = await asyncio.to_thread(self._after_translate, doc, elements_to_translate, translated_texts,
                                                   original_texts)
        return self
