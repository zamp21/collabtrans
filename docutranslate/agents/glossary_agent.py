# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import json
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

import json_repair

from docutranslate.agents import AgentConfig, Agent
from docutranslate.utils.json_utils import segments2json_chunks


@dataclass
class GlossaryAgentConfig(AgentConfig):
    to_lang: str


class GlossaryAgent(Agent):
    def __init__(self, config: GlossaryAgentConfig):
        super().__init__(config)
        self.to_lang = config.to_lang
        self.system_prompt = f"""
# Role
You are a professional glossary extractor

# Task
You will receive a JSON-formatted list of paragraphs where keys are paragraph numbers and values are paragraph contents.
You need to extract person names and location names from these paragraphs and translate these terms into {self.to_lang}.
Finally, output a glossary of original terms:translated terms

# Requirements
- Do not include special tags or tags formatted as `<ph-xxxxxx>` in the glossary
- The src in the output glossary must exactly match the original term, while dst is the {self.to_lang} translation of the term
- The same src should only appear once in the glossary without repetition
-Do not include common nouns in the glossary.

# Output
The output format should be plain JSON text in a list format
{[{"src": "<Original Term>", "dst": "<Translated Term>"}]}

# Example
## Input
{{"0":"Jobs likes apples","1":"Bill Gates is sunbathing in Shanghai."}}
## Output(Assuming the target language is Chinese)
{r'[{"src": "Jobs", "dst": "乔布斯"}, {"src": "Bill Gates", "dst": "比尔盖茨"}, {"src": "Shanghai", "dst": "上海"}]'}
"""

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger):
        if result == "":
            return []
        try:
            result = json_repair.loads(result)
            if not isinstance(result, list):
                raise ValueError("GlossaryAgent返回结果不是list的json形式")
        except:
            logger.error("结果不能正确解析")
            return self._error_result_handler(origin_prompt, logger)
        return result

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        if origin_prompt == "":
            return []
        try:
            return json_repair.loads(origin_prompt)
        except:
            logger.error("prompt不是json格式")
            return origin_prompt

    def send_segments(self, segments: list[str], chunk_size: int):
        self.logger.info(f"开始提取术语表,to_lang:{self.to_lang}")
        result = {}
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        translated_chunks = super().send_prompts(prompts=prompts,
                                                 result_handler=self._result_handler,
                                                 error_result_handler=self._error_result_handler)
        for chunk in translated_chunks:
            chunk: list[dict[str, str]]
            try:
                glossary_dict = {d["src"]: d["dst"] for d in chunk}
                result = glossary_dict | result
            except JSONDecodeError as e:
                self.logger.info(f"json解析错误，解析文本:{chunk}，错误:{e.__repr__()}")
            except Exception as e:
                self.logger.info(f"send_segments发生错误:{e.__repr__()}")
        self.logger.info("术语表提取完成")
        return result

    async def send_segments_async(self, segments: list[str], chunk_size: int):
        self.logger.info(f"开始提取术语表,to_lang:{self.to_lang}")
        result = {}
        indexed_originals, chunks, merged_indices_list = await asyncio.to_thread(segments2json_chunks, segments,
                                                                                 chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False) for chunk in chunks]
        translated_chunks = await super().send_prompts_async(prompts=prompts,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)
        for chunk in translated_chunks:
            chunk: list[dict[str, str]]
            try:
                glossary_dict = {d["src"]: d["dst"] for d in chunk}
                result = result | glossary_dict
            except JSONDecodeError as e:
                self.logger.info(f"json解析错误，解析文本:{chunk}，错误:{e.__repr__()}")
            except Exception as e:
                self.logger.info(f"send_segments发生错误:{e.__repr__()}")
        # print(f"术语表:\n{result}")
        self.logger.info("术语表提取完成")
        return result
