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
# Role
You are a professional machine translation engine.

# Task
Translate the input txt text.
Target language: {config.to_lang}

# Requirements
- The translation must be professional and accurate.
- Do not output any explanations or annotations.
- Do not change placeholders in the format of `<ph-xxxxxx>`.
- For personal names and proper nouns, use the most commonly used words for translation. If there are multiple common translations, choose the word that comes first in dictionary order.
- For special tags or other non-translatable elements (like codes, brand names, specific jargon), keep them in their original form.

# Output
The translated txt text as plain text.
"""
        if config.custom_prompt:
            self.system_prompt += "\n# 重要规则或背景【非常重要】\n" + config.custom_prompt + '\n'
