# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from io import BytesIO
import logging

from xlsx2html import xlsx2html

from collabtrans.exporter.base import ExporterConfig
from collabtrans.exporter.xlsx.base import XlsxExporter
from collabtrans.ir.document import Document
from collabtrans.utils.memory_utils import log_memory

logger = logging.getLogger(__name__)


@dataclass
class Xlsx2HTMLExporterConfig(ExporterConfig):
    cdn: bool = True


class Xlsx2HTMLExporter(XlsxExporter):
    def __init__(self, config: Xlsx2HTMLExporterConfig = None):
        config = config or Xlsx2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn = config.cdn

    def export(self, document: Document) -> Document:
        log_memory(logger, "xlsx2html: before export", "")
        html_content = xlsx2html(BytesIO(document.content), output=None).getvalue()
        log_memory(logger, "xlsx2html: after export", f"html size {len(html_content) / (1024*1024):.2f} MB")
        return Document.from_bytes(content=html_content.encode("utf-8"), suffix=".html", stem=document.stem)
