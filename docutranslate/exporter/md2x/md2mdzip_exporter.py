from dataclasses import dataclass

from docutranslate.exporter.export_config import ExportConfig
from docutranslate.exporter.md2x.interfaces import MDExporter
from docutranslate.ir.markdown_document import MarkdownDocument,Document
from docutranslate.utils.markdown_utils import unembed_base64_images_to_zip


@dataclass
class MD2MDZIPExportConfig(ExportConfig):
    pass


class MD2MDZipExporter(MDExporter):
    def __init__(self, export_config: MD2MDZIPExportConfig | None=None):
        pass

    def export(self,document:MarkdownDocument)->Document:
        return Document.from_bytes(suffix=".zip",content=unembed_base64_images_to_zip(document.content.decode(), markdown_name=document.name),stem=document.stem)


