#!/usr/bin/env python3

"""
Simple PDF to DOCX converter using pdf2docx.

Usage:
  python tools/pdf_to_docx.py input.pdf [output.docx] [--start 1] [--end -1]

Notes:
  - If output path is omitted, it will use the same stem as input with .docx extension.
  - You can limit pages with --start/--end (1-based, inclusive). Use -1 for end to convert to last page.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def convert_pdf_to_docx(
    pdf_path: Path,
    docx_path: Path,
    start_page: int | None = None,
    end_page: int | None = None,
) -> None:
    try:
        from pdf2docx import Converter  # type: ignore
    except Exception as e:
        print(f"[ERROR] Failed to import pdf2docx: {e}", file=sys.stderr)
        print("Please install it: uv add pdf2docx", file=sys.stderr)
        sys.exit(1)

    if not pdf_path.exists():
        print(f"[ERROR] Input PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(2)

    docx_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Converting PDF → DOCX")
    print(f"       Input : {pdf_path}")
    print(f"       Output: {docx_path}")
    if start_page or end_page:
        print(f"       Pages : {start_page or 1} .. {end_page or 'last'}")

    try:
        cv = Converter(str(pdf_path))
        # pdf2docx expects zero-based page index in some versions when using pages arg via list.
        # Here we use start/end parameters which are 0-based internally but behaves like 1-based in API.
        # To avoid ambiguity across versions, call convert with explicit start/end if provided.
        kwargs = {}
        if start_page is not None and start_page > 0:
            kwargs["start"] = start_page - 1  # convert to 0-based
        if end_page is not None and end_page > 0:
            kwargs["end"] = end_page - 1  # convert to 0-based, inclusive behavior handled by library
        cv.convert(str(docx_path), **kwargs)
        cv.close()
        print("[OK] Conversion finished.")
    except Exception as e:
        print(f"[ERROR] Conversion failed: {e}", file=sys.stderr)
        sys.exit(3)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert PDF to DOCX using pdf2docx")
    parser.add_argument("input_pdf", help="Path to input PDF")
    parser.add_argument("output_docx", nargs="?", help="Path to output DOCX (optional)")
    parser.add_argument("--start", type=int, default=None, help="Start page (1-based, inclusive)")
    parser.add_argument("--end", type=int, default=None, help="End page (1-based, inclusive). Use -1 for last page")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    pdf_path = Path(args.input_pdf).expanduser().resolve()

    if args.output_docx:
        docx_path = Path(args.output_docx).expanduser().resolve()
    else:
        stem = pdf_path.stem
        docx_path = pdf_path.with_name(stem + ".docx")

    start_page = args.start
    end_page = None if args.end in (None, -1) else args.end

    convert_pdf_to_docx(pdf_path, docx_path, start_page=start_page, end_page=end_page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


