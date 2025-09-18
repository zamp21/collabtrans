# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from collabtrans.exporter.txt.base import TXTExporter
from collabtrans.exporter.xlsx.base import XlsxExporter
from collabtrans.ir.document import Document


class Epub2EpubExporter(XlsxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
