# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from collabtrans.exporter.base import Exporter
from collabtrans.ir.document import Document

#TODO:看情况是否需要为TXT单独写一个document类型
class SrtExporter(Exporter[Document]):

    def export(self,document:Document)->Document:
        ...