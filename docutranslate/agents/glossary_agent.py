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
        self.system_prompt = f"""
# Role
You are a professional machine translation engine.
# 角色
你是一个专业的术语表提取器

# Task
你会收到一个json格式的段落表，其中键是段落的序号，值是段落的内容。
你需要从这些段落中提取**人名**和**地名**，并翻译这些名词为{config.to_lang}语言。
最终输出一个名词原文:名词译文的术语表

# Requirements
- 特殊标签、形如`<ph-xxxxxx>`的标签不要添加到术语表
- 输出术语表的src必须与名词原文完全一致，dst是该名词的{config.to_lang}的译文
- 相同的src仅在术语表中添加一次，不能重复

# Output
输出格式是列表的json纯文本
{[{"src": "<名词原文>", "dst": "<名词译文>"}]}

#示例
## 输入(翻译为中文):
{{"0":"Jobs likes apples","1":"Bill Gates is sunbathing in Shanghai."}}
## 输出
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
        self.logger.info("开始提取术语表")
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
                result = result | glossary_dict
            except JSONDecodeError as e:
                self.logger.info(f"json解析错误，解析文本:{chunk}，错误:{e.__repr__()}")
            except Exception as e:
                self.logger.info(f"send_segments发生错误:{e.__repr__()}")
        self.logger.info("术语表提取完成")
        return result

    async def send_segments_async(self, segments: list[str], chunk_size: int):
        self.logger.info("开始术语表提取")
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
        print(f"术语表:\n{result}")
        self.logger.info("术语表提取完成")
        return result
