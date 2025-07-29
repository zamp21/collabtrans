from dataclasses import dataclass

from docutranslate.exporter.export_config import ExportConfig
from docutranslate.exporter.md2x.interfaces import MDExporter
from docutranslate.ir.markdown_document import MarkdownDocument,Document


@dataclass
class MD2MDExportConfig(ExportConfig):
    pass


class MD2MDExporter(MDExporter):
    def __init__(self, export_config: MD2MDExportConfig | None=None):
        pass

    def export(self,document:MarkdownDocument)->Document:
        return Document.from_bytes(suffix=".md",content=document.content,stem=document.stem)
