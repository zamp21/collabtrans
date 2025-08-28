import asyncio
import json
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

from json_repair import json_repair

from docutranslate.agents import AgentConfig, Agent
from docutranslate.glossary.glossary import Glossary
from docutranslate.utils.json_utils import segments2json_chunks


@dataclass
class SegmentsTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


class SegmentsTranslateAgent(Agent):
    def __init__(self, config: SegmentsTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
Role
You are a professional machine translation engine.
Task
You will receive a sequence of segments to be translated, represented in JSON format. The keys are the segment IDs, and the values are the segments for translation.
You need to translate these segments into the target language.
Target language: {config.to_lang}
Requirements
The translation must be professional and accurate.
Do not output any explanations or annotations.
The format of the translated segments should be as close as possible to the source format.
For personal names and proper nouns, use the most commonly used words for translation. If there are multiple common translations, choose the word that comes first in dictionary order.
For special tags or other non-translatable elements (like codes, brand names, specific jargon), keep them in their original form.
If a segment is already in the target language, keep it as is.
Output
The translated sequence of segments, represented as JSON text (note: not a code block). The keys are the segment IDs, and the values are the translated segments.
The returned JSON text must be parsable by json.loads into a dictionary of the form {r'{"segment_id": "translation"}'}.
Example
Input
{r'{"0":"hello","1":"apple","2":true,"3":"false"}'}
Output
{r'{"0":"你好","1":"苹果","2":true,"3":"错误"}'}
Warning: Never wrap the entire JSON object in quotes to make it a single string. Never wrap the JSON text in ```.
"""
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\n'
        self.glossary_dict = config.glossary_dict

    def _pre_send_handler(self, system_prompt, prompt):
        if self.glossary_dict:
            glossary = Glossary(glossary_dict=self.glossary_dict)
            system_prompt += glossary.append_system_prompt(prompt)
        return system_prompt, prompt

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        if result == "":
            return {}
        try:
            result = json_repair.loads(result)
            if not isinstance(result, dict):
                raise ValueError(f"agent返回结果不是dict的json形式,result:{result}")
        except RuntimeError as e:
            raise ValueError(f"结果不能正确解析:{e.__repr__()}")
        return result

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        if origin_prompt == "":
            return {}
        try:
            return json_repair.loads(origin_prompt)
        except:
            logger.error("prompt不是json格式")
            return origin_prompt

    def send_segments(self, segments: list[str], chunk_size: int):
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        translated_chunks = super().send_prompts(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                 result_handler=self._result_handler,
                                                 error_result_handler=self._error_result_handler)
        indexed_translated = indexed_originals.copy()
        for chunk in translated_chunks:
            try:
                for key, val in chunk.items():
                    if key in indexed_translated:
                        indexed_translated[key] = val
            except JSONDecodeError as e:
                self.logger.info(f"json解析错误，解析文本:{chunk}，错误:{e.__repr__()}")
            except ValueError as e:
                self.logger.info(f"value错误，更新对象:{indexed_translated}，错误:{e.__repr__()}")
            except Exception as e:
                self.logger.info(f"send_segments发生错误:{e.__repr__()}")

        # 初始化结果列表
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            # 添加未处理的部分
            result.extend(ls[last_end:start])
            # 合并切片范围内的元素
            merged_item = "".join(ls[start:end])
            result.append(merged_item)
            last_end = end

        # 添加剩余部分
        result.extend(ls[last_end:])
        return result

    # todo:增加协程粒度
    async def send_segments_async(self, segments: list[str], chunk_size: int):
        indexed_originals, chunks, merged_indices_list = await asyncio.to_thread(segments2json_chunks, segments,
                                                                                 chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        translated_chunks = await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)
        indexed_translated = indexed_originals.copy()
        for chunk in translated_chunks:
            try:
                for key, val in chunk.items():
                    if key in indexed_translated:
                        indexed_translated[key] = str(val)
            except JSONDecodeError as e:
                self.logger.info(f"json解析错误，解析文本:{chunk}，错误:{e.__repr__()}")
            except ValueError as e:
                self.logger.info(f"value错误，更新对象:{indexed_translated}，错误:{e.__repr__()}")
            except Exception as e:
                self.logger.info(f"send_segments发生错误:{e.__repr__()}")

        # 初始化结果列表
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            # 添加未处理的部分
            result.extend(ls[last_end:start])
            # 合并切片范围内的元素
            merged_item = "".join(ls[start:end])
            result.append(merged_item)
            last_end = end

        # 添加剩余部分
        result.extend(ls[last_end:])
        return result

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
