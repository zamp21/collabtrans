# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Self, Tuple, Type

from collabtrans.cacher import md_based_convert_cacher
from collabtrans.exporter.base import ExporterConfig
from collabtrans.global_values.conditional_import import DOCLING_EXIST
from collabtrans.glossary.glossary import Glossary
from collabtrans.ir.document import Document
from collabtrans.ir.markdown_document import MarkdownDocument

if DOCLING_EXIST:
    from collabtrans.converter.x2md.converter_docling import ConverterDoclingConfig, ConverterDocling
from collabtrans.converter.converter_identity import ConverterIdentity
from collabtrans.converter.x2md.converter_mineru import ConverterMineruConfig, ConverterMineru
from collabtrans.converter.x2md.base import X2MarkdownConverterConfig, X2MarkdownConverter
from collabtrans.exporter.md.md2html_exporter import MD2HTMLExporterConfig, MD2HTMLExporter
from collabtrans.exporter.md.md2md_exporter import MD2MDExporter
from collabtrans.exporter.md.md2mdzip_exporter import MD2MDZipExporter
from collabtrans.exporter.md.types import ConvertEngineType
from collabtrans.workflow.base import Workflow, WorkflowConfig
from collabtrans.workflow.interfaces import MDFormatsExportable, HTMLExportable
from collabtrans.translator.ai_translator.md_translator import MDTranslatorConfig, MDTranslator


@dataclass(kw_only=True)
class MarkdownBasedWorkflowConfig(WorkflowConfig):
    convert_engine: ConvertEngineType
    converter_config: X2MarkdownConverterConfig | None
    translator_config: MDTranslatorConfig
    html_exporter_config: MD2HTMLExporterConfig


class MarkdownBasedWorkflow(Workflow[MarkdownBasedWorkflowConfig, Document, MarkdownDocument],
                            HTMLExportable[MD2HTMLExporterConfig],
                            MDFormatsExportable[ExporterConfig]):
    _converter_factory: dict[
        ConvertEngineType, Tuple[Type[X2MarkdownConverter|ConverterIdentity], Type[X2MarkdownConverterConfig]] | None] = {
        "mineru": (ConverterMineru, ConverterMineruConfig),
        "identity": (ConverterIdentity, None)
    }
    if DOCLING_EXIST:
        _converter_factory["docling"] = (ConverterDocling, ConverterDoclingConfig)

    def __init__(self, config: MarkdownBasedWorkflowConfig):
        super().__init__(config=config)
        self.convert_engine = config.convert_engine
        if config.logger:
            for sub_config in [self.config.converter_config, self.config.translator_config,
                               self.config.html_exporter_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _get_document_md(self, convert_engin: ConvertEngineType, convert_config: X2MarkdownConverterConfig):
        if self.document_original is None:
            raise RuntimeError("File has not been read yet. Call read_path or read_bytes first.")

        # 获取缓存的解析后文件
        document_cached = md_based_convert_cacher.get_cached_result(self.document_original, convert_engin,
                                                                    convert_config)
        if document_cached:
            self.attachment.add_document("md_cached",document_cached)
            return document_cached

        # 未缓存则解析文件
        if convert_engin in self._converter_factory:
            converter_class, config_class = self._converter_factory[convert_engin]
            if config_class and not isinstance(convert_config, config_class):
                raise TypeError(
                    f"The correct convert_config was not passed. It should be of type {config_class.__name__}, but it is currently of type {type(convert_config).__name__}.")
            converter = converter_class(convert_config)
        else:
            raise ValueError(f"不存在{convert_engin}解析引擎")
        document_md = converter.convert(self.document_original)
        if hasattr(converter,"attachments"):
            for attachment in converter.attachments:
                self.attachment.add_attachment(attachment)
        # 获取缓存解析后文件
        md_based_convert_cacher.cache_result(document_md, self.document_original, convert_engin, convert_config)

        return document_md

    def _pre_translate(self, document: Document):
        convert_engine: ConvertEngineType = "identity" if document.suffix == ".md" else self.convert_engine
        convert_config = self.config.converter_config
        translator_config = self.config.translator_config
        translator = MDTranslator(translator_config)
        return convert_engine, convert_config, translator_config, translator

    def translate(self) -> Self:
        convert_engine, convert_config, translator_config, translator = self._pre_translate(self.document_original)
        document_md = self._get_document_md(convert_engine, convert_config)
        translator.translate(document_md)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document_md
        return self

    async def translate_async(self) -> Self:
        convert_engine, convert_config, translator_config, translator = self._pre_translate(self.document_original)
        document_md = await asyncio.to_thread(self._get_document_md, convert_engine, convert_config)
        await translator.translate_async(document_md)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document_md
        return self

    def export_to_html(self, config: MD2HTMLExporterConfig | None = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(MD2HTMLExporter(config))
        return docu.content.decode()

    def export_to_markdown(self, config: ExporterConfig | None = None) -> str:
        docu = self._export(MD2MDExporter())
        return docu.content.decode()

    def export_to_markdown_zip(self, config: ExporterConfig | None = None) -> bytes:
        docu = self._export(MD2MDZipExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: MD2HTMLExporterConfig | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=MD2HTMLExporter(config=config), name=name, output_dir=output_dir)
        return self

    def save_as_markdown(self, name: str = None, output_dir: Path | str = "./output",
                         _: ExporterConfig | None = None) -> Self:

        self._save(exporter=MD2MDExporter(), name=name, output_dir=output_dir)
        return self

    def save_as_markdown_zip(self, name: str = None, output_dir: Path | str = "./output",
                             _: ExporterConfig | None = None) -> Self:

        self._save(exporter=MD2MDZipExporter(), name=name, output_dir=output_dir)
        return self
