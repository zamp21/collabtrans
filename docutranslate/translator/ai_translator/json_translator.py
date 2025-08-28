import json
from dataclasses import dataclass
from typing import Self, Any

from jsonpath_ng.ext import parse

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


@dataclass
class JsonTranslatorConfig(AiTranslatorConfig):
    json_paths: list[str]


class JsonTranslator(AiTranslator):
    def __init__(self, config: JsonTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt,
                to_lang=config.to_lang,
                baseurl=config.base_url,
                key=config.api_key,
                model_id=config.model_id,
                temperature=config.temperature,
                thinking=config.thinking,
                max_concurrent=config.concurrent,
                timeout=config.timeout,
                logger=self.logger,
                glossary_dict=config.glossary_dict
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.jsonpaths = config.json_paths

    def _extract_matches(self, content: dict) -> list[Any]:
        """
        根据 self.jsonpaths 从 JSON 内容中提取所有匹配项。
        与原始代码不同，这里直接返回 Match 对象列表，它同时包含了值和路径信息。
        """
        all_matches = []
        for path_str in self.jsonpaths:
            path_expr = parse(path_str)
            matches = path_expr.find(content)
            all_matches.extend(matches)
        return all_matches

    def _update_content_with_translations(self, content: dict, matches: list[Any], translated_texts: list[str]):
        """
        使用翻译后的文本更新原始JSON内容。
        """
        # 使用 zip 将每个匹配项与其对应的翻译文本配对
        for match, translated_text in zip(matches, translated_texts):
            # match.full_path 包含了更新原始 content 所需的精确位置信息
            match.full_path.update(content, translated_text)

    def translate(self, document: Document) -> Self:
        """
        主方法：提取、翻译并更新JSON文档中的指定内容。

        流程:
        1. 解析输入的JSON文档。
        2. 提取所有符合jsonpath规则的匹配项 (Match对象)。
        3. 从匹配项中获取原始文本，并批量发送进行翻译。
        4. 将翻译回来的文本根据其原始位置，更新回JSON对象中。
        5. 将更新后的 content 写回 document
        """
        content = json.loads(document.content.decode())

        # 步骤 1: 提取所有需要翻译的匹配项
        all_matches = self._extract_matches(content)

        if not all_matches:
            # 如果没有找到任何内容，则无需执行任何操作
            return self

        original_texts = [match.value for match in all_matches]
        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)
        # 步骤 2: 批量翻译提取出的文本
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # 健壮性检查：确保翻译回来的项目数量与发送的一致
        if len(original_texts) != len(translated_texts):
            raise ValueError("翻译服务返回的项目数量与发送的数量不匹配。")

        # 步骤 3: 将翻译结果写回原始JSON对象
        self._update_content_with_translations(content, all_matches, translated_texts)

        # 更新原始 document 对象的内容（可选，但良好实践）
        document.content = json.dumps(content, ensure_ascii=False).encode('utf-8')

        return self

    # todo:增加协程粒度
    async def translate_async(self, document: Document) -> Self:
        content = json.loads(document.content.decode())

        # 步骤 1: 提取所有需要翻译的匹配项
        all_matches = self._extract_matches(content)

        if not all_matches:
            # 如果没有找到任何内容，则无需执行任何操作
            return self

        original_texts = [match.value for match in all_matches]

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

            # 步骤 2: 批量翻译提取出的文本
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # 健壮性检查：确保翻译回来的项目数量与发送的一致
        if len(original_texts) != len(translated_texts):
            raise ValueError("翻译服务返回的项目数量与发送的数量不匹配。")

        # 步骤 3: 将翻译结果写回原始JSON对象
        self._update_content_with_translations(content, all_matches, translated_texts)

        # 更新原始 document 对象的内容（可选，但良好实践）
        document.content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        return self
