#!/usr/bin/env python3
"""Test MinerU output to see table format"""

import json
import httpx
import io

# Test with a simple PDF to see the output format
def test_mineru_output():
    # Use the local MinerU API
    base_url = "http://localhost:8920"

    # Create a test PDF or use existing one
    test_pdf_path = "test/test_files/sample.pdf"

    # If no test PDF, create a simple one
    import os
    if not os.path.exists(test_pdf_path):
        print(f"No test PDF found at {test_pdf_path}")
        print("Please provide a test PDF file")
        return

    with open(test_pdf_path, 'rb') as f:
        pdf_content = f.read()

    # Upload to MinerU
    file_content = io.BytesIO(pdf_content)
    file_content.name = "sample.pdf"

    data = {
        "backend": "hybrid-auto-engine",
        "parse_method": "auto",
        "formula_enable": True,
        "table_enable": True,
        "return_md": True,
        "return_content_list": True,
        "is_ocr": True
    }

    client = httpx.Client(timeout=300.0)

    try:
        response = client.post(
            f"{base_url}/file_parse",
            data=data,
            files={"files": ("sample.pdf", file_content, "application/pdf")}
        )
        response.raise_for_status()
        result = response.json()

        # Print the result structure
        print("=== MinerU Result Structure ===")
        print(f"Status: {result.get('status')}")

        if result.get('results'):
            for filename, file_result in result['results'].items():
                print(f"\n=== File: {filename} ===")

                # Check if content_list exists
                if file_result.get('content_list'):
                    content_list = file_result['content_list']
                    print(f"Content list length: {len(content_list)}")

                    # Find tables in content_list
                    tables = [item for item in content_list if item.get('type') == 'table']
                    print(f"Tables found: {len(tables)}")

                    if tables:
                        print("\n=== First Table Structure ===")
                        first_table = tables[0]
                        print(json.dumps(first_table, indent=2, ensure_ascii=False)[:2000])

                # Check markdown content for table format
                if file_result.get('md_content'):
                    md_content = file_result['md_content']
                    # Find table sections in markdown
                    lines = md_content.split('\n')
                    table_lines = []
                    in_table = False
                    for line in lines:
                        if '|' in line and line.strip().startswith('|'):
                            in_table = True
                            table_lines.append(line)
                        elif in_table and not line.strip().startswith('|'):
                            in_table = False
                            if table_lines:
                                break

                    if table_lines:
                        print("\n=== Markdown Table Sample ===")
                        for line in table_lines[:10]:
                            print(line)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mineru_output()