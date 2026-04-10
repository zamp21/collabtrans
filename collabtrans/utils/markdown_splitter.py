# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import re
from typing import List




class MarkdownBlockSplitter:
    def __init__(self, max_block_size: int = 5000):
        """
        Initialize Markdown splitter

        Args:
            max_block_size: Maximum bytes per block
        """
        self.max_block_size = max_block_size

    @staticmethod
    def _get_bytes(text: str) -> int:
        return len(text.encode('utf-8'))

    def split_markdown(self, markdown_text: str) -> List[str]:
        """
        Split Markdown text into blocks of specified size
        Ensure original text can be reconstructed by simple concatenation (except for split code blocks)
        Try to keep headers and their corresponding content in the same block
        """
        # 1. Split text into logical blocks
        logical_blocks = self._split_into_logical_blocks(markdown_text)

        # 2. Merge logical blocks so they don't exceed max_block_size
        chunks = []
        current_chunk_parts = []
        current_size = 0

        for block in logical_blocks:
            block_size = self._get_bytes(block)

            # Case 1: Block itself is too large
            if block_size > self.max_block_size:
                # First output currently accumulated blocks
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))
                    current_chunk_parts = []
                    current_size = 0

                # Split this oversized block and add directly to results
                chunks.extend(self._split_large_block(block))
                continue

            # Case 2: Adding this block to current chunk would exceed limit
            if current_size + block_size > self.max_block_size:
                if current_chunk_parts:
                    chunks.append("".join(current_chunk_parts))

                current_chunk_parts = [block]
                current_size = block_size
            # Case 3: Normal addition
            else:
                current_chunk_parts.append(block)
                current_size += block_size

        # Add the last remaining chunk
        if current_chunk_parts:
            chunks.append("".join(current_chunk_parts))

        return chunks

    def _split_into_logical_blocks(self, markdown_text: str) -> List[str]:
        """
        Split Markdown text into logical blocks (headers, paragraphs, code blocks, HTML blocks, empty line separators, etc.)
        """
        # Normalize line breaks
        text = markdown_text.replace('\r\n', '\n')

        # Pattern to match code blocks and HTML blocks (like tables)
        # We need to protect these from being split incorrectly
        block_pattern = r'(```[\s\S]*?```|~~~[\s\S]*?~~~|<table[\s\S]*?</table>)'
        parts = re.split(block_pattern, text, flags=re.IGNORECASE)

        blocks = []
        for i, part in enumerate(parts):
            if not part:
                continue

            if i % 2 == 1:  # This is a code block or HTML table - keep as single unit
                blocks.append(part)
            else:  # This is regular Markdown content
                # Split by one or more empty lines and preserve separators
                # This effectively separates paragraphs, lists, headers, etc., and preserves empty lines between them
                sub_parts = re.split(r'(\n{2,})', part)
                # Filter out empty strings that re.split might produce
                blocks.extend([p for p in sub_parts if p])

        return blocks

    def _split_large_block(self, block: str) -> List[str]:
        """
        Split a single block that exceeds max_block_size
        HTML tables and code blocks should not be split
        """
        # HTML tables should not be split - return as single chunk even if oversized
        if block.strip().lower().startswith('<table') and block.strip().lower().endswith('</table>'):
            return [block]

        # Prioritize code blocks
        if block.startswith(('```', '~~~')):
            fence = '```' if block.startswith('```') else '~~~'
            lines = block.split('\n')
            header = lines[0]
            footer = lines[-1]
            content_lines = lines[1:-1]

            chunks = []
            current_chunk_lines = [header]
            current_size = self._get_bytes(header) + 1

            for line in content_lines:
                line_size = self._get_bytes(line) + 1
                if current_size + line_size + self._get_bytes(footer) > self.max_block_size:
                    current_chunk_lines.append(footer)
                    chunks.append('\n'.join(current_chunk_lines))
                    current_chunk_lines = [header, line]
                    current_size = self._get_bytes(header) + 1 + line_size
                else:
                    current_chunk_lines.append(line)
                    current_size += line_size

            if len(current_chunk_lines) > 1:
                current_chunk_lines.append(footer)
                chunks.append('\n'.join(current_chunk_lines))
            return chunks

        # Split regular large text by lines
        lines = block.split('\n')
        chunks = []
        current_chunk = []
        current_size = 0
        for line in lines:
            line_size = self._get_bytes(line) + 1
            if current_size + line_size > self.max_block_size and current_chunk:
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_size = line_size - 1  # -1 for the first line does not have a leading '\n'
            else:
                current_chunk.append(line)
                current_size += line_size

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks


def split_markdown_text(markdown_text: str, max_block_size=5000) -> List[str]:
    """
    Split Markdown string into blocks not exceeding max_block_size
    """
    splitter = MarkdownBlockSplitter(max_block_size=max_block_size)
    chunks = splitter.split_markdown(markdown_text)
    # Filter out blocks consisting only of whitespace characters
    return [chunk for chunk in chunks if chunk.strip()]


def _needs_single_newline_join(prev_chunk: str, next_chunk: str) -> bool:
    """
    Determine if two blocks should be joined with a single newline
    This usually happens between consecutive lines of lists, tables, quote blocks, or HTML elements
    """
    if not prev_chunk.strip() or not next_chunk.strip():
        return False

    last_line_prev = prev_chunk.rstrip().split('\n')[-1].lstrip()
    first_line_next = next_chunk.lstrip().split('\n')[0].lstrip()

    # Markdown Tables
    if last_line_prev.startswith('|') and last_line_prev.endswith('|') and \
            first_line_next.startswith('|') and first_line_next.endswith('|'):
        return True

    # Lists (unordered and ordered)
    list_markers = r'^\s*([-*+]|\d+\.)\s+'
    if re.match(list_markers, last_line_prev) and re.match(list_markers, first_line_next):
        return True

    # Quotes
    if last_line_prev.startswith('>') and first_line_next.startswith('>'):
        return True

    # HTML elements - if previous chunk ends with HTML tag or next starts with HTML tag
    # This handles cases where HTML tables or other elements are split
    html_end_pattern = r'</\w+>\s*$'
    html_start_pattern = r'^\s*<\w+'

    if re.search(html_end_pattern, prev_chunk, re.IGNORECASE) or \
       re.match(html_start_pattern, first_line_next, re.IGNORECASE):
        # Check if this looks like continuation of HTML content
        # Don't add extra newlines between HTML elements
        if '<table' in prev_chunk.lower() or '</table>' in prev_chunk.lower() or \
           '<table' in next_chunk.lower() or '</table>' in next_chunk.lower():
            return True

    return False


def join_markdown_texts(markdown_texts: List[str]) -> str:
    """
    Intelligently join Markdown block list
    """
    if not markdown_texts:
        return ""

    joined_text = markdown_texts[0]
    for i in range(1, len(markdown_texts)):
        prev_chunk = markdown_texts[i - 1]
        current_chunk = markdown_texts[i]

        # Determine whether to use single or double newline
        if _needs_single_newline_join(prev_chunk, current_chunk):
            separator = "\n"
        else:
            # Default to double newline to separate different blocks
            separator = "\n\n"

        joined_text += separator + current_chunk

    return joined_text


if __name__ == '__main__':
    from pathlib import Path
    from collabtrans.utils.markdown_utils import clean_markdown_math_block
    content=Path(r"C:\Users\jxgm\Desktop\3a8d8999-3e9d-4f32-a32c-5b0830bb4320\full.md").read_text()
    content=split_markdown_text(content)
    content=join_markdown_texts(content)

