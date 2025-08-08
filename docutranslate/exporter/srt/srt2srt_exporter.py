from docutranslate.exporter.srt.base import SrtExporter
from docutranslate.ir.document import Document


class Srt2SrtExporter(SrtExporter):
    def export(self, document: Document) -> Document:
        return document.copy()
