from dataclasses import dataclass

from docutranslate.agents import AgentConfig, Agent
from docutranslate.glossary.glossary import Glossary


@dataclass
class TXTTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


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
        self.custom_prompt = config.custom_prompt
        if config.custom_prompt:
            self.system_prompt += "\n# **Important rules or background** \n" + self.custom_prompt + '\n'
        self.glossary_dict = config.glossary_dict

    def _pre_send_handler(self, system_prompt, prompt):
        if self.glossary_dict:
            glossary = Glossary(glossary_dict=self.glossary_dict)
            system_prompt += glossary.append_system_prompt(prompt)
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
