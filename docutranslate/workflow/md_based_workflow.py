import asyncio
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Self, Tuple, Any

from docutranslate.cacher import md_based_convert_cacher
from docutranslate.global_values.conditional_import import DOCLING_EXIST

if DOCLING_EXIST:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig, ConverterDocling
from docutranslate.converter.x2md.converter_identity import ConverterIdentity
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig, ConverterMineru
from docutranslate.converter.x2md.base import X2MarkdownConverterConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig, MD2HTMLExporter
from docutranslate.exporter.md.md2md_exporter import MD2MDExporter
from docutranslate.exporter.md.md2mdzip_exporter import MD2MDZipExporter
from docutranslate.exporter.md.types import ConvertEnginType
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import MDFormatsExportable, HTMLExportable
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig, MDTranslator


@dataclass(kw_only=True)
class MarkdownBasedWorkflowConfig(WorkflowConfig):
    # X2MarkdownConverterConfig
    convert_engine: ConvertEnginType | None
    formula: bool = True
    # ConverterDoclingConfig
    code: bool = True
    artifact: Path | None = None
    # ConverterMineruConfig
    mineru_token: str
    # MDTranslatorConfig
    base_url: str
    api_key: str
    model_id: str
    to_lang: str
    custom_prompt: str | None = None
    temperature: float = 0.7
    timeout: int = 2000
    chunk_size: int = 3000
    concurrent: int = 30
    # MD2HTMLExporterConfig
    cdn: bool = True
    # general
    logger: Logger | None = None


class MarkdownBasedWorkflow(Workflow, HTMLExportable, MDFormatsExportable):
    def __init__(self, config: MarkdownBasedWorkflowConfig):
        super().__init__(config=config)
        self._converter_factory: dict[ConvertEnginType, Tuple[Any, Any]] = {
            "mineru": (ConverterMineru, ConverterMineruConfig),
        }
        if DOCLING_EXIST:
            self._converter_factory["docling"] = (ConverterDocling, ConverterDoclingConfig)
        self.x2markdown_converter_config:X2MarkdownConverterConfig|None
        if config.convert_engine is None:
            self.converter_config=None
        elif config.convert_engine== "mineru":
            self.converter_config = ConverterMineruConfig(formula=config.formula,
                                                          mineru_token=config.mineru_token)
        elif DOCLING_EXIST and config.convert_engine== "docling":
            self.converter_config = ConverterDoclingConfig(code=config.code,
                                                           formula=config.formula,
                                                           artifact=config.artifact)
        self.translator_config = MDTranslatorConfig(base_url=config.base_url,
                                                    api_key=config.api_key,
                                                    model_id=config.model_id,
                                                    to_lang=config.to_lang,
                                                    custom_prompt=config.custom_prompt,
                                                    temperature=config.temperature,
                                                    timeout=config.timeout,
                                                    chunk_size=config.chunk_size,
                                                    concurrent=config.concurrent,
                                                    )
        self.md2html_exporter_config = MD2HTMLExporterConfig(cdn=config.cdn)
        self.convert_engine=config.convert_engine

    def _get_document_md(self,convert_engin:ConvertEnginType|None,convert_config:X2MarkdownConverterConfig):
        if self.document_original is None:
            raise RuntimeError("file has not been read yet. Call read_path or read_bytes first.")
        # 获取缓存的解析后文件
        document_cached = md_based_convert_cacher.get_cached_result(self.document_original, convert_engin,
                                                                    convert_config)
        # 获取解析文件
        if document_cached:
            document_md = document_cached
        else:
            if convert_engin is None or self.document_original.suffix == ".md":
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
        convert_engin,convert_config=self.convert_engine,self.converter_config
        translator_config=self.translator_config
        document_md = self._get_document_md(convert_engin,convert_config)
        # 翻译解析后文件
        translator = MDTranslator(translator_config)
        translator.translate(document_md)
        self.document_translated = document_md
        return self

    async def translate_async(self) -> Self:
        convert_engin,convert_config=self.convert_engine,self.converter_config
        translator_config=self.translator_config
        document_md = await asyncio.to_thread(self._get_document_md, convert_engin, convert_config)
        # 翻译解析后文件
        translator = MDTranslator(translator_config)
        await translator.translate_async(document_md)
        self.document_translated = document_md
        return self

    def export_to_html(self, export_config: MD2HTMLExporterConfig | None = None) -> str:
        export_config=export_config or self.md2html_exporter_config
        docu = self._export(MD2HTMLExporter(export_config))
        return docu.content.decode()

    def export_to_markdown(self, export_config: X2MarkdownConverterConfig | None = None) -> str:
        docu = self._export(MD2MDExporter())
        return docu.content.decode()

    def export_to_markdown_zip(self, export_config: X2MarkdownConverterConfig | None = None) -> bytes:
        docu = self._export(MD2MDZipExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     export_config: MD2HTMLExporterConfig | None = None) -> Self:
        export_config = export_config or self.md2html_exporter_config
        self._save(exporter=MD2HTMLExporter(config=export_config), name=name, output_dir=output_dir)
        return self

    def save_as_markdown(self, name: str = None, output_dir: Path | str = "./output",
                         export_config=None) -> Self:

        self._save(exporter=MD2MDExporter(), name=name, output_dir=output_dir)
        return self

    def save_as_markdown_zip(self, name: str = None, output_dir: Path | str = "./output",
                             export_config=None) -> Self:

        self._save(exporter=MD2MDZipExporter(), name=name, output_dir=output_dir)
        return self
