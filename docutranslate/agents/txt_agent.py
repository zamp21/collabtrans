from dataclasses import dataclass

from docutranslate.agents import AgentConfig, Agent


@dataclass
class TXTTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None


class TXTTranslateAgent(Agent):
    def __init__(self, config: TXTTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# 角色
你是一个专业的机器翻译引擎
# 工作
翻译输入的txt文本
目标语言{config.to_lang}
# 要求
翻译要求专业准确
不输出任何解释和注释
不能改变形如<ph-xxxxxx>的占位符
# 输出
翻译后的txt译文纯文本
"""
        if config.custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + config.custom_prompt + '\n'
