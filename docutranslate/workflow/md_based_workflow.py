import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Self, Tuple, Type

from docutranslate.cacher import md_based_convert_cacher
from docutranslate.exporter.base import ExporterConfig
from docutranslate.global_values.conditional_import import DOCLING_EXIST
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument

if DOCLING_EXIST:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig, ConverterDocling
from docutranslate.converter.x2md.converter_identity import ConverterIdentity
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig, ConverterMineru
from docutranslate.converter.x2md.base import X2MarkdownConverterConfig, X2MarkdownConverter
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig, MD2HTMLExporter
from docutranslate.exporter.md.md2md_exporter import MD2MDExporter
from docutranslate.exporter.md.md2mdzip_exporter import MD2MDZipExporter
from docutranslate.exporter.md.types import ConvertEnginType
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import MDFormatsExportable, HTMLExportable
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig, MDTranslator


@dataclass(kw_only=True)
class MarkdownBasedWorkflowConfig(WorkflowConfig):
    convert_engine: ConvertEnginType
    converter_config: X2MarkdownConverterConfig | None
    translator_config: MDTranslatorConfig
    html_exporter_config: MD2HTMLExporterConfig


class MarkdownBasedWorkflow(Workflow[MarkdownBasedWorkflowConfig, Document, MarkdownDocument], HTMLExportable,
                            MDFormatsExportable):
    def __init__(self, config: MarkdownBasedWorkflowConfig):
        super().__init__(config=config)
        self._converter_factory: dict[
            ConvertEnginType, Tuple[Type[X2MarkdownConverter], Type[X2MarkdownConverterConfig]] | None] = {
            "mineru": (ConverterMineru, ConverterMineruConfig),
            "identity": (ConverterIdentity, None)
        }
        if DOCLING_EXIST:
            self._converter_factory["docling"] = (ConverterDocling, ConverterDoclingConfig)
        self.convert_engine = config.convert_engine
        if config.logger:
            for sub_config in [self.config.converter_config, self.config.translator_config, self.config.html_exporter_config]:
                if sub_config and sub_config.logger is not None:
                    sub_config.logger = config.logger

    def _get_document_md(self, convert_engin: ConvertEnginType, convert_config: X2MarkdownConverterConfig):
        if self.document_original is None:
            raise RuntimeError("file has not been read yet. Call read_path or read_bytes first.")

        # 获取缓存的解析后文件
        document_cached = md_based_convert_cacher.get_cached_result(self.document_original, convert_engin,
                                                                    convert_config)
        # 获取解析文件
        if document_cached:
            document_md = document_cached
        else:
            if self.document_original.suffix == ".md":
                converter = ConverterIdentity()
            elif convert_engin in self._converter_factory:
                converter_class, config_class = self._converter_factory[convert_engin]
                if not isinstance(convert_config, config_class):
                    raise TypeError(
                        f"未传入正确的convert_config，应传入{config_class.__name__}类型，现为{type(convert_config).__name__}类型")
                converter = converter_class(convert_config)
            else:
                raise ValueError(f"不存在{convert_engin}解析引擎")
            document_md = converter.convert(self.document_original)
            # 获取缓存解析后文件
            md_based_convert_cacher.cache_result(document_md, self.document_original, convert_engin, convert_config)
        return document_md

    def translate(self) -> Self:
        convert_engin, convert_config = self.convert_engine, self.config.converter_config
        translator_config = self.config.translator_config
        document_md = self._get_document_md(convert_engin, convert_config)
        # 翻译解析后文件
        translator = MDTranslator(translator_config)
        translator.translate(document_md)
        self.document_translated = document_md
        return self

    async def translate_async(self) -> Self:
        convert_engin, convert_config = self.convert_engine, self.config.converter_config
        translator_config = self.config.translator_config
        document_md = await asyncio.to_thread(self._get_document_md, convert_engin, convert_config)
        # 翻译解析后文件
        translator = MDTranslator(translator_config)
        await translator.translate_async(document_md)
        self.document_translated = document_md
        return self

    def export_to_html(self, export_config: MD2HTMLExporterConfig | None = None) -> str:
        export_config = export_config or self.config.html_exporter_config
        docu = self._export(MD2HTMLExporter(export_config))
        return docu.content.decode()

    def export_to_markdown(self, config: ExporterConfig | None = None) -> str:
        docu = self._export(MD2MDExporter())
        return docu.content.decode()

    def export_to_markdown_zip(self, config: ExporterConfig | None = None) -> bytes:
        docu = self._export(MD2MDZipExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     export_config: MD2HTMLExporterConfig | None = None) -> Self:
        export_config = export_config or self.config.html_exporter_config
        self._save(exporter=MD2HTMLExporter(config=export_config), name=name, output_dir=output_dir)
        return self

    def save_as_markdown(self, name: str = None, output_dir: Path | str = "./output",
                         export_config: ExporterConfig | None = None) -> Self:

        self._save(exporter=MD2MDExporter(), name=name, output_dir=output_dir)
        return self

    def save_as_markdown_zip(self, name: str = None, output_dir: Path | str = "./output",
                             export_config: ExporterConfig | None = None) -> Self:

        self._save(exporter=MD2MDZipExporter(), name=name, output_dir=output_dir)
        return self
