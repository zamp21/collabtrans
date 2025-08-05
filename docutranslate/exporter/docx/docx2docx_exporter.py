from docutranslate.exporter.docx.base import DocxExporter
from docutranslate.ir.document import Document


class Docx2DocxExporter(DocxExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
