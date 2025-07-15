import os
from collections import OrderedDict

from docutranslate.converter import Document

CACHE_NUM=os.getenv("DOCUTRANSLATE_CACHE_NUM",default=10)

class DocumentCacher:
    def __init__(self):
        self.cache_dict = OrderedDict()
    @staticmethod
    def _get_hashcode(document: Document, formula: bool, code: bool, convert_engin: str) -> str:
        obj = (document.suffix, document.filebytes, formula, code, convert_engin)
        return str(hash(obj))

    def get_cached_result(self, document: Document, formula: bool, code: bool, convert_engin: str)->str|None:
        return self.cache_dict.get(self._get_hashcode(document, formula, code, convert_engin))

    def cache_result(self, result: str, document: Document, formula: bool, code: bool, convert_engin: str):
        hash_code = self._get_hashcode(document, formula, code, convert_engin)
        if len(self.cache_dict)>=CACHE_NUM:
            self.cache_dict.popitem(last=False)
        self.cache_dict[hash_code] = result
        return result

    def clear(self):
        self.cache_dict.clear()


document_cacher_global = DocumentCacher()
