# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import os
import asyncio
from collections import OrderedDict

from collabtrans.converter.base import ConverterConfig
from collabtrans.ir.document import Document
from collabtrans.ir.markdown_document import MarkdownDocument

CACHE_NUM = os.getenv("DOCUTRANSLATE_CACHE_NUM", default="10")


class MDBasedCovertCacher:
    def __init__(self):
        self.cache_dict = OrderedDict()
        self._locks = {}  # Per-document locks
        self._global_lock = asyncio.Lock()  # Lock for managing _locks dict

    @staticmethod
    def _get_hashcode(document: Document, convert_engin: str, convert_config: ConverterConfig|None) -> str:
        if convert_config :
            convert_config_hash=convert_config.gethash()
        else:
            convert_config_hash=None

        obj = (document.suffix, document.content, convert_engin, convert_config_hash)
        return str(hash(obj))

    def get_cached_result(self, document: Document, convert_engin: str,
                          convert_config: ConverterConfig) -> MarkdownDocument | None:
        return self.cache_dict.get(self._get_hashcode(document, convert_engin, convert_config))

    def cache_result(self, convert_result: MarkdownDocument, document: Document, convert_engin: str,
                     convert_config: ConverterConfig) -> MarkdownDocument:
        hash_code = self._get_hashcode(document, convert_engin, convert_config)
        if len(self.cache_dict) > int(CACHE_NUM):
            self.cache_dict.popitem(last=False)
        self.cache_dict[hash_code] = convert_result
        return convert_result

    async def get_or_convert(self, document: Document, convert_engin: str,
                              convert_config: ConverterConfig, convert_func) -> MarkdownDocument:
        """Get cached result or convert with lock to prevent duplicate conversions.

        Args:
            document: The document to convert
            convert_engin: The converter engine name (e.g., 'mineru')
            convert_config: The converter configuration
            convert_func: Async function to call for conversion if not cached

        Returns:
            MarkdownDocument (either from cache or newly converted)
        """
        hash_code = self._get_hashcode(document, convert_engin, convert_config)

        # Check cache first without lock
        cached = self.cache_dict.get(hash_code)
        if cached is not None:
            return cached

        # Get or create a lock for this specific document
        async with self._global_lock:
            if hash_code not in self._locks:
                self._locks[hash_code] = asyncio.Lock()
            doc_lock = self._locks[hash_code]

        # Acquire the document-specific lock
        async with doc_lock:
            # Double-check cache after acquiring lock (another coroutine might have converted it)
            cached = self.cache_dict.get(hash_code)
            if cached is not None:
                return cached

            # Perform the conversion
            result = await convert_func()

            # Cache the result
            if len(self.cache_dict) > int(CACHE_NUM):
                self.cache_dict.popitem(last=False)
            self.cache_dict[hash_code] = result

            return result

    def clear(self):
        self.cache_dict.clear()
        self._locks.clear()


md_based_convert_cacher = MDBasedCovertCacher()