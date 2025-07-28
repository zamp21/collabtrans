from docutranslate.exporter.interfaces import Exporter
from docutranslate.ir.document import Document

#TODO:看情况是否需要为TXT单独写一个document类型
class TXTExporter(Exporter):

    def export(self,document:Document)->Document:
        ...