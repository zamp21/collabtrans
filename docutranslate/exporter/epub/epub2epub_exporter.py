from docutranslate.exporter.txt.base import TXTExporter
from docutranslate.exporter.xlsx.base import XlsxExporter
from docutranslate.ir.document import Document


class Epub2EpubExporter(XlsxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
