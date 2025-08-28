from typing import Literal

from docutranslate.ir.document import Document

AttachMentIdentifier = Literal["glossary"]


class AttachMent:
    def __init__(self):
        self.attachment_dict: dict[AttachMentIdentifier, Document] = {}

    def add_attachment(self, identifier: AttachMentIdentifier, document: Document):
        self.attachment_dict[identifier] = document
