from typing import NotRequired, Unpack

from docutranslate.agents import AgentArgs, Agent


class TXTTranslateAgentArgs(AgentArgs, total=True):
    to_lang: str
    custom_prompt: NotRequired[str]


class TXTTranslateAgent(Agent):
    def __init__(self, custom_prompt=None, to_lang="中文", **kwargs: Unpack[AgentArgs]):
        super().__init__(**kwargs)
        self.system_prompt = f"""
# 角色
你是一个专业的机器翻译引擎
# 工作
翻译输入的txt文本
目标语言{to_lang}
# 要求
翻译要求专业准确
不输出任何解释和注释
不能改变形如<ph-xxxxxx>的占位符
# 输出
翻译后的txt译文纯文本
"""
        if custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + custom_prompt + '\n'
        self.system_prompt += r'\no_think'
