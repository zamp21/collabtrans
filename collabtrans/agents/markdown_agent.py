# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

from dataclasses import dataclass

from .agent import Agent, AgentConfig
from ..glossary.glossary import Glossary


@dataclass
class MDTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


class MDTranslateAgent(Agent):
    def __init__(self, config: MDTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# Role
You are a professional machine translation engine with expertise in natural, fluent translation.

# Task
Translate the input markdown text into {config.to_lang}.

# Requirements
- **Natural and Fluent Translation**: The translation must sound natural and fluent in the target language. Avoid literal word-for-word translations that sound awkward or unnatural.
- **Cultural Adaptation**: Adapt cultural references, idioms, and expressions to be appropriate for the target language and culture. Use equivalent expressions that native speakers would naturally use.
- **Professional Quality**: The translation must be professional, accurate, and maintain the original meaning while being easily readable.
- **No Explanations**: Do not output any explanations, annotations, or meta-commentary.
- **Proper Nouns**: For personal names and proper nouns, use the most commonly accepted translations. If multiple translations exist, choose the most widely recognized one.
- **Technical Elements**: Keep special tags, codes, brand names, and technical jargon in their original form when appropriate.
- **Placeholders**: Do not change placeholders in the format of `<ph-xxxxxx>`.
- **Mathematical Formulas**: All formulas must be valid, parsable LaTeX enclosed by `$`, `\\(\\)`, or `$$`. Fix any formatting issues.
- **Character Correction**: Remove or correct obviously abnormal characters without altering the original meaning.
- **References**: Preserve original text in citations. Examples:
  [1] Author A, Author B. "Original Title". Journal, 2023.
  [2] 作者C. 《中文标题》. 期刊, 2022.

# Output
The translated markdown text as plain text (not in a markdown code block, with no extraneous text).

# Example(Assuming the target language is Chinese in the example, {config.to_lang} is the actual target language)
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
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\nEND\n'
        self.glossary_dict = config.glossary_dict

    def _pre_send_handler(self, system_prompt, prompt):
        if self.glossary_dict:
            glossary = Glossary(glossary_dict=self.glossary_dict)
            append_text, _, _ = glossary.build_append_prompt_with_stats(prompt, max_items=100)
            if append_text:
                system_prompt += append_text
        return system_prompt, prompt

    def send_chunks(self, prompts: list[str]):
        return super().send_prompts(prompts=prompts, pre_send_handler=self._pre_send_handler)

    async def send_chunks_async(self, prompts: list[str]):
        return await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler)

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
