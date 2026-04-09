#!/usr/bin/env python3
"""Test PDF to DOCX conversion using MinerU + Pandoc"""

import asyncio
import sys
import os

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collabtrans.converter.format_converter import FormatConverter


async def test_conversion():
    converter = FormatConverter()

    # Test with a sample PDF if available
    test_pdf = "test.pdf"
    if not os.path.exists(test_pdf):
        print("No test.pdf found, skipping test")
        return

    print("Testing MinerU + Pandoc conversion...")

    try:
        # Create a simple log queue
        log_queue = asyncio.Queue()

        # Define a coroutine to print logs
        async def print_logs():
            while True:
                try:
                    msg = await asyncio.wait_for(log_queue.get(), timeout=0.1)
                    print(f"[LOG] {msg}")
                except asyncio.TimeoutError:
                    break

        # Start conversion
        convert_id = await converter.convert(
            source_path=test_pdf,
            target_format="docx",
            quality="high",
            options={"use_mineru": True}
        )

        # Print logs
        await print_logs()

        # Get status
        status = converter.get_conversion_status(convert_id)
        print(f"Status: {status}")

        # Get output file
        output_file = converter.get_conversion_file(convert_id)
        if output_file:
            print(f"Output file: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_conversion())