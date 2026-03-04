# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from io import BytesIO, StringIO
import logging

import openpyxl
import csv
from collabtrans.exporter.xlsx.base import XlsxExporter
from collabtrans.ir.document import Document
from collabtrans.utils.memory_utils import log_memory

logger = logging.getLogger(__name__)


class Xlsx2CsvExporter(XlsxExporter):

    def export(self, document: Document) -> Document:
        log_memory(logger, "xlsx2csv: before load_workbook", f"file size {len(document.content) / (1024*1024):.2f} MB")
        workbook = openpyxl.load_workbook(BytesIO(document.content))
        sheet = workbook.active

        # 2. Use StringIO as text buffer
        text_buffer = StringIO()

        # 3. Pass buffer directly to csv.writer
        writer = csv.writer(text_buffer)

        # Iterate through each row in the worksheet
        for row in sheet.rows:
            writer.writerow([cell.value for cell in row])

        # 4. Encode text buffer content as bytes
        output_bytes = text_buffer.getvalue().encode('utf-8')
        log_memory(logger, "xlsx2csv: after export", f"csv size {len(output_bytes) / (1024*1024):.2f} MB")

        # 5. Return a Document with .csv suffix
        return Document.from_bytes(content=output_bytes, suffix=".csv", stem=document.stem)




