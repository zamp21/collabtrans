# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from collabtrans.exporter.xlsx.base import XlsxExporter
from collabtrans.ir.document import Document


class Xlsx2XlsxExporter(XlsxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
