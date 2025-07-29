from dataclasses import dataclass

import jinja2

from docutranslate.exporter.export_config import ExportConfig
from docutranslate.exporter.txt2x.interfaces import TXTExporter
from docutranslate.ir.document import Document
from docutranslate.utils.resource_utils import resource_path


@dataclass
class TXT2HTMLExportConfig(ExportConfig):
    cdn: bool = True


class TXT2HTMLExporter(TXTExporter):
    def __init__(self, export_config: TXT2HTMLExportConfig = None):
        export_config = export_config or TXT2HTMLExportConfig()
        self.cdn = export_config.cdn

    def export(self, document: Document) -> Document:
        cdn = self.cdn
        html_template = resource_path("template/txt.html").read_text(encoding="utf-8")

        # language=html
        pico = f'<style>{resource_path("static/pico.css").read_text(encoding="utf-8")}</style>' if not cdn else r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/picocss/2.1.1/pico.min.css" integrity="sha512-+4kjFgVD0n6H3xt19Ox84B56MoS7srFn60tgdWFuO4hemtjhySKyW4LnftYZn46k3THUEiTTsbVjrHai+0MOFw==" crossorigin="anonymous" referrerpolicy="no-referrer" />'

        body='\n'.join([r'<p>'+para+'</p>' for para in document.content.decode().split("\n")])
        render = jinja2.Template(html_template).render(
            title=document.stem,
            pico=pico,
            body=body,
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)
