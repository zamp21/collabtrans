# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from collabtrans.exporter.txt.base import TXTExporter
from collabtrans.ir.document import Document


class TXT2TXTExporter(TXTExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
