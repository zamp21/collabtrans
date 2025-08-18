import asyncio
from dataclasses import dataclass
from typing import Self, Literal, List, Dict, Any

# 新增导入
from bs4 import BeautifulSoup, NavigableString

from markdown_it import MarkdownIt
from markdown_it.token import Token

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig
from docutranslate.translator.base import Translator


@dataclass
class MDTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace"] = "replace"
    translate_code_blocks: bool = False


class MDTranslator(Translator):
    def __init__(self, config: MDTranslatorConfig):
        super().__init__(config=config)
        # ... (构造函数的其余部分保持不变)
        self.chunk_size = config.chunk_size
        agent_config = SegmentsTranslateAgentConfig(
            custom_prompt=config.custom_prompt,
            to_lang=config.to_lang,
            baseurl=config.base_url,
            key=config.api_key,
            model_id=config.model_id,
            system_prompt=None,
            temperature=config.temperature,
            thinking=config.thinking,
            max_concurrent=config.concurrent,
            timeout=config.timeout,
            logger=self.logger
        )
        self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.translate_agent.system_prompt+="对于参考文献，保持源语言不翻译"
        self.config = config
        # 启用 HTML 解析是安全的
        self.md_parser = MarkdownIt("commonmark", {'html': True})

    def _pre_translate(self, document: Document) -> tuple[
        List[Token], List[Dict[str, Any]], List[str], Dict[int, BeautifulSoup]]:
        """
        预处理步骤：解析 Markdown 和嵌入的 HTML，提取所有可翻译的纯文本。
        """
        markdown_content = document.content.decode('utf-8')
        tokens = self.md_parser.parse(markdown_content)

        segments_to_translate = []
        original_texts = []
        # 新增：用于缓存已解析的 HTML DOM 树，避免重复解析
        parsed_html_cache = {}

        for i, token in enumerate(tokens):
            # --- 分支 1: 处理标准 Markdown 内容 ---
            if token.type == 'inline' and token.content:
                for child_idx, child in enumerate(token.children):
                    if child.type == 'text' and child.content.strip():
                        segment_info = {
                            "type": "markdown",  # 标记为 markdown 类型
                            "token_index": i,
                            "child_index": child_idx,
                        }
                        segments_to_translate.append(segment_info)
                        original_texts.append(child.content)

            # --- 分支 2: 新增逻辑，处理嵌入的 HTML 块 ---
            elif token.type == 'html_block' and token.content:
                # 使用 BeautifulSoup 解析 HTML 内容
                soup = BeautifulSoup(token.content, 'lxml')
                parsed_html_cache[i] = soup  # 缓存解析后的对象

                # 查找所有文本节点 (NavigableString)
                # 我们只翻译可见的、非空的文本内容
                for text_node in soup.find_all(string=True):
                    if isinstance(text_node, NavigableString) and text_node.strip():
                        # 排除脚本和样式表内的文本
                        if text_node.parent.name in ['script', 'style']:
                            continue

                        segment_info = {
                            "type": "html",  # 标记为 html 类型
                            "token_index": i,  # 记录 html_block token 的索引
                            "node": text_node,  # 直接引用文本节点对象
                        }
                        segments_to_translate.append(segment_info)
                        original_texts.append(text_node.string)

        return tokens, segments_to_translate, original_texts, parsed_html_cache

    def _after_translate(self, tokens: List[Token], segments_to_translate: List[Dict[str, Any]],
                         translated_texts: List[str], parsed_html_cache: Dict[int, BeautifulSoup]) -> bytes:
        """
        翻译后处理步骤：将翻译后的文本分别写回 Markdown AST 和 HTML DOM，然后重新渲染。
        """
        for i, segment_info in enumerate(segments_to_translate):
            translated_text = translated_texts[i]
            token_index = segment_info["token_index"]

            # --- 分支 1: 写回 Markdown Token ---
            if segment_info["type"] == "markdown":
                child_index = segment_info["child_index"]
                tokens[token_index].children[child_index].content = translated_text

            # --- 分支 2: 写回 HTML DOM (BeautifulSoup 对象) ---
            elif segment_info["type"] == "html":
                # 使用之前引用的节点对象，直接替换其内容
                segment_info["node"].replace_with(translated_text)

        # --- 新增步骤: 将修改后的 BeautifulSoup 对象渲染回字符串，更新 token ---
        for token_index, soup in parsed_html_cache.items():
            # 将 soup 对象转换回字符串，prettify() 会进行格式化，str() 则不会
            tokens[token_index].content = str(soup)

        renderer = self.md_parser.renderer
        translated_markdown = renderer.render(tokens, self.md_parser.options, {})
        return translated_markdown.encode('utf-8')

    def translate(self, document: Document) -> Self:
        tokens, segments, originals, cache = self._pre_translate(document)
        if not originals:
            self.logger.info("\n文件中没有找到需要翻译的纯文本内容。")
            return self

        translated = self.translate_agent.send_segments(originals, self.chunk_size)
        document.content = self._after_translate(tokens, segments, translated, cache)
        return self

    async def translate_async(self, document: Document) -> Self:
        tokens, segments, originals, cache = await asyncio.to_thread(self._pre_translate, document)
        if not originals:
            self.logger.info("\n文件中没有找到需要翻译的纯文本内容。")
            return self

        translated = await self.translate_agent.send_segments_async(originals, self.chunk_size)
        document.content = await asyncio.to_thread(self._after_translate, tokens, segments, translated, cache)
        return self