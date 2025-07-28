from dataclasses import dataclass
from logging import Logger


@dataclass
class AiTranslateConfig:
    base_url: str
    api_key: str
    model_id: str
    to_lang: str
    custom_prompt: str | None = None
    temperature: float = 0.7
    timeout: int = 2000
    chunk_size: int = 3000
    concurrent: int = 30
    logger: Logger | None = None