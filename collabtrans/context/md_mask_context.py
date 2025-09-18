# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from collabtrans.ir.markdown_document import MarkdownDocument
from collabtrans.utils.markdown_utils import MaskDict, uris2placeholder, placeholder2uris


class MDMaskUrisContext:
    def __init__(self, document: MarkdownDocument):
        self.document = document
        self.mask_dict = MaskDict()

    def __enter__(self):
        self.document.content = uris2placeholder(self.document.content.decode(), self.mask_dict).encode()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.document.content = placeholder2uris(self.document.content.decode(), self.mask_dict).encode()
