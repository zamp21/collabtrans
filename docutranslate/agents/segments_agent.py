import json
from json_repair import json_repair
from dataclasses import dataclass
from json import JSONDecodeError

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
翻译后的片段序列，以json文本表示（注意不是代码块）。其中键是片段编号，值是翻译后的片段。
返回的json文本必须能被json.loads转换为形如{{"片段编号":"译文"}}的字典。
# 示例
## 输入
{r'{"0":"hello","1":"apple","2":true,"3":"false"}'}
## 输出
{r'{"0":"你好","1":"苹果","2":true,"3":"错误"}'}
# 错误输出示例
"{r'"{\"0\":\"你好\",\"1\":\"苹果\"}"'}"
# 正确输出示例
{r'{"0":"你好","1":"苹果"}'}
警告：绝不要将整个JSON对象用引号包裹成一个字符串。
"""
        if config.custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + config.custom_prompt + '\n'

    def send_segments(self, segments: list[str], chunk_size: int):
        indexed_originals = {str(i): text for i, text in enumerate(segments)}
        chunks = flat_json_split(indexed_originals, chunk_size)
        prompts = [json.dumps(chunk,ensure_ascii=False) for chunk in chunks]
        translated_chunks = super().send_prompts(prompts=prompts)
        indexed_translated = indexed_originals.copy()
        for chunk_str in translated_chunks:
            try:
                translated_part = json_repair.loads(chunk_str)
                for key,val in translated_part:
                    if key in indexed_translated:
                        indexed_translated[key]=val
            except JSONDecodeError as e:
                self.logger.info(f"json解析错误，解析文本:{chunk_str}，错误:{e.__repr__()}")
            except ValueError as e:
                self.logger.info(f"value错误，更新对象:{indexed_translated}，错误:{e.__repr__()}")

        return list(indexed_translated.values())

    #todo:增加协程粒度
    async def send_segments_async(self, segments: list[str], chunk_size: int):
        indexed_originals = {str(i): text for i, text in enumerate(segments)}
        chunks = flat_json_split(indexed_originals, chunk_size)
        prompts = [json.dumps(chunk,ensure_ascii=False) for chunk in chunks]
        translated_chunks = await super().send_prompts_async(prompts=prompts)
        indexed_translated = indexed_originals.copy()
        for chunk_str in translated_chunks:
            try:
                translated_part:dict = json_repair.loads(chunk_str)
                for key,val in translated_part.items():
                    if key in indexed_translated:
                        indexed_translated[key]=val
            except JSONDecodeError as e:
                self.logger.error(f"json解析错误，解析文本:{chunk_str}，错误:{e.__repr__()}")
            except ValueError as e:
                self.logger.error(f"value错误，更新对象:{indexed_translated}，错误:{e.__repr__()}")
            except AttributeError as e:
                self.logger.error(f"属性错误,chunk_str:{chunk_str}，错误:{e.__repr__()}")

        return list(indexed_translated.values())
