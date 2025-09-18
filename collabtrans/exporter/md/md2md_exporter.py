# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from collabtrans.exporter.md.base import MDExporter
from collabtrans.ir.markdown_document import MarkdownDocument, Document


class MD2MDExporter(MDExporter):

    def export(self, document: MarkdownDocument) -> Document:
        return Document.from_bytes(suffix=".md", content=document.content, stem=document.stem)
