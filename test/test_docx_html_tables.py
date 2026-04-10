# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
"""Test script to verify DOCX export with HTML tables."""

import asyncio
import logging
from pathlib import Path

from collabtrans.converter.x2md.converter_mineru import ConverterMineruConfig, ConverterMineru
from collabtrans.exporter.md.md2docx_exporter import MD2DocxExporter, MD2DocxExporterConfig
from collabtrans.ir.markdown_document import MarkdownDocument

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_html_table_to_docx():
    """Test that HTML tables from MinerU convert to proper DOCX tables."""
    # Create a test markdown with inline HTML table (like MinerU produces)
    test_md = """# Test Document

This is a test paragraph.

<table><tr><td></td><td>试样编号</td><td>最大力</td></tr><tr><td>单位</td><td></td><td>N</td></tr><tr><td>1</td><td>A1</td><td>100</td></tr></table>

Another paragraph after the table.

| Markdown Col1 | Markdown Col2 |
|---------------|---------------|
| MD Cell A     | MD Cell B     |

Final paragraph.
"""

    # Create a MarkdownDocument
    md_doc = MarkdownDocument(
        stem="test_tables",
        suffix=".md",
        content=test_md.encode('utf-8')
    )

    # Export to DOCX
    exporter = MD2DocxExporter()
    docx_doc = exporter.export(md_doc)

    # Save to file for inspection
    output_path = Path("/tmp/test_html_tables.docx")
    output_path.write_bytes(docx_doc.content)

    # Check if tables are present in the DOCX
    import subprocess
    result = subprocess.run(
        ['unzip', '-p', str(output_path), 'word/document.xml'],
        capture_output=True,
        text=True
    )

    # Count table elements
    table_count = result.stdout.count('<w:tbl>')
    logger.info(f"Found {table_count} tables in DOCX")

    if table_count >= 2:
        logger.info("SUCCESS: Both HTML and markdown tables converted to DOCX tables")
    else:
        logger.error(f"FAILURE: Expected at least 2 tables, found {table_count}")

    return table_count >= 2


if __name__ == "__main__":
    success = test_html_table_to_docx()
    print(f"\nTest result: {'PASSED' if success else 'FAILED'}")