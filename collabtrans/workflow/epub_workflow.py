# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from collabtrans.exporter.base import ExporterConfig
from collabtrans.exporter.epub.epub2epub_exporter import Epub2EpubExporter
from collabtrans.exporter.epub.epub2html_exporter import Epub2HTMLExporterConfig, Epub2HTMLExporter
from collabtrans.glossary.glossary import Glossary

from collabtrans.ir.document import Document
from collabtrans.translator.ai_translator.epub_translator import EpubTranslatorConfig, EpubTranslator
from collabtrans.workflow.base import Workflow, WorkflowConfig
from collabtrans.workflow.interfaces import HTMLExportable, EpubExportable


@dataclass(kw_only=True)
class EpubWorkflowConfig(WorkflowConfig):
    translator_config: EpubTranslatorConfig
    html_exporter_config: Epub2HTMLExporterConfig


class EpubWorkflow(Workflow[EpubWorkflowConfig, Document, Document], HTMLExportable[Epub2HTMLExporterConfig],
                   EpubExportable[ExporterConfig]):
    def __init__(self, config: EpubWorkflowConfig):
        super().__init__(config=config)
        if config.logger:
            for sub_config in [self.config.translator_config]:
                if sub_config:
                    sub_config.logger = config.logger

    def _pre_translate(self, document_original: Document):
        document = document_original.copy()
        translate_config = self.config.translator_config
        translator = EpubTranslator(translate_config)
        return document, translator

    def translate(self) -> Self:
        document, translator = self._pre_translate(self.document_original)
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

    def export_to_html(self, config: Epub2HTMLExporterConfig = None) -> str:
        config = config or self.config.html_exporter_config
        docu = self._export(Epub2HTMLExporter(config))
        return docu.content.decode()

    def export_to_epub(self, _: ExporterConfig | None = None) -> bytes:
        docu = self._export(Epub2EpubExporter())
        return docu.content

    def save_as_html(self, name: str = None, output_dir: Path | str = "./output",
                     config: Epub2HTMLExporter | None = None) -> Self:
        config = config or self.config.html_exporter_config
        self._save(exporter=Epub2HTMLExporter(config), name=name, output_dir=output_dir)
        return self

    def save_as_epub(self, name: str = None, output_dir: Path | str = "./output",
                     _: ExporterConfig | None = None) -> Self:
        self._save(exporter=Epub2EpubExporter(), name=name, output_dir=output_dir)
        return self
