from dataclasses import dataclass

from docutranslate.agents import AgentConfig, Agent


@dataclass
class JsonTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None


class JsonTranslateAgent(Agent):
    def __init__(self, config: JsonTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# 角色
你是一个专业的机器翻译引擎
# 工作
翻译输入的json的值，保持键不改变
目标语言:{config.to_lang}
# 要求
翻译要求专业准确
不输出任何解释和注释
如果已经是目标语言，则保持原样
# 输出
翻译后的json纯文本
# 示例
## 输入
{r'{"1":"hello","2":"apple","3":true,"4":"false"}'}
## 输出
{r'{"1":"你好","2":"苹果","3":true,"4":"错误"}'}
"""
        if config.custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + config.custom_prompt + '\n'
