# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from collabtrans.exporter.base import Exporter
from collabtrans.ir.document import Document

# TODO: Consider if a separate document type is needed for JSON files
class JsonExporter(Exporter[Document]):

    def export(self,document:Document)->Document:
        ...