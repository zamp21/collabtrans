import json
from dataclasses import dataclass

from docutranslate.agents import AgentConfig, Agent
from docutranslate.utils.json_utils import flat_json_split


@dataclass
class SegmentsTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None


class SegmentsTranslateAgent(Agent):
    def __init__(self, config: SegmentsTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# 角色
你是一个专业的机器翻译引擎
# 工作
你接收一个待翻译片段的序列，以json格式表示。其中键是待片段的编号，值是待翻译片段。
你需要将待翻译片段翻译成目标语言。
目标语言:{config.to_lang}
# 要求
翻译要求专业准确
不输出任何解释和注释
翻译后的片段应该与源格式尽量相同
如果待翻译片段已经是目标语言，则保持原样
# 输出
翻译后的片段序列，以json格式表示。其中键是片段编号，值是翻译后的片段
# 示例
## 输入
{r'{"0":"hello","1":"apple","2":true,"3":"false"}'}
## 输出
{r'{"0":"你好","1":"苹果","2":true,"3":"错误"}'}
"""
        if config.custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + config.custom_prompt + '\n'

    def send_segments(self, segments: list[str], chunk_size: int):
        indexed_originals = {str(i): text for i, text in enumerate(segments)}
        chunks = flat_json_split(indexed_originals, chunk_size)
        prompts = [json.dumps(chunk) for chunk in chunks]
        translated_chunks = super().send_prompts(prompts=prompts)
        indexed_translated = indexed_originals.copy()
        for chunk_str in translated_chunks:
            translated_part = json.loads(chunk_str)
            indexed_translated.update(translated_part)
        return list(indexed_translated.values())

    #todo:增加协程粒度
    async def send_segments_async(self, segments: list[str], chunk_size: int):
        indexed_originals = {str(i): text for i, text in enumerate(segments)}
        chunks = flat_json_split(indexed_originals, chunk_size)
        prompts = [json.dumps(chunk) for chunk in chunks]
        translated_chunks = await super().send_prompts_async(prompts=prompts)
        indexed_translated = indexed_originals.copy()
        for chunk_str in translated_chunks:
            translated_part = json.loads(chunk_str)
            indexed_translated.update(translated_part)
        return list(indexed_translated.values())
