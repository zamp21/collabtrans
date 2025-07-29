from docutranslate.exporter.interfaces import Exporter
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument


class MDExporter(Exporter):

    def export(self,document:MarkdownDocument)->Document:
        ...
