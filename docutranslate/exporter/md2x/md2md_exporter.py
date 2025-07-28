from dataclasses import dataclass
from typing import runtime_checkable

from docutranslate.exporter.export_config import ExportConfig
from docutranslate.exporter.md2x.interfaces import MDExporter
from docutranslate.ir.markdown_document import MarkdownDocument,Document
from docutranslate.utils.markdown_utils import unembed_base64_images_to_zip


@dataclass
class MD2MDExportConfig(ExportConfig):
    embed_images: bool = True


class MD2MDExporter(MDExporter):
    def __init__(self, export_config: MD2MDExportConfig | None=None):
        export_config=export_config or MD2MDExportConfig()
        self.embed_images=export_config.embed_images

    def export(self,document:MarkdownDocument)->Document:
        if self.embed_images:
            return Document.from_bytes(suffix=".md",content=document.content,stem=document.stem)
        else:
            return Document.from_bytes(suffix=".zip",content=unembed_base64_images_to_zip(document.content.decode(), markdown_name=document.name),stem=document.stem)


