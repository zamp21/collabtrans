# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from collabtrans.exporter.docx.base import DocxExporter
from collabtrans.ir.document import Document


class Docx2DocxExporter(DocxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
