from typing import Self

from docutranslate.exporter.export_config import ExportConfig
from docutranslate.exporter.interfaces import Exporter
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument


class MDExporter(Exporter):

    def export(self,document:MarkdownDocument)->Document:
        ...
