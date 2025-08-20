from dataclasses import dataclass

from .agent import Agent, AgentConfig

@dataclass
class MDTranslateAgentConfig(AgentConfig):
    to_lang:str
    custom_prompt:str|None=None

class MDTranslateAgent(Agent):
    def __init__(self,config:MDTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# Role
You are a professional machine translation engine.

# Task
Translate the input markdown text.
Target language: {config.to_lang}

# Requirements
- The translation must be professional and accurate.
- Do not output any explanations or annotations.
- Do not change placeholders in the format of `<ph-xxxxxx>`.
- All formulas, regardless of length, must be represented as valid, parsable LaTeX. They must be correctly enclosed by `$`, `\\(\\)`, or `$$`. If a formula is not formatted correctly, you must fix it.
- Remove or correct any obviously abnormal characters, but without altering the original meaning.
- When citing references, strictly preserve the original text; do not translate them. Examples of reference formats are as follows:
  [1] Author A, Author B. "Original Title". Journal, 2023.
  [2] 作者C. 《中文标题》. 期刊, 2022.

# Output
The translated markdown text as plain text (not in a markdown code block, with no extraneous text).

# Example
## Target language is Chinese
Input:
hello, what's your nam*@e?
![photo title](<ph-abcdde>)
The equation is E=mc 2. This is famous.
1+1=2$$
(c_0,c_1_1,c_2^2)is a coordinate.

Output:
你好，你叫什么名字？
![图像标题](<ph-abcdde>)
这个方程是 $E=mc^2$。这很有名。
$$1+1=2$$
\\((c_0,c_1,c_2^2)\\)是一个坐标。"""
        if config.custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + config.custom_prompt + '\n'
