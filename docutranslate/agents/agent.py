import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Literal
from urllib.parse import urlparse

import httpx

from docutranslate.global_values import USE_PROXY
from docutranslate.logger import global_logger
from docutranslate.utils.utils import get_httpx_proxies

MAX_RETRY_COUNT = 2
MAX_TOTAL_ERROR_COUNT = 10

ThinkingMode = Literal["enable", "disable", "default"]


@dataclass(kw_only=True)
class AgentConfig:
    logger: logging.Logger
    baseurl: str
    key: str
    model_id: str
    system_prompt: str | None
    temperature: float = 0.7
    max_concurrent: int = 30
    timeout: int = 2000
    thinking: ThinkingMode = "default"


class TotalErrorCounter:
    def __init__(self, logger: logging.Logger):
        self.lock = Lock()
        self.count = 0
        self.logger = logger

    def add(self):
        self.lock.acquire()
        self.count += 1
        if self.count > MAX_TOTAL_ERROR_COUNT:
            self.logger.info(f"错误响应过多")
        self.lock.release()
        return self.reach_limit()

    def reach_limit(self):
        return self.count > MAX_TOTAL_ERROR_COUNT


# 仅使用多线程时用以计数
class PromptsCounter:
    def __init__(self, total: int, logger: logging.Logger):
        self.lock = Lock()
        self.count = 0
        self.total = total
        self.logger = logger

    def add(self):
        self.lock.acquire()
        self.count += 1
        self.logger.info(f"多线程-已完成：{self.count}/{self.total}")
        self.lock.release()


TIMEOUT = 600


class Agent:
    _think_factory = {
        "open.bigmodel.cn": ("thinking", {"type": "enabled"}, {"type": "disabled"}),
        "dashscope.aliyuncs.com": ("enable_thinking ", True, False),
        "ark.cn-beijing.volces.com": ("thinking", {"type": "enabled"}, {"type": "disabled"}),
        "https://generativelanguage.googleapis.com/v1beta/openai/": ("generationConfig",
                                                                     {"thinkingConfig": {"thinkingBudget": -1}},
                                                                     {"thinkingConfig": {"thinkingBudget": 0}})
    }

    def __init__(self, config: AgentConfig):

        self.baseurl = config.baseurl.strip()
        if self.baseurl.endswith("/"):
            self.baseurl = self.baseurl[:-1]
        self.domain = urlparse(self.baseurl).netloc
        self.key = config.key.strip() or "xx"
        self.model_id = config.model_id.strip()
        self.system_prompt = config.system_prompt or ""
        self.temperature = config.temperature
        if USE_PROXY:
            self.client = httpx.Client(proxies=get_httpx_proxies(), verify=False)
            self.client_async = httpx.AsyncClient(proxies=get_httpx_proxies(), verify=False)
        else:
            self.client = httpx.Client(trust_env=False, proxy=None, verify=False)
            self.client_async = httpx.AsyncClient(trust_env=False, proxy=None, verify=False)

        self.max_concurrent = config.max_concurrent
        self.timeout = config.timeout
        self.thinking = config.thinking
        self.logger = config.logger or global_logger
        self.total_error_counter = TotalErrorCounter(logger=self.logger)

    def _add_thinking_mode(self, data: dict):
        if self.domain not in self._think_factory:
            return
        field_thinking, val_enable, val_disable = self._think_factory[self.domain]
        if self.thinking == "enable":
            data[field_thinking] = val_enable
        elif self.thinking == "disable":
            data[field_thinking] = val_disable

    def _prepare_request_data(self, prompt: str, system_prompt: str, temperature=None, top_p=0.9):
        if temperature is None:
            temperature = self.temperature
        headers = {"Content-Type": "application/json",
                   "Authorization": f"Bearer {self.key}"}
        data = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                # {"role": "system", "content": "所有回复必须以【SSS】开头（这是最高规则，适用于之后的所有例子）。示例：【SSS】这是示例回答\n"+system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "top_p": top_p,
        }
        if self.thinking != "default":
            self._add_thinking_mode(data)
        return headers, data

    async def send_async(self, prompt: str, system_prompt: None | str = None, retry=True, retry_count=0) -> str:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if prompt.strip() == "":
            return prompt
        headers, data = self._prepare_request_data(prompt, system_prompt)

        try:
            response = await self.client_async.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            return result
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"AI请求错误 (async): {e.response.status_code} - {e.response.text}")
            print(f"prompt:\n{prompt}")
            self.total_error_counter.add()
            return prompt
        except httpx.RequestError as e:
            self.logger.warning(f"AI请求连接错误 (async): {repr(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"AI响应格式错误 (async): {repr(e)}")
        # 如果没有正常获取结果则重试
        if retry and retry_count < MAX_RETRY_COUNT:
            if self.total_error_counter.add():
                return prompt
            self.logger.info(f"正在重试，重试次数{retry_count}")
            await asyncio.sleep(0.5)
            return await self.send_async(prompt, system_prompt, retry=True, retry_count=retry_count + 1)
        else:
            self.logger.error(f"达到重试次数上限")
            return prompt

    async def send_prompts_async(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            max_concurrent: int | None = None  # 新增参数，默认并发数为5
    ) -> list[str]:
        max_concurrent = self.max_concurrent if max_concurrent is None else max_concurrent
        total = len(prompts)
        self.logger.info(f"base-url:{self.baseurl},model-id:{self.model_id}")
        self.logger.info(f"预计发送{total}个请求，并发请求数:{max_concurrent}")
        count = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        # 辅助协程，用于包装 self.send_async 并使用信号量
        async def send_with_semaphore(p_text: str):
            async with semaphore:  # 在进入代码块前获取信号量，退出时释放
                result = await self.send_async(
                    prompt=p_text,
                    system_prompt=system_prompt,
                )
                nonlocal count
                count += 1
                self.logger.info(f"协程-已完成{count}/{total}")
                return result

        for p_text in prompts:
            task = asyncio.create_task(send_with_semaphore(p_text))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=False)
        return results

    def send(self, prompt: str, system_prompt: None | str = None, retry=True, retry_count=0) -> str:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if prompt.strip() == "":
            return prompt
        headers, data = self._prepare_request_data(prompt, system_prompt)
        try:
            response = self.client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]
            return result
        except httpx.HTTPStatusError as e:
            self.logger.warning(f"AI请求错误 (async): {e.response.status_code} - {e.response.text}")
            print(f"prompt:\n{prompt}")
            self.total_error_counter.add()
            return prompt
        except httpx.RequestError as e:
            self.logger.warning(f"AI请求连接错误 (sync): {repr(e)}\nprompt:{prompt}")
        except (KeyError, IndexError) as e:
            raise Exception(f"AI响应格式错误 (sync): {repr(e)}")
        # 如果没有正常获取结果则重试
        if retry and retry_count < MAX_RETRY_COUNT:
            if self.total_error_counter.add():
                return prompt
            self.logger.info(f"正在重试，重试次数{retry_count}")
            time.sleep(0.5)
            return self.send(prompt, system_prompt, retry=True, retry_count=retry_count + 1)
        else:
            self.logger.error(f"达到重试次数上限")
            return prompt

    def _send_prompt_count(self, prompt: str, system_prompt: None | str, count: PromptsCounter) -> str:
        result = self.send(prompt, system_prompt)
        count.add()
        return result

    def send_prompts(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
    ) -> list[str]:
        self.logger.info(f"base-url:{self.baseurl},model-id:{self.model_id}")
        self.logger.info(f"预计发送{len(prompts)}个请求，并发请求数:{self.max_concurrent}")
        system_prompts = [system_prompt] * len(prompts)
        counts = [PromptsCounter(len(prompts), self.logger)] * len(prompts)
        output_list = []
        with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            results_iterator = executor.map(self._send_prompt_count, prompts, system_prompts, counts)
            output_list = list(results_iterator)
        return output_list


if __name__ == '__main__':
    pass
