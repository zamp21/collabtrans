import asyncio
import json
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

from json_repair import json_repair

from docutranslate.agents import AgentConfig, Agent
from docutranslate.utils.json_utils import segments2json_chunks


@dataclass
class SegmentsTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None


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
        if config.custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + config.custom_prompt + '\n'

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        try:
            result = json_repair.loads(result)
            if not isinstance(result,dict):
                raise ValueError("agent返回结果不是dict的json形式")
        except:
            logger.error("结果不能正确解析")
            return self._error_result_handler(origin_prompt, logger)
        return result

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        try:
            return json_repair.loads(origin_prompt)
        except:
            logger.error("prompt不是json格式")
            return origin_prompt

    def send_segments(self, segments: list[str], chunk_size: int):
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        translated_chunks = super().send_prompts(prompts=prompts, result_handler=self._result_handler,
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
        translated_chunks = await super().send_prompts_async(prompts=prompts, result_handler=self._result_handler,
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
