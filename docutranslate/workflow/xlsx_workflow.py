from dataclasses import dataclass
from pathlib import Path
from typing import Self

from docutranslate.exporter.base import ExporterConfig
from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig, Xlsx2HTMLExporter
from docutranslate.exporter.xlsx.xlsx2xlsx_exporter import Xlsx2XlsxExporter
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig, XlsxTranslator
from docutranslate.workflow.base import Workflow, WorkflowConfig
from docutranslate.workflow.interfaces import HTMLExportable, XlsxExportable


@dataclass(kw_only=True)
class XlsxWorkflowConfig(WorkflowConfig):
    translator_config: XlsxTranslatorConfig
    html_exporter_config: Xlsx2HTMLExporterConfig


class XlsxWorkflow(Workflow[XlsxWorkflowConfig, Document, Document], HTMLExportable[Xlsx2HTMLExporterConfig],
                   XlsxExportable[ExporterConfig]):
    def __init__(self, config: XlsxWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = XlsxTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        translator.translate(document)
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        await translator.translate_async(document)
        self.document_translated = document
        return self

    def export_to_html(self, config: Xlsx2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Xlsx2HTMLExporter(config))
        return docu.content.decode()

    def export_to_xlsx(self, _: ExporterConfig | None = None) -> bytes:
        docu = self._export(Xlsx2XlsxExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Xlsx2HTMLExporter | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Xlsx2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_xlsx(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Xlsx2XlsxExporter(), name=name, output_dir=output_dir)
        return self
