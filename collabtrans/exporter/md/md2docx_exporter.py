# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import base64
import hashlib
import logging
import mimetypes
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

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
    extract_images: bool = True  # Whether to extract base64 images to files


class MD2DocxExporter(MDExporter):
    """
    Export Markdown to DOCX using Pandoc.

    Handles:
    - Base64 embedded images (extracts to temporary files)
    - HTML tables (converted via pandoc raw_html)
    - LaTeX formulas (via tex_math_dollars)

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

    def _extract_base64_images(self, markdown_content: str, image_dir: str, md_dir: str) -> Tuple[str, list]:
        """
        Extract base64 embedded images to files and update markdown references.

        Args:
            markdown_content: The markdown content with base64 images
            image_dir: Directory to save extracted images
            md_dir: Directory where the markdown file will be saved (for relative paths)

        Returns:
            Tuple of (updated markdown content, list of created image paths)
        """
        os.makedirs(image_dir, exist_ok=True)
        created_files = []

        # Pattern to match base64 images: ![alt](data:mime;base64,data)
        pattern = r'!\[(.*?)\]\(data:([^;]+);base64,([^)]+)\)'

        def replace_base64_image(match: re.Match) -> str:
            alt_text = match.group(1)
            mime_type = match.group(2)
            b64_data = match.group(3)

            # Determine file extension
            ext = mimetypes.guess_extension(mime_type)
            if not ext:
                ext = '.bin'

            # Generate unique filename based on content hash
            content_hash = hashlib.md5(b64_data.encode()).hexdigest()[:12]
            image_filename = f"img_{content_hash}{ext}"
            image_path = os.path.join(image_dir, image_filename)

            # Decode and save image
            try:
                image_bytes = base64.b64decode(b64_data)
                with open(image_path, 'wb') as f:
                    f.write(image_bytes)
                created_files.append(image_path)
                logger.debug(f"Extracted base64 image to: {image_path}")

                # Calculate relative path from markdown file to image
                rel_image_path = os.path.relpath(image_path, md_dir)
                # Return updated markdown with relative file reference
                return f"![{alt_text}]({rel_image_path})"
            except Exception as e:
                logger.warning(f"Failed to extract base64 image: {e}")
                return match.group(0)  # Return original if extraction fails

        updated_content = re.sub(pattern, replace_base64_image, markdown_content)
        return updated_content, created_files

    def _process_html_tables(self, markdown_content: str) -> str:
        """
        Process HTML tables to ensure they render correctly in DOCX.

        Pandoc should handle raw HTML tables, but we can add some preprocessing
        if needed.
        """
        # HTML tables should be handled by pandoc's raw_html extension
        # No additional processing needed for now
        return markdown_content

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

        # Create a temporary directory for all files
        with tempfile.TemporaryDirectory() as temp_dir:
            md_path = os.path.join(temp_dir, f"{document.stem}.md")
            docx_path = os.path.join(temp_dir, f"{document.stem}.docx")
            image_dir = os.path.join(temp_dir, "images")

            # Get markdown content
            markdown_content = document.content.decode('utf-8')

            # Process content
            if config.extract_images:
                # Extract base64 images to files (use relative paths from md_dir)
                markdown_content, _ = self._extract_base64_images(markdown_content, image_dir, temp_dir)

            # Process HTML tables
            markdown_content = self._process_html_tables(markdown_content)

            # Write processed markdown
            with open(md_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)

            try:
                # Build pandoc command
                # Key extensions:
                # - pipe_tables+grid_tables: Markdown table formats
                # - raw_html: Allow HTML tables
                # - tex_math_dollars: $..$ and $$...$$ for LaTeX math
                cmd = [
                    'pandoc',
                    md_path,
                    '-o', docx_path,
                    '--from=markdown+pipe_tables+grid_tables+multiline_tables+raw_html+tex_math_dollars',
                    '--to=docx',
                    '--wrap=none',
                    '--resource-path=' + temp_dir,  # Allow pandoc to find images
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
                    timeout=300  # 5 minutes timeout for large documents
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