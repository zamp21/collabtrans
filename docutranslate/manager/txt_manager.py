from pathlib import Path
from typing import Self

from docutranslate.exporter.txt2x.txt2html_exporter import TXT2HTMLExportConfig, TXT2HTMLExporter
from docutranslate.exporter.txt2x.txt2txt_exporter import TXT2TXTExporter
from docutranslate.manager.base_manager import BaseManager
from docutranslate.manager.interfaces import HTMLExportable, TXTExportable
from docutranslate.translater.txt_translator import TXTTranslateConfig, TXTTranslator



class TXTManager(BaseManager, HTMLExportable,TXTExportable):

    def translate(self, translate_config: TXTTranslateConfig) -> Self:
        document = self.document_original.copy()
        # 翻译解析后文件
        translator = TXTTranslator(translate_config)
        translator.translate(document)
        self.document_translated = document
        return self

    async def translate_async(self, translate_config: TXTTranslateConfig) -> Self:
        document = self.document_original.copy()
        # 翻译解析后文件
        translator = TXTTranslator(translate_config)
        await translator.translate_async(document)
        self.document_translated = document
        return self

    def export_to_html(self, export_config: TXT2HTMLExportConfig=None) -> str:
        docu = self._export(TXT2HTMLExporter(export_config))
        return docu.content.decode()

    def export_to_txt(self) -> str:
        docu = self._export(TXT2TXTExporter())
        return docu.content.decode()

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     export_config: TXT2HTMLExportConfig | None = None) -> Self:
        self._save(exporter=TXT2HTMLExporter(export_config), name=name, output_dir=output_dir)
        return self

    def save_as_txt(self, name: str = None, output_dir: Path | str = "./output", ) -> Self:
        self._save(exporter=TXT2TXTExporter(), name=name, output_dir=output_dir)
        return self
