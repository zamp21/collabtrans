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
        "Chinese": "Microsoft YaHei",  # Microsoft YaHei
        "Simplified Chinese": "Microsoft YaHei",
        "Traditional Chinese": "Microsoft JhengHei",  # Microsoft JhengHei
        
        # English
        "English": "Calibri",
        
        # Japanese
        "Japanese": "Yu Gothic",  # Yu Gothic
        "Japanese": "Yu Gothic",
        "Japanese": "Yu Gothic",
        
        # Korean
        "Korean": "Malgun Gothic",  # Malgun Gothic
        "한국어": "Malgun Gothic",
        "Korean": "Malgun Gothic",
        
        # Russian
        "Russian": "Times New Roman",  # Common Russian font
        "Русский": "Times New Roman",
        "Russian": "Times New Roman",
        
        # Arabic
        "Arabic": "Arial Unicode MS",  # Supports Arabic characters
        "العَرَبِيَّة": "Arial Unicode MS",
        "Arabic": "Arial Unicode MS",
        
        # Other European languages
        "Spanish": "Calibri",
        "Español": "Calibri",
        "Spanish": "Calibri",
        
        "French": "Calibri",
        "Français": "Calibri",
        "French": "Calibri",
        
        "German": "Calibri",
        "Deutsch": "Calibri",
        "German": "Calibri",
        
        "Portuguese": "Calibri",
        "Português": "Calibri",
        "Portuguese": "Calibri",
        
        # Vietnamese
        "Vietnamese": "Arial Unicode MS",  # Supports Vietnamese characters
        "tiếng Việt": "Arial Unicode MS",
        "Vietnamese": "Arial Unicode MS",
        
        # Hebrew
        "Hebrew": "Arial Unicode MS",  # Supports Hebrew characters
        "Hebrew": "Arial Unicode MS",
        "עברית": "Arial Unicode MS",
        
        # Thai
        "Thai": "Arial Unicode MS",  # Supports Thai characters
        "Thai": "Arial Unicode MS",
        "ไทย": "Arial Unicode MS",
        
        # Hindi
        "Hindi": "Arial Unicode MS",  # Supports Hindi characters
        "Hindi": "Arial Unicode MS",
        "हिन्दी": "Arial Unicode MS",
    }
    
    # Find matching font
    font = language_font_map.get(target_language)
    
    # If no matching font found, return default font
    if not font:
        # Intelligent selection based on language characteristics
        if any(char in target_language for char in ['Chinese', 'Chinese', 'Simplified', 'Traditional']):
            font = "Microsoft YaHei"
        elif any(char in target_language for char in ['Japanese', 'Japanese', 'Japanese']):
            font = "Yu Gothic"
        elif any(char in target_language for char in ['Korean', 'Korean', '한국어']):
            font = "Malgun Gothic"
        elif any(char in target_language for char in ['Russian', 'Russian', 'Русский']):
            font = "Times New Roman"
        elif any(char in target_language for char in ['Arabic', 'Arabic', 'العَرَبِيَّة']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['Vietnamese', 'Vietnamese', 'tiếng Việt']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['Hebrew', 'Hebrew', 'עברית']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['Thai', 'Thai', 'ไทย']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['Hindi', 'Hindi', 'हिन्दी']):
            font = "Arial Unicode MS"
        else:
            # Default to Calibri (suitable for most Latin alphabet languages)
            font = "Calibri"
    
    return font


@dataclass
class DocxTranslatorConfig(AiTranslatorConfig):
    """
    Configuration class for DocxTranslator.
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class DocxTranslator(AiTranslator):
    """
    Translator for .docx files.
    This version is optimized to handle mixed text and image paragraphs without losing images.
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
        [Refactored] Preprocess .docx file, extract text at Run level to avoid breaking images.
        :param document: Document object containing .docx file content.
        :return: A tuple containing:
                 - docx.Document object
                 - A list containing text block information (each element represents a group of consecutive text runs)
                 - A list containing all original texts to be translated
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
                    # Encounter image, treat previously accumulated text as a translation unit
                    if current_text_segment.strip():
                        elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                        original_texts.append(current_text_segment)
                    # Reset accumulator
                    current_text_segment = ""
                    current_runs = []
                else:
                    # Accumulate text run
                    current_runs.append(run)
                    current_text_segment += run.text

            # Process the last text block at the end of the paragraph
            if current_text_segment.strip():
                elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                original_texts.append(current_text_segment)

        # Traverse all paragraphs
        for para in doc.paragraphs:
            process_paragraph(para)

        # Traverse all tables
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        process_paragraph(para)

        return doc, elements_to_translate, original_texts

    def _after_translate(self, doc: DocumentObject, elements_to_translate: List[Dict[str, Any]],
                         translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        [Refactored] Write translated text back to corresponding text runs, preserving images and styles.
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
                    if any(char in self.config.to_lang for char in ['Chinese', 'Chinese', 'Simplified', 'Traditional']):
                        # Chinese fallback fonts
                        fallback_fonts = ['SimSun', 'SimHei', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['Japanese', 'Japanese', 'Japanese']):
                        # Japanese fallback fonts
                        fallback_fonts = ['MS Gothic', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['Korean', 'Korean', '한국어']):
                        # Korean fallback fonts
                        fallback_fonts = ['Gulim', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['Russian', 'Russian', 'Русский']):
                        # Russian fallback fonts
                        fallback_fonts = ['Times New Roman', 'Arial', 'Calibri']
                    elif any(char in self.config.to_lang for char in ['Arabic', 'Arabic', 'العَرَبِيَّة']):
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
