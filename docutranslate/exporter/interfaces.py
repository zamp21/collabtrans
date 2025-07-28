from typing import Protocol, runtime_checkable, TypeVar, Any, Self

from docutranslate.exporter.export_config import ExportConfig
from docutranslate.ir.document import Document

D_in = TypeVar('D_in', bound=Document)


@runtime_checkable
class Exporter(Protocol[D_in]):
    @classmethod
    def from_config(cls, export_config: ExportConfig | None = None) -> Self:
        ...

    def export(self, document: D_in) -> Any:
        ...
