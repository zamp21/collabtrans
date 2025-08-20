from dataclasses import dataclass

import jinja2
import markdown2

from docutranslate.exporter.md.base import MDExporter, MDExporterConfig
from docutranslate.ir.document import Document
from docutranslate.ir.markdown_document import MarkdownDocument
from docutranslate.utils.resource_utils import resource_path

@dataclass
class MD2HTMLExporterConfig(MDExporterConfig):
    cdn: bool = True

class MD2HTMLExporter(MDExporter):
    def __init__(self, config: MD2HTMLExporterConfig = None):
        config = config or MD2HTMLExporterConfig()
        super().__init__(config=config)
        self.cdn=config.cdn

    def export(self, document: MarkdownDocument) -> Document:
        cdn = self.cdn
        markdowner = markdown2.Markdown(extras=['tables', 'fenced-code-blocks', 'mermaid', "code-friendly"])
        # language=html
        pico = f'<style>{resource_path("static/pico.css").read_text(encoding="utf-8")}</style>' if not cdn else r'<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/picocss/2.1.1/pico.min.css" integrity="sha512-+4kjFgVD0n6H3xt19Ox84B56MoS7srFn60tgdWFuO4hemtjhySKyW4LnftYZn46k3THUEiTTsbVjrHai+0MOFw==" crossorigin="anonymous" referrerpolicy="no-referrer" />'
        html_template = resource_path("template/markdown.html").read_text(encoding="utf-8")
        katex_css = f'<link rel="stylesheet" href="/static/katex/katex.css"/>' if not cdn else r"""<link rel="stylesheet" href="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.css" integrity="sha512-fHwaWebuwA7NSF5Qg/af4UeDx9XqUpYpOGgubo3yWu+b2IQR4UeQwbb42Ti7gVAjNtVoI/I9TEoYeu9omwcC6g==" crossorigin="anonymous" referrerpolicy="no-referrer" />"""
        katex_js = f'<script src="/static/katex/katex.js"></script>' if not cdn else r"""<script src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/katex.min.js" integrity="sha512-LQNxIMR5rXv7o+b1l8+N1EZMfhG7iFZ9HhnbJkTp4zjNr5Wvst75AqUeFDxeRUa7l5vEDyUiAip//r+EFLLCyA==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>"""
        auto_render = f'<script>{resource_path("static/autoRender.js").read_text(encoding="utf-8")}</script>' if not cdn else r"""<script src="https://s4.zstatic.net/ajax/libs/KaTeX/0.16.9/contrib/auto-render.min.js" integrity="sha512-iWiuBS5nt6r60fCz26Nd0Zqe0nbk1ZTIQbl3Kv7kYsX+yKMUFHzjaH2+AnM6vp2Xs+gNmaBAVWJjSmuPw76Efg==" crossorigin="anonymous" referrerpolicy="no-referrer"></script>"""
        # language=javascript
        render_math_in_element = r"""
                                 <script>
                                     document.addEventListener("DOMContentLoaded", function () {
                                     renderMathInElement(document.body, {
                                         delimiters: [
                                             {left: '$$', right: '$$', display: true},
                                             {left: '\\[', right: '\\]', display: true},
                                             {left: '$', right: '$', display: false},
                                             {left: '\\(', right: '\\)', display: false}
                                         ],
                                         throwOnError: false
                                     })
                                 });
                                 </script>""" if cdn else r"""
                                                          <script>
                                                              document.addEventListener("DOMContentLoaded", function
                                                              () {
                                                              renderMathInElement(document.body, {
                                                                  delimiters: [
                                                                      {left: '$$', right: '$$', display: true},
                                                                      {left: '\\[', right: '\\]', display: true},
                                                                      {left: '$', right: '$', display: false},
                                                                      {left: '\\(', right: '\\)', display: false}
                                                                  ],
                                                                  fonts: false,
                                                                  throwOnError: false
                                                              })
                                                          });
                                                          </script>"""
        mermaid = f'<script>{resource_path("static/mermaid.js").read_text(encoding="utf-8")}</script>'
        content = markdowner.convert(document.content.decode().replace("\\", "\\\\"))
        # TODO:实现MathJax本地化
        render = jinja2.Template(html_template).render(
            title=document.stem,
            pico=pico,
            katexCss=katex_css,
            katexJs=katex_js,
            autoRender=auto_render,
            markdown=content,
            renderMathInElement=render_math_in_element,
            mermaid=mermaid,
        )
        return Document.from_bytes(content=render.encode("utf-8"), suffix=".html", stem=document.stem)
