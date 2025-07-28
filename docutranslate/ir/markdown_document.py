from docutranslate.ir.document import Document


class MarkdownDocument(Document):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.suffix=".md"