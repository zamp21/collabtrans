from copy import copy
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import Self

from docutranslate.exporter.txt2x.txt2html_exporter import TXT2HTMLExportConfig, TXT2HTMLExporter
from docutranslate.manager.base_manager import BaseManager
from docutranslate.manager.interfaces import HTMLExportable
from docutranslate.translater.txt_translator import TXTTranslateConfig, TXTTranslator


@dataclass
class TXTManagerConfig:
    chunk_size: int = 3000
    base_url: str | None = None
    api_key = None,
    model_id: str | None = None
    temperature = 0.7
    concurrent: int = 30
    timeout = 2000
    cache = True
    logger: Logger | None = None


class TXTManager(BaseManager, HTMLExportable):
    def support_export_format(self) -> list[str]:
        return [".txt", ".html"]

    def translate(self, translate_config: TXTTranslateConfig) -> Self:
        document = copy(self.document_original)
        # 翻译解析后文件
        translator = TXTTranslator(translate_config)
        translator.translate(document)
        self.document_translated = document
        return self

    async def translate_async(self, translate_config: TXTTranslateConfig) -> Self:
        document = copy(self.document_original)
        # 翻译解析后文件
        translator = TXTTranslator(translate_config)
        await translator.translate_async(document)
        self.document_translated = document
        return self

    def export_to_html(self, export_config: TXT2HTMLExportConfig) -> str:
        docu = self._export(TXT2HTMLExporter(export_config))
        return docu.content.decode()

    def export_to_txt(self) -> str:
        if self.document_translated is None:
            raise RuntimeError("Document has not been translated yet. Call translate() first.")
        return self.document_translated.content.decode()

    def save_as_html(self, name: str = None, out_put_dir: Path | str = "./output",
                     export_config: TXT2HTMLExportConfig | None = None) -> Self:
        self._save(exporter=TXT2HTMLExporter(export_config), name=name, out_put_dir=out_put_dir)
        return self

    def save_as_txt(self, name: str = None, out_put_dir: Path | str = "./output", ) -> Self:
        name = name or self.document_translated.name
        output_path = Path(out_put_dir) / Path(name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(self.document_translated.content)
        self.logger.info(f"文件已保存到{output_path.resolve()}")
        return self
