# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from typing import Self, Literal, Set, Dict, List, Tuple

from bs4 import BeautifulSoup, NavigableString, Comment

from collabtrans.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from collabtrans.ir.document import Document
from collabtrans.translator.ai_translator.base import AiTranslatorConfig, AiTranslator

# --- Rule Definitions ---

# 1. Non-translatable tags (blacklist)
# These tags and their content should not be translated under any circumstances, as they usually contain code, styles, or metadata.
# During preprocessing, these tags and all their child elements will be directly removed from the document to ensure they are not accidentally modified.
NON_TRANSLATABLE_TAGS: Set[str] = {
    'script',  # JavaScript code
    'style',  # CSS styles
    'pre',  # Preformatted text, usually for code blocks
    'code',  # Inline code
    'kbd',  # Keyboard input
    'samp',  # Sample output
    'var',  # Variables
    'noscript',  # Content when script is not enabled
    'meta',  # Metadata
    'link',  # External resource links
    'head',  # Document head, usually doesn't contain visible translatable content
}

# 2. Translatable tags (whitelist)
# Define a set of HTML tags considered "safe", where direct text content is suitable for translation.
# This whitelist strategy combined with the blacklist above provides double protection.
SAFE_TAGS: Set[str] = {
    'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'li', 'blockquote', 'q', 'caption',
    'span', 'a', 'strong', 'em', 'b', 'i', 'u',
    'td', 'th',
    'button', 'label', 'legend', 'option',
    'figcaption', 'summary', 'details',
    'div',  # div is quite general, but our logic only extracts its top-level text nodes, which is relatively safe
}

# 3. Translatable attributes (whitelist)
# Define a set of "safe" attributes whose values are usually readable text for users.
# Format: { 'tag_name': ['attr1', 'attr2'], ... }
SAFE_ATTRIBUTES: Dict[str, List[str]] = {
    'img': ['alt', 'title'],
    'a': ['title'],
    'input': ['placeholder', 'title'],
    'textarea': ['placeholder', 'title'],
    'abbr': ['title'],
    'area': ['alt'],
    # For all tags, title attribute is usually translatable
    '*': ['title']
}


@dataclass
class HtmlTranslatorConfig(AiTranslatorConfig):
    """
    Configuration class for HTML translator.

    Attributes:
        insert_mode (Literal["replace", "append", "prepend"]):
            Specify how to insert translated text.
            - "replace": Replace original text with translation.
            - "append": Append translation after original text.
            - "prepend": Prepend translation before original text.
        separator (str): String used to separate original and translated text in "append" or "prepend" mode.
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = " "  # Using space as default separator in HTML may be more appropriate


class HtmlTranslator(AiTranslator):
    """
    A translator for translating HTML file content.
    It adopts a blacklist and whitelist combined strategy to maximize page style and functionality preservation:
    1. Blacklist: First, completely remove script, style, code and other clearly non-translatable tags and their content.
    2. Whitelist: Then, in the remaining HTML, only extract and translate text content in specified safe tags and attributes.
    3. Comment protection: Explicitly skip HTML comments to ensure they are not translated.
    This method effectively avoids breaking page structure, scripts, styles and comments.
    """

    def __init__(self, config: HtmlTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt,
                to_lang=config.to_lang,
                base_url=config.base_url,
                api_key=config.api_key,
                model_id=config.model_id,
                temperature=config.temperature,
                thinking=config.thinking,
                concurrent=config.concurrent,
                timeout=config.timeout,
                logger=self.logger,
                glossary_dict=config.glossary_dict,
                retry=config.retry
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> Tuple[BeautifulSoup, List[Dict], List[str]]:
        """
        Parse HTML document and extract all text nodes and attributes that need translation according to rules.
        Steps:
        1. Use blacklist to remove all non-translatable tags, fundamentally preventing them from being processed.
        2. Traverse remaining HTML elements, extract translatable text and attribute values according to whitelist, while skipping comments.
        """
        soup = BeautifulSoup(document.content, 'lxml')

        # Step 1: Remove all non-translatable tags and their content
        for tag in soup.find_all(NON_TRANSLATABLE_TAGS):
            tag.decompose()

        translatable_items = []
        original_texts = []

        # Step 2: Traverse all remaining tags, extract translatable content
        for tag in soup.find_all(True):
            # --- 2a. Translate text nodes within safe tags ---
            if tag.name in SAFE_TAGS:
                # Only process text in direct child nodes of tags, this is key to preserving styles.
                for child in list(tag.children):
                    # [Key modification] Ensure processing pure text nodes, not comments (Comment is a subclass of NavigableString)
                    if isinstance(child, NavigableString) and not isinstance(child, Comment) and child.strip():
                        text = str(child)
                        translatable_items.append({'type': 'node', 'object': child})
                        original_texts.append(text)

            # --- 2b. Translate safe attributes within safe tags ---
            attributes_to_check = SAFE_ATTRIBUTES.get(tag.name, []) + SAFE_ATTRIBUTES.get('*', [])
            for attr in set(attributes_to_check):  # Use set to deduplicate
                if tag.has_attr(attr) and tag[attr].strip():
                    value = tag[attr]
                    translatable_items.append({'type': 'attribute', 'tag': tag, 'attribute': attr})
                    original_texts.append(value)

        return soup, translatable_items, original_texts

    def _after_translate(self, soup: BeautifulSoup, translatable_items: list,
                         translated_texts: list[str], original_texts: list[str]) -> bytes:
        """
        Write translated text back to corresponding nodes or attributes in BeautifulSoup object and return final HTML byte stream.
        """
        if len(translatable_items) != len(translated_texts):
            self.logger.error("Number of text segments before and after translation don't match (%d vs %d), skipping write operation to prevent file corruption.",
                              len(translatable_items), len(translated_texts))
            return soup.encode('utf-8')

        for i, item in enumerate(translatable_items):
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            new_content = ""
            if self.insert_mode == "replace":
                if item['type'] == 'node':
                    # For text nodes, preserve leading and trailing whitespace from original text, which is crucial for maintaining inline element spacing.
                    leading_space = original_text[:len(original_text) - len(original_text.lstrip())]
                    trailing_space = original_text[len(original_text.rstrip()):]
                    new_content = leading_space + translated_text + trailing_space
                else:  # Attribute
                    new_content = translated_text

            elif self.insert_mode == "append":
                new_content = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                new_content = translated_text + self.separator + original_text
            else:
                self.logger.error(f"Invalid HtmlTranslatorConfig parameter: insert_mode='{self.insert_mode}'")
                new_content = original_text  # Restore original text on error

            # Write content back based on type
            if item['type'] == 'node':
                node = item['object']
                # Check if node is still in parse tree to prevent issues during processing
                if node.parent:
                    node.replace_with(NavigableString(new_content))
            elif item['type'] == 'attribute':
                tag = item['tag']
                attr = item['attribute']
                tag[attr] = new_content

        # Encode modified BeautifulSoup object to utf-8 byte stream
        return soup.encode('utf-8')

    def translate(self, document: Document) -> Self:
        """
        Synchronously translate HTML document.
        """
        soup, translatable_items, original_texts = self._pre_translate(document)
        if not translatable_items:
            self.logger.info("\nNo translatable content found in HTML file that meets safety rules.")
            # Even without translation content, return cleaned document content (removed non-translatable tags)
            document.content = soup.encode('utf-8')
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        document.content = self._after_translate(soup, translatable_items, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        Asynchronously translate HTML document.
        """
        soup, translatable_items, original_texts = await asyncio.to_thread(self._pre_translate, document)

        if not translatable_items:
            self.logger.info("\nNo translatable content found in HTML file that meets safety rules.")
            document.content = await asyncio.to_thread(soup.encode, 'utf-8')
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        document.content = await asyncio.to_thread(
            self._after_translate, soup, translatable_items, translated_texts, original_texts
        )
        return self
