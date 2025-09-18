# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from collabtrans.exporter.base import ExporterConfig
from collabtrans.exporter.html.base import HtmlExporter
from collabtrans.ir.document import Document


class Html2HtmlExporter(HtmlExporter):
    def __init__(self, config: ExporterConfig|None = None):
        super().__init__(config=config)

    def export(self, document: Document) -> Document:
        return Document.from_bytes(content=document.content, suffix=".html", stem=document.stem)
