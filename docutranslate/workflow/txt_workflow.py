from pathlib import Path
from typing import Self

from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig, TXT2HTMLExporter
from docutranslate.exporter.txt.txt2txt_exporter import TXT2TXTExporter
from docutranslate.workflow.base import Workflow
from docutranslate.workflow.interfaces import HTMLExportable, TXTExportable
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig, TXTTranslator



class TXTWorkflow(Workflow, HTMLExportable, TXTExportable):

    def translate(self, translate_config: TXTTranslatorConfig) -> Self:
        document = self.document_original.copy()
        # 翻译解析后文件
        translator = TXTTranslator(translate_config)
        translator.translate(document)
        self.document_translated = document
        return self

    async def translate_async(self, translate_config: TXTTranslatorConfig) -> Self:
        document = self.document_original.copy()
        # 翻译解析后文件
        translator = TXTTranslator(translate_config)
        await translator.translate_async(document)
        self.document_translated = document
        return self

    def export_to_html(self, export_config: TXT2HTMLExporterConfig=None) -> str:
        docu = self._export(TXT2HTMLExporter(export_config))
        return docu.content.decode()

    def export_to_txt(self) -> str:
        docu = self._export(TXT2TXTExporter())
        return docu.content.decode()

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     export_config: TXT2HTMLExporterConfig | None = None) -> Self:
        self._save(exporter=TXT2HTMLExporter(export_config), name=name, output_dir=output_dir)
        return self

    def save_as_txt(self, name: str = None, output_dir: Path | str = "./output", ) -> Self:
        self._save(exporter=TXT2TXTExporter(), name=name, output_dir=output_dir)
        return self
