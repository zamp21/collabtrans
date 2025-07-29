import asyncio
from pathlib import Path
from typing import Self, Literal, overload, TYPE_CHECKING

from docutranslate.cacher import md_based_convert_cacher
from docutranslate.global_values.conditional_import import DOCLING_EXIST

if DOCLING_EXIST or TYPE_CHECKING:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig, ConverterDocling
from docutranslate.converter.x2md.converter_identity import ConverterIdentity
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig, ConverterMineru
from docutranslate.converter.x2md.interfaces import X2MarkdownConverter
from docutranslate.exporter.md2x.md2html_exporter import MD2HTMLExportConfig, MD2HTMLExporter
from docutranslate.exporter.md2x.md2md_exporter import MD2MDExportConfig, MD2MDExporter
from docutranslate.exporter.md2x.md2mdzip_exporter import MD2MDZIPExportConfig, MD2MDZipExporter
from docutranslate.exporter.md2x.types import x2md_convert_config_type, convert_engin_type
from docutranslate.manager.base_manager import BaseManager
from docutranslate.manager.interfaces import MDFormatsExportable, HTMLExportable
from docutranslate.translater.md_translator import MDTranslateConfig, MDTranslator


class MarkdownBasedManager(BaseManager, HTMLExportable, MDFormatsExportable):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if DOCLING_EXIST or TYPE_CHECKING:
            self._converter_factory: dict[str:tuple[X2MarkdownConverter, x2md_convert_config_type]] = {
                "mineru": (ConverterMineru, ConverterMineruConfig),
                "docling": (ConverterDocling, ConverterDoclingConfig)
            }
        else:
            self._converter_factory: dict[str:tuple[X2MarkdownConverter, x2md_convert_config_type]] = {
                "mineru": (ConverterMineru, ConverterMineruConfig),
            }

    def _get_document_md(self, convert_engin: convert_engin_type | None,
                         convert_config: x2md_convert_config_type | None):
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
                converter = converter_class(convert_config, logger=self.logger)
            else:
                raise ValueError(f"不存在{convert_engin}解析引擎")
            document_md = converter.convert(self.document_original)
            # 获取缓存解析后文件
            md_based_convert_cacher.cache_result(document_md, self.document_original, convert_engin, convert_config)
        return document_md

    @overload
    def translate(self, convert_engin: None,
                  convert_config: x2md_convert_config_type | None, translate_config: MDTranslateConfig) -> Self:
        ...

    @overload
    def translate(self, convert_engin: Literal["docling"],
                  convert_config: "ConverterDoclingConfig", translate_config: MDTranslateConfig) -> Self:
        ...

    @overload
    def translate(self, convert_engin: Literal["mineru"],
                  convert_config: ConverterMineruConfig, translate_config: MDTranslateConfig) -> Self:
        ...

    def translate(self, convert_engin: convert_engin_type | None,
                  convert_config: x2md_convert_config_type | None,
                  translate_config: MDTranslateConfig) -> Self:
        document_md = self._get_document_md(convert_engin, convert_config)
        # 翻译解析后文件
        translator = MDTranslator(translate_config)
        translator.translate(document_md)
        self.document_translated = document_md
        return self

    async def translate_async(self, convert_engin: Literal["mineru", "docling"] | None,
                              convert_config: x2md_convert_config_type | None,
                              translate_config: MDTranslateConfig) -> Self:

        document_md = await asyncio.to_thread(self._get_document_md, convert_engin, convert_config)
        # 翻译解析后文件
        translator = MDTranslator(translate_config)
        await translator.translate_async(document_md)
        self.document_translated = document_md
        return self

    def export_to_html(self, export_config: MD2HTMLExportConfig | None = None) -> str:
        docu = self._export(MD2HTMLExporter(export_config))
        return docu.content.decode()

    def export_to_markdown(self, export_config: MD2MDExportConfig | None = None) -> str:
        docu = self._export(MD2MDExporter())
        return docu.content.decode()

    def export_to_markdown_zip(self, export_config: MD2MDZIPExportConfig | None = None) -> bytes:
        docu = self._export(MD2MDZipExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     export_config: MD2HTMLExportConfig | None = None) -> Self:
        self._save(exporter=MD2HTMLExporter(), name=name, output_dir=output_dir)
        return self

    def save_as_markdown(self, name: str = None, output_dir: Path | str = "./output",
                         export_config: MD2MDExportConfig | None = None) -> Self:

        self._save(exporter=MD2MDExporter(), name=name, output_dir=output_dir)
        return self

    def save_as_markdown_zip(self, name: str = None, output_dir: Path | str = "./output",
                             export_config: MD2MDZIPExportConfig | None = None) -> Self:

        self._save(exporter=MD2MDZipExporter(), name=name, output_dir=output_dir)
        return self
