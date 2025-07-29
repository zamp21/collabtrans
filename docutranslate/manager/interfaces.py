from pathlib import Path
from typing import Protocol, runtime_checkable, Self, TypeVar

from docutranslate.exporter.export_config import ExportConfig

T = TypeVar("T", bound=ExportConfig)



@runtime_checkable
class HTMLExportable(Protocol):
    def export_to_html(self, export_config: T) -> str:
        ...

    def save_as_html(self, name: str, output_dir: Path | str, export_config: T) -> Self:
        ...


@runtime_checkable
class MDExportable(Protocol):
    def export_to_markdown(self, export_config: T) -> str:
        ...

    def save_as_markdown(self, name: str, output_dir: Path | str, export_config: T) -> Self:
        ...


@runtime_checkable
class TXTExportable(Protocol):
    def export_to_txt(self) -> str:
        ...

    def save_as_txt(self, name: str, output_dir: Path | str) -> Self:
        ...
