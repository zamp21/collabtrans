# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from collabtrans.exporter.base import ExporterConfig
from collabtrans.exporter.docx.docx2docx_exporter import Docx2DocxExporter
from collabtrans.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig, Docx2HTMLExporter
from collabtrans.glossary.glossary import Glossary
from collabtrans.ir.document import Document
from collabtrans.translator.ai_translator.docx_translator import DocxTranslatorConfig, DocxTranslator
from collabtrans.workflow.base import Workflow, WorkflowConfig
from collabtrans.workflow.interfaces import HTMLExportable, DocxExportable


@dataclass(kw_only=True)
class DocxWorkflowConfig(WorkflowConfig):
    translator_config: DocxTranslatorConfig
    html_exporter_config: Docx2HTMLExporterConfig
    translate_headers_footers: bool = True
    translate_textboxes_sdts: bool = True


class DocxWorkflow(Workflow[DocxWorkflowConfig, Document, Document], HTMLExportable[Docx2HTMLExporterConfig],
                   DocxExportable[ExporterConfig]):
    def __init__(self, config: DocxWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _is_toc_content(self, text: str) -> bool:
        """判断文本内容是否为目录"""
        if not text:
            return False
        
        lines = text.split('\n')
        if len(lines) < 3:  # 少于3行不太可能是目录
            return False
        
        # 检查目录关键词
        toc_indicators = ['目录', 'contents', 'table of contents', 'toc']
        if any(indicator in text.lower() for indicator in toc_indicators):
            return True
        
        # 检查编号模式
        numbered_entries = 0
        for line in lines:
            line = line.strip()
            if line and (line[-1].isdigit() or '...' in line):
                numbered_entries += 1
        
        # 如果超过一半的行看起来像编号的目录条目
        if numbered_entries >= len(lines) * 0.5:
            return True
        
        return False

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = DocxTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        
        # 翻译文档主体内容
        translator.translate(document)
        
        # 翻译页眉页脚（如果启用）
        if self.config.translate_headers_footers:
            from collabtrans.converter.x2md.docx_extras import extract_headers_footers, apply_headers_footers
            try:
                # 在当前文档内容上提取页眉页脚，避免覆盖正文翻译
                items = extract_headers_footers(document.content)
                if items:
                    self.logger.info(f"提取到 {len(items)} 个页眉页脚文本")
                    # 批量翻译
                    texts = [text for _, text in items]
                    if translator.translate_agent:
                        translated_list = translator.translate_agent.send_segments(texts, translator.chunk_size)
                    else:
                        translated_list = texts
                    translated_map = {}
                    for (key, _), translated_text in zip(items, translated_list):
                        if translated_text and str(translated_text).strip():
                            translated_map[key] = translated_text
                    if translated_map:
                        # 在当前文档内容上回写
                        new_bytes = apply_headers_footers(document.content, translated_map)
                        document.content = new_bytes
                        self.logger.info("页眉页脚翻译完成")
            except Exception as e:
                self.logger.warning(f"页眉页脚翻译失败: {e}")
        
        # 翻译文本框和SDT（如果启用）
        if self.config.translate_textboxes_sdts:
            from collabtrans.converter.x2md.docx_extras import extract_text_in_textboxes_and_sdts, apply_text_in_textboxes_and_sdts
            try:
                items = extract_text_in_textboxes_and_sdts(document.content)
                if items:
                    self.logger.info(f"提取到 {len(items)} 个文本框/SDT文本")
                    
                    # 过滤掉TOC内容
                    filtered_items = []
                    skipped_toc_count = 0
                    
                    for i, (key, text) in enumerate(items):
                        # 检查是否为TOC内容
                        if self._is_toc_content(text):
                            self.logger.info(f"  [{i}] {key}: 跳过TOC内容 - {text[:50]}...")
                            skipped_toc_count += 1
                        else:
                            filtered_items.append((key, text))
                            self.logger.info(f"  [{i}] {key}: {text[:50]}...")
                    
                    if skipped_toc_count > 0:
                        self.logger.info(f"跳过了 {skipped_toc_count} 个TOC内容")
                    
                    if filtered_items:
                        texts = [text for _, text in filtered_items]
                        if translator.translate_agent:
                            translated_list = translator.translate_agent.send_segments(texts, translator.chunk_size)
                        else:
                            translated_list = texts
                        translated_map = {}
                        for (key, _), translated_text in zip(filtered_items, translated_list):
                            if translated_text and str(translated_text).strip():
                                translated_map[key] = translated_text
                        if translated_map:
                            new_bytes = apply_text_in_textboxes_and_sdts(document.content, translated_map)
                            document.content = new_bytes
                            self.logger.info("文本框和SDT翻译完成")
                    else:
                        self.logger.info("所有SDT内容都是TOC，跳过翻译")
                else:
                    self.logger.info("未找到文本框/SDT文本")
            except Exception as e:
                self.logger.warning(f"文本框/SDT翻译失败: {e}")
        
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        
        # 翻译文档主体内容
        await translator.translate_async(document)
        
        # 翻译页眉页脚（如果启用）
        if self.config.translate_headers_footers:
            from collabtrans.converter.x2md.docx_extras import extract_headers_footers, apply_headers_footers
            try:
                # 在当前文档内容上提取页眉页脚，避免覆盖正文翻译
                items = extract_headers_footers(document.content)
                if items:
                    self.logger.info(f"提取到 {len(items)} 个页眉页脚文本")
                    # 批量翻译（异步）
                    texts = [text for _, text in items]
                    if translator.translate_agent:
                        translated_list = await translator.translate_agent.send_segments_async(texts, translator.chunk_size)
                    else:
                        translated_list = texts
                    translated_map = {}
                    for (key, _), translated_text in zip(items, translated_list):
                        if translated_text and str(translated_text).strip():
                            translated_map[key] = translated_text
                    if translated_map:
                        # 在当前文档内容上回写
                        new_bytes = apply_headers_footers(document.content, translated_map)
                        document.content = new_bytes
                        self.logger.info("页眉页脚翻译完成")
            except Exception as e:
                self.logger.warning(f"页眉页脚翻译失败: {e}")
        
        # 翻译文本框和SDT（如果启用）
        if self.config.translate_textboxes_sdts:
            from collabtrans.converter.x2md.docx_extras import extract_text_in_textboxes_and_sdts, apply_text_in_textboxes_and_sdts
            try:
                items = extract_text_in_textboxes_and_sdts(document.content)
                if items:
                    self.logger.info(f"提取到 {len(items)} 个文本框/SDT文本")
                    
                    # 过滤掉TOC内容
                    filtered_items = []
                    skipped_toc_count = 0
                    
                    for i, (key, text) in enumerate(items):
                        # 检查是否为TOC内容
                        if self._is_toc_content(text):
                            self.logger.info(f"  [{i}] {key}: 跳过TOC内容 - {text[:50]}...")
                            skipped_toc_count += 1
                        else:
                            filtered_items.append((key, text))
                            self.logger.info(f"  [{i}] {key}: {text[:50]}...")
                    
                    if skipped_toc_count > 0:
                        self.logger.info(f"跳过了 {skipped_toc_count} 个TOC内容")
                    
                    if filtered_items:
                        texts = [text for _, text in filtered_items]
                        if translator.translate_agent:
                            translated_list = await translator.translate_agent.send_segments_async(texts, translator.chunk_size)
                        else:
                            translated_list = texts
                        translated_map = {}
                        for (key, _), translated_text in zip(filtered_items, translated_list):
                            if translated_text and str(translated_text).strip():
                                translated_map[key] = translated_text
                        if translated_map:
                            # 应用翻译后的文本框和SDT
                            new_bytes = apply_text_in_textboxes_and_sdts(document.content, translated_map)
                            document.content = new_bytes
                            self.logger.info("文本框和SDT翻译完成")
                    else:
                        self.logger.info("所有SDT内容都是TOC，跳过翻译")
                else:
                    self.logger.info("未找到文本框/SDT文本")
            except Exception as e:
                self.logger.warning(f"文本框/SDT翻译失败: {e}")
        
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    def export_to_html(self, config: Docx2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Docx2HTMLExporter(config))
        return docu.content.decode()

    def export_to_docx(self, _: ExporterConfig | None = None) -> bytes:
        docu = self._export(Docx2DocxExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Docx2HTMLExporter | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Docx2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_docx(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Docx2DocxExporter(), name=name, output_dir=output_dir)
        return self
