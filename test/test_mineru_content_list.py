#!/usr/bin/env python3
"""Test PDF to DOCX conversion using MinerU with content_list"""

import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collabtrans.converter.x2md.converter_mineru import ConverterMineru, ConverterMineruConfig
from collabtrans.ir.document import Document


async def test_mineru_content_list():
    """Test MinerU conversion and check content_list structure"""

    test_pdf = "test/test_files/sample.pdf"
    if not os.path.exists(test_pdf):
        # Try other common test PDF locations
        for path in ["1.pdf", "test.pdf", "sample.pdf"]:
            if os.path.exists(path):
                test_pdf = path
                break
        else:
            print("No test PDF found. Please provide a test PDF file.")
            return

    print(f"Using test PDF: {test_pdf}")

    # Create MinerU converter
    config = ConverterMineruConfig(
        mineru_token='',
        base_url='http://localhost:8920',
        model_version='vlm',
        formula_ocr=True,
        ocr_enabled=True
    )
    converter = ConverterMineru(config)

    # Convert PDF
    print("Converting PDF with MinerU...")
    document = Document.from_path(test_pdf)
    md_doc = converter.convert(document)

    print(f"Markdown content length: {len(md_doc.content)} bytes")

    # Check if we have local_result with content_list
    if hasattr(converter, 'local_result') and converter.local_result:
        result = converter.local_result
        print(f"\nResult status: {result.get('status')}")

        if result.get('results'):
            for filename, file_result in result['results'].items():
                print(f"\nFile: {filename}")

                # Check content_list
                if file_result.get('content_list'):
                    content_list = file_result['content_list']
                    print(f"Content list length: {len(content_list)}")

                    # Find tables
                    tables = [item for item in content_list if item.get('type') == 'table']
                    print(f"Tables found: {len(tables)}")

                    if tables:
                        print("\n=== First Table Structure ===")
                        first_table = tables[0]
                        print(f"Table keys: {first_table.keys()}")
                        if first_table.get('table_body'):
                            table_body = first_table['table_body']
                            print(f"Table body rows: {len(table_body)}")
                            if table_body:
                                print(f"First row cols: {len(table_body[0]) if table_body[0] else 0}")
                                print(f"Sample data: {table_body[0][:3] if table_body[0] else 'empty'}")
                else:
                    print("No content_list in result")
        else:
            print("No results in local_result")
    else:
        print("No local_result available")


if __name__ == "__main__":
    asyncio.run(test_mineru_content_list())