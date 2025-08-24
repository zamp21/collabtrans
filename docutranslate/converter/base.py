from abc import ABC, abstractmethod
from dataclasses import dataclass
from logging import Logger
from typing import Hashable

from docutranslate.ir.document import Document
from docutranslate.logger import global_logger


@dataclass(kw_only=True)
class ConverterConfig(ABC):
    logger: Logger | None = None

    @abstractmethod
    def gethash(self) -> Hashable:
        ...


class Converter(ABC):
    def __init__(self, config: ConverterConfig | None = None):
        self.config = config
        if config:
            self.logger = config.logger or global_logger
        else:
            self.logger = global_logger

    @abstractmethod
    def convert(self, document: Document) -> Document:
        ...

    async def convert_async(self, document: Document) -> Document:
        ...