# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from collabtrans.exporter.md.base import MDExporter, MDExporterConfig
from collabtrans.ir.document import Document
from collabtrans.ir.markdown_document import MarkdownDocument

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class MD2DocxExporterConfig(MDExporterConfig):
    """Configuration for MD to DOCX exporter using Pandoc."""
    # Additional Pandoc options can be added here
    reference_doc: Optional[str] = None  # Path to reference DOCX for styling
    toc: bool = False  # Whether to include table of contents
    toc_depth: int = 3  # Depth of table of contents


class MD2DocxExporter(MDExporter):
    """
    Export Markdown to DOCX using Pandoc.

    Requires pandoc to be installed on the system.
    """

    def __init__(self, config: Optional[MD2DocxExporterConfig] = None):
        super().__init__(config=config)
        self._check_pandoc_available()

    def _check_pandoc_available(self):
        """Check if pandoc is available on the system."""
        try:
            import subprocess
            result = subprocess.run(['pandoc', '--version'], capture_output=True, timeout=5)
            if result.returncode != 0:
                raise RuntimeError("Pandoc is not available. Please install pandoc: https://pandoc.org/installing.html")
        except FileNotFoundError:
            raise RuntimeError("Pandoc is not installed. Please install pandoc: https://pandoc.org/installing.html")
        except Exception as e:
            raise RuntimeError(f"Failed to check pandoc availability: {e}")

    def export(self, document: MarkdownDocument) -> Document:
        """
        Export MarkdownDocument to DOCX format using Pandoc.

        Args:
            document: The MarkdownDocument to export

        Returns:
            A Document containing the DOCX file content
        """
        import subprocess

        config = self.config if isinstance(self.config, MD2DocxExporterConfig) else MD2DocxExporterConfig()

        # Create temporary files for input and output
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as md_file:
            md_file.write(document.content.decode('utf-8'))
            md_path = md_file.name

        docx_path = md_path.replace('.md', '.docx')

        try:
            # Build pandoc command
            cmd = [
                'pandoc',
                md_path,
                '-o', docx_path,
                '--from=markdown+pipe_tables+grid_tables+multiline_tables+raw_html+tex_math_dollars',
                '--to=docx',
                '--wrap=none',
            ]

            # Add optional parameters
            if config.reference_doc and os.path.exists(config.reference_doc):
                cmd.extend(['--reference-doc', config.reference_doc])

            if config.toc:
                cmd.append('--toc')
                cmd.extend(['--toc-depth', str(config.toc_depth)])

            logger.info(f"Running pandoc: {' '.join(cmd)}")

            # Run pandoc
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minutes timeout
            )

            if result.returncode != 0:
                logger.error(f"Pandoc conversion failed: {result.stderr}")
                raise RuntimeError(f"Pandoc conversion failed: {result.stderr}")

            # Read the generated DOCX file
            with open(docx_path, 'rb') as f:
                docx_content = f.read()

            logger.info(f"Successfully converted markdown to DOCX ({len(docx_content)} bytes)")

            return Document.from_bytes(
                suffix=".docx",
                content=docx_content,
                stem=document.stem
            )

        except subprocess.TimeoutExpired:
            raise RuntimeError("Pandoc conversion timed out")
        finally:
            # Clean up temporary files
            if os.path.exists(md_path):
                os.remove(md_path)
            if os.path.exists(docx_path):
                os.remove(docx_path)