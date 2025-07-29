from pathlib import Path
from typing import Protocol, Self, TypeVar, runtime_checkable

from docutranslate.exporter.export_config import ExportConfig

T = TypeVar("T", bound=ExportConfig)

@runtime_checkable
class HTMLExportable(Protocol[T]):
    def export_to_html(self, export_config: T | None = None) -> str:
        ...

    def save_as_html(self, name: str, output_dir: Path | str, export_config: T | None = None) -> Self:
        ...

@runtime_checkable
class MDExportable(Protocol[T]):

    def export_to_markdown(self, export_config: T | None = None) -> str:
        ...

    def save_as_markdown(self, name: str, output_dir: Path | str, export_config: T | None = None) -> Self:
        ...

@runtime_checkable
class MDZIPExportable(Protocol[T]):

    def export_to_markdown_zip(self, export_config: T | None = None) -> bytes:
        ...

    def save_as_markdown_zip(self, name: str, output_dir: Path | str, export_config: T | None = None) -> Self:
        ...

@runtime_checkable
class MDFormatsExportable(MDZIPExportable[T], MDExportable[T], Protocol):
    ...

@runtime_checkable
class TXTExportable(Protocol[T]):
    def export_to_txt(self) -> str:
        ...

    def save_as_txt(self, name: str, output_dir: Path | str) -> Self:
        ...
