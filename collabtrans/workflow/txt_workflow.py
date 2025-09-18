# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from collabtrans.exporter.base import ExporterConfig
from collabtrans.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig, TXT2HTMLExporter
from collabtrans.exporter.txt.txt2txt_exporter import TXT2TXTExporter
from collabtrans.glossary.glossary import Glossary
from collabtrans.ir.document import Document
from collabtrans.translator.ai_translator.txt_translator import TXTTranslatorConfig, TXTTranslator
from collabtrans.workflow.base import Workflow, WorkflowConfig
from collabtrans.workflow.interfaces import HTMLExportable, TXTExportable


@dataclass(kw_only=True)
class TXTWorkflowConfig(WorkflowConfig):
    translator_config: TXTTranslatorConfig
    html_exporter_config: TXT2HTMLExporterConfig


class TXTWorkflow(Workflow[TXTWorkflowConfig, Document, Document], HTMLExportable[TXT2HTMLExporterConfig],
                  TXTExportable[ExporterConfig]):
    def __init__(self, config: TXTWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self,document_original:Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = TXTTranslator(translate_config)
        return document,translator


    def translate(self) -> Self:
        document, translator=self._pre_translate(self.document_original)
        translator.translate(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    async def translate_async(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
        await translator.translate_async(document)
        if translator.glossary_dict_gen:
            self.attachment.add_document("glossary", Glossary.glossary_dict2csv(translator.glossary_dict_gen))
        self.document_translated = document
        return self

    def export_to_html(self, config: TXT2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(TXT2HTMLExporter(config))
        return docu.content.decode()

    def export_to_txt(self, _: ExporterConfig | None = None) -> str:
        docu = self._export(TXT2TXTExporter())
        return docu.content.decode()

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: TXT2HTMLExporterConfig | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=TXT2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_txt(self, name: str = None, output_dir: Path | str = "./output",
                    _: ExporterConfig | None = None) -> Self:
        self._save(exporter=TXT2TXTExporter(), name=name, output_dir=output_dir)
        return self
