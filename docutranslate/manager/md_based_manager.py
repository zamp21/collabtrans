import asyncio
from pathlib import Path
from typing import Self, Literal, overload

from docutranslate.cacher import md_based_convert_cacher
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig, ConverterDocling
from docutranslate.converter.x2md.converter_identity import ConverterIdentity
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig, ConverterMineru
from docutranslate.exporter.md2x.md2html_exporter import MD2HTMLExportConfig, MD2HTMLExporter
from docutranslate.exporter.md2x.md2md_exporter import MD2MDExportConfig, MD2MDExporter
from docutranslate.exporter.md2x.types import x2md_convert_config_type
from docutranslate.manager.base_manager import BaseManager
from docutranslate.manager.interfaces import HTMLExportable, MDExportable
from docutranslate.translater.md_translator import MDTranslateConfig, MDTranslator


class MarkdownBasedManager(BaseManager, HTMLExportable, MDExportable):

    def support_export_format(self) -> list[str]:
        return [".md",".html",".zip"]

    def _get_document_md(self, convert_engin, convert_config):
        if self.document_original is None:
            raise RuntimeError("file has not been read yet. Call read_path or read_bytes first.")
        # 获取缓存的解析后文件
        document_cached = md_based_convert_cacher.get_cached_result(self.document_original, convert_engin,
                                                                    convert_config)
        # 获取解析文件
        if document_cached:
            document_md = document_cached
        else:
            if convert_engin is None:
                converter = ConverterIdentity()
            elif convert_engin == "mineru":
                if not isinstance(convert_config, ConverterMineruConfig):
                    raise RuntimeError(f"未传入正确的convert_config，应传入{ConverterMineruConfig}")
                converter = ConverterMineru(convert_config, logger=self.logger)
            elif convert_engin == "docling":
                if not isinstance(convert_config, ConverterDoclingConfig):
                    raise RuntimeError(f"未传入正确的convert_config，应传入{ConverterDoclingConfig}")
                converter = ConverterDocling(convert_config, logger=self.logger)
            else:
                raise ValueError(f"不存在{convert_engin}解析引擎")
            document_md = converter.convert(self.document_original)
            # 获取缓存解析后文件
            md_based_convert_cacher.cache_result(document_md, self.document_original, convert_engin, convert_config)
        return document_md

    @overload
    def translate(self, convert_engin: None,
                  convert_config: None, translate_config: MDTranslateConfig) -> Self:
        ...

    @overload
    def translate(self, convert_engin: Literal["docling"],
                  convert_config: ConverterDoclingConfig, translate_config: MDTranslateConfig) -> Self:
        ...

    @overload
    def translate(self, convert_engin: Literal["mineru"],
                  convert_config: ConverterMineruConfig, translate_config: MDTranslateConfig) -> Self:
        ...

    def translate(self, convert_engin: Literal["mineru", "docling"] | None,
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
        docu = self._export(MD2MDExporter(export_config))
        return docu.content.decode()

    def save_as_html(self, name: str = None, out_put_dir: Path | str = "./output",
                     export_config: MD2HTMLExportConfig | None = None) -> Self:
        self._save(exporter=MD2HTMLExporter(export_config), name=name, out_put_dir=out_put_dir)
        return self

    def save_as_markdown(self, name: str = None, out_put_dir: Path | str = "./output",
                         export_config: MD2MDExportConfig | None = None) -> Self:

        self._save(exporter=MD2MDExporter(export_config), name=name, out_put_dir=out_put_dir)
        return self
