import json
from dataclasses import dataclass
from typing import Self, Any

from jsonpath_ng import parse

from docutranslate.agents.segments_agent import JsonTranslateAgentConfig, JsonTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig
from docutranslate.translator.base import Translator
from docutranslate.utils.json_utils import flat_json_split


@dataclass
class JsonTranslatorConfig(AiTranslatorConfig):
    jsonpaths: list[str]


class JsonTranslator(Translator):
    def __init__(self, config: JsonTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        agent_config = JsonTranslateAgentConfig(custom_prompt=config.custom_prompt,
                                                to_lang=config.to_lang,
                                                baseurl=config.base_url,
                                                key=config.api_key,
                                                model_id=config.model_id,
                                                system_prompt=None,
                                                temperature=config.temperature,
                                                thinking=config.thinking,
                                                max_concurrent=config.concurrent,
                                                timeout=config.timeout,
                                                logger=self.logger)
        self.translate_agent = JsonTranslateAgent(agent_config)
        self.jsonpaths = config.jsonpaths

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

    def _translate_texts_in_batches(self, texts: list[str]) -> list[str]:
        """
        将文本列表打包、分块、发送翻译并返回翻译结果。
        此函数封装了与翻译代理交互的所有细节。
        """
        # 1. 使用索引作为唯一ID，将文本列表转换为字典，便于API处理
        indexed_originals = {str(i): text for i, text in enumerate(texts)}

        # 2. 将大字典分割成小块，以满足API的限制
        chunks = flat_json_split(indexed_originals, self.chunk_size)

        # 3. 将每个块序列化为JSON字符串并发送翻译
        prompts = [json.dumps(chunk) for chunk in chunks]
        translated_chunks = self.translate_agent.send_prompts(prompts)

        # 4. 将翻译结果合并回一个字典
        # 我们从原始字典的副本开始，以确保即使翻译失败，我们也能保持结构
        indexed_translated = indexed_originals.copy()
        for chunk_str in translated_chunks:
            translated_part = json.loads(chunk_str)
            indexed_translated.update(translated_part)

        # 5. 按原始顺序返回翻译后的文本列表
        return list(indexed_translated.values())

    async def _translate_texts_in_batches_async(self, texts: list[str]) -> list[str]:
        """
        将文本列表打包、分块、发送翻译并返回翻译结果。
        此函数封装了与翻译代理交互的所有细节。
        """
        # 1. 使用索引作为唯一ID，将文本列表转换为字典，便于API处理
        indexed_originals = {str(i): text for i, text in enumerate(texts)}

        # 2. 将大字典分割成小块，以满足API的限制
        chunks = flat_json_split(indexed_originals, self.chunk_size)

        # 3. 将每个块序列化为JSON字符串并发送翻译
        prompts = [json.dumps(chunk) for chunk in chunks]
        translated_chunks = await self.translate_agent.send_prompts_async(prompts)

        # 4. 将翻译结果合并回一个字典
        # 我们从原始字典的副本开始，以确保即使翻译失败，我们也能保持结构
        indexed_translated = indexed_originals.copy()
        for chunk_str in translated_chunks:
            translated_part = json.loads(chunk_str)
            indexed_translated.update(translated_part)

        # 5. 按原始顺序返回翻译后的文本列表
        return list(indexed_translated.values())
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

        # 步骤 2: 批量翻译提取出的文本
        translated_texts = self._translate_texts_in_batches(original_texts)

        # 健壮性检查：确保翻译回来的项目数量与发送的一致
        if len(original_texts) != len(translated_texts):
            raise ValueError("翻译服务返回的项目数量与发送的数量不匹配。")

        # 步骤 3: 将翻译结果写回原始JSON对象
        self._update_content_with_translations(content, all_matches, translated_texts)

        # 更新原始 document 对象的内容（可选，但良好实践）
        document.content = json.dumps(content, ensure_ascii=False).encode('utf-8')

        return self

    # def translate(self, document: Document) -> Self:
    #     content = json.loads(document.content.decode())
    #     path_vals: dict[str:list[str]] = {}
    #     for jsonpath in self.jsonpaths:
    #         jsonpath_expr = parse(jsonpath)
    #         matches = [match.value for match in jsonpath_expr.find(content)]
    #         path_vals[jsonpath] = matches
    #     vals_all = []
    #     for vals in path_vals.values():
    #         vals_all.extend(vals)
    #     vals_dict = {str(i): val for i, val in enumerate(vals_all)}#{"1":"val1","2":"val2"}
    #     chunks=flat_json_split(vals_dict,self.chunk_size)
    #     chunks_translated=self.translate_agent.send_prompts([json.dumps(chunk) for chunk in chunks])
    #     for chunk in chunks_translated:
    #         vals_dict.update(json.loads(chunk))
    #
    #     #翻译后的{path1:[val1',val2']}
    #     reconstructed_dict = {}
    #     start_index = 0
    #     for key in path_vals.keys():
    #         length = len(path_vals[key])
    #         sub_list = list(vals_dict.values())[start_index: start_index + length]
    #         reconstructed_dict[key] = sub_list
    #         start_index += length
    #
    #     for path in reconstructed_dict:
    #         path_expression = parse(path)
    #         matches = path_expression.find(content)
    #         for idx,match in enumerate(matches):
    #             match.full_path.update(content, reconstructed_dict[path][idx])
    #     return self

    async def translate_async(self, document: Document) -> Self:
        content = json.loads(document.content.decode())

        # 步骤 1: 提取所有需要翻译的匹配项
        all_matches = self._extract_matches(content)

        if not all_matches:
            # 如果没有找到任何内容，则无需执行任何操作
            return self

        original_texts = [match.value for match in all_matches]

        # 步骤 2: 批量翻译提取出的文本
        translated_texts = await self._translate_texts_in_batches_async(original_texts)

        # 健壮性检查：确保翻译回来的项目数量与发送的一致
        if len(original_texts) != len(translated_texts):
            raise ValueError("翻译服务返回的项目数量与发送的数量不匹配。")

        # 步骤 3: 将翻译结果写回原始JSON对象
        self._update_content_with_translations(content, all_matches, translated_texts)

        # 更新原始 document 对象的内容（可选，但良好实践）
        document.content = json.dumps(content, ensure_ascii=False).encode('utf-8')
        return self
