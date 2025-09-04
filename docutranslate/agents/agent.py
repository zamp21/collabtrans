# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import itertools
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Literal, Callable, Any
from urllib.parse import urlparse

import httpx

from docutranslate.global_values import USE_PROXY
from docutranslate.logger import global_logger
from docutranslate.utils.utils import get_httpx_proxies

MAX_RETRY_COUNT = 2
MAX_REQUESTS_PER_ERROR = 20

ThinkingMode = Literal["enable", "disable", "default"]


class PartialTranslationError(ValueError):
    """一个特殊的异常，用于表示结果不完整但包含了部分成功的数据，以便触发重试。"""

    def __init__(self, message, partial_result: dict):
        super().__init__(message)
        self.partial_result = partial_result


@dataclass(kw_only=True)
class AgentConfig:
    logger: logging.Logger
    baseurl: str
    key: str
    model_id: str
    temperature: float = 0.7
    max_concurrent: int = 30
    timeout: int = 2000
    thinking: ThinkingMode = "default"


class TotalErrorCounter:
    def __init__(self, logger: logging.Logger, max_errors_count=10):
        self.lock = Lock()
        self.count = 0
        self.logger = logger
        self.max_errors_count = max_errors_count

    def add(self):
        with self.lock:
            self.count += 1
            if self.count > self.max_errors_count:
                self.logger.info(f"错误响应过多")
            return self.reach_limit()

    def reach_limit(self):
        return self.count > self.max_errors_count


# 仅使用多线程时用以计数
class PromptsCounter:
    def __init__(self, total: int, logger: logging.Logger):
        self.lock = Lock()
        self.count = 0
        self.total = total
        self.logger = logger

    def add(self):
        with self.lock:
            self.count += 1
            self.logger.info(f"多线程-已完成：{self.count}/{self.total}")


PreSendHandlerType = Callable[[str, str], tuple[str, str]]
ResultHandlerType = Callable[[str, str, logging.Logger], Any]
ErrorResultHandlerType = Callable[[str, logging.Logger], Any]


class Agent:
    _think_factory = {
        "open.bigmodel.cn": ("thinking", {"type": "enabled"}, {"type": "disabled"}),
        "dashscope.aliyuncs.com": ("enable_thinking ", True, False),
        "ark.cn-beijing.volces.com": ("thinking", {"type": "enabled"}, {"type": "disabled"}),
        "generativelanguage.googleapis.com": ("extra_body",
                                              {"google": {
                                                  "thinking_config": {
                                                      "thinking_budget": -1,
                                                      "include_thoughts": True
                                                  }
                                              }
                                              }, {"google": {
                "thinking_config": {
                    "thinking_budget": 0,
                    "include_thoughts": False
                }
            }}),
        "api.siliconflow.cn": ("enable_thinking", True, False)
    }

    def __init__(self, config: AgentConfig):

        self.baseurl = config.baseurl.strip()
        if self.baseurl.endswith("/"):
            self.baseurl = self.baseurl[:-1]
        self.domain = urlparse(self.baseurl).netloc
        self.key = config.key.strip() or "xx"
        self.model_id = config.model_id.strip()
        self.system_prompt = ""
        self.temperature = config.temperature
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
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "top_p": top_p,
        }
        if self.thinking != "default":
            self._add_thinking_mode(data)
        return headers, data

    async def send_async(self, client: httpx.AsyncClient, prompt: str, system_prompt: None | str = None, retry=True,
                         retry_count=0,
                         pre_send_handler: PreSendHandlerType = None,
                         result_handler: ResultHandlerType = None,
                         error_result_handler: ErrorResultHandlerType = None,
                         best_partial_result: dict | None = None) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)

        headers, data = self._prepare_request_data(prompt, system_prompt)
        should_retry = False
        current_partial_result = None

        try:
            response = await client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]

            if retry_count > 0:
                self.logger.info(f"重试成功 (第 {retry_count + 1}/{MAX_RETRY_COUNT + 1} 次尝试)。")

            # print(f"result:=============================================================\n{result}\n================\n")
            return result if result_handler is None else result_handler(result, prompt, self.logger)

        # 专门捕获部分翻译错误
        except PartialTranslationError as e:
            self.logger.error(f"收到部分翻译结果，将尝试重试: {e}")
            current_partial_result = e.partial_result  # 保存这次的部分结果
            should_retry = True

        except httpx.HTTPStatusError as e:
            self.logger.error(f"AI请求HTTP状态错误 (async): {e.response.status_code} - {e.response.text}")
            print(f"prompt:\n{prompt}")
            should_retry = True
        except httpx.RequestError as e:
            self.logger.error(f"AI请求连接错误 (async): {repr(e)}")
            should_retry = True
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"AI响应格式或值错误 (async), 将尝试重试: {repr(e)}")
            should_retry = True

        # 如果当前捕获到了部分结果，就更新“最佳”结果
        if current_partial_result:
            best_partial_result = current_partial_result

        if should_retry and retry and retry_count < MAX_RETRY_COUNT:
            if retry_count == 0:
                if self.total_error_counter.add():
                    self.logger.error("错误次数过多，已达到上限，不再重试。")
                    # 如果有部分结果，优先返回部分结果
                    return best_partial_result if best_partial_result else (
                        prompt if error_result_handler is None else error_result_handler(prompt, self.logger))
            elif self.total_error_counter.reach_limit():
                self.logger.error("错误次数过多，已达到上限，不再为该请求重试。")
                return best_partial_result if best_partial_result else (
                    prompt if error_result_handler is None else error_result_handler(prompt, self.logger))

            self.logger.info(f"正在重试第 {retry_count + 1}/{MAX_RETRY_COUNT} 次...")
            await asyncio.sleep(0.5)
            # 将“最佳”结果传递给下一次递归调用
            return await self.send_async(client, prompt, system_prompt, retry=True, retry_count=retry_count + 1,
                                         pre_send_handler=pre_send_handler,
                                         result_handler=result_handler,
                                         error_result_handler=error_result_handler,
                                         best_partial_result=best_partial_result)
        else:
            if should_retry:
                self.logger.error(f"所有重试均失败，已达到重试次数上限。")

            # 在最终失败时，检查是否有可用的部分结果
            if best_partial_result:
                self.logger.info("所有重试失败，但存在部分翻译结果，将使用该结果。")
                return best_partial_result

            return prompt if error_result_handler is None else error_result_handler(prompt, self.logger)

    async def send_prompts_async(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            max_concurrent: int | None = None,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None
    ) -> list[Any]:
        max_concurrent = self.max_concurrent if max_concurrent is None else max_concurrent
        total = len(prompts)
        self.logger.info(
            f"base-url:{self.baseurl},model-id:{self.model_id},concurrent:{max_concurrent},temperature:{self.temperature}")
        self.logger.info(f"预计发送{total}个请求，并发请求数:{max_concurrent}")
        self.total_error_counter.max_errors_count = len(prompts) // MAX_REQUESTS_PER_ERROR
        count = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        proxies = get_httpx_proxies() if USE_PROXY else None

        async with httpx.AsyncClient(trust_env=False, proxies=proxies, verify=False) as client:
            async def send_with_semaphore(p_text: str):
                async with semaphore:
                    result = await self.send_async(
                        client=client,
                        prompt=p_text,
                        system_prompt=system_prompt,
                        pre_send_handler=pre_send_handler,
                        result_handler=result_handler,
                        error_result_handler=error_result_handler,
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

    def send(self, client: httpx.Client, prompt: str, system_prompt: None | str = None, retry=True, retry_count=0,
             pre_send_handler=None, result_handler=None, error_result_handler=None,
             best_partial_result: dict | None = None) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)

        headers, data = self._prepare_request_data(prompt, system_prompt)
        should_retry = False
        current_partial_result = None

        try:
            response = client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            result = response.json()["choices"][0]["message"]["content"]

            if retry_count > 0:
                self.logger.info(f"重试成功 (第 {retry_count + 1}/{MAX_RETRY_COUNT + 1} 次尝试)。")

            return result if result_handler is None else result_handler(result, prompt, self.logger)

        # --- MODIFICATION START ---
        except PartialTranslationError as e:
            self.logger.error(f"收到部分翻译结果，将尝试重试: {e}")
            current_partial_result = e.partial_result
            should_retry = True
        # --- MODIFICATION END ---

        except httpx.HTTPStatusError as e:
            self.logger.error(f"AI请求HTTP状态错误 (sync): {e.response.status_code} - {e.response.text}")
            print(f"prompt:\n{prompt}")
            should_retry = True
        except httpx.RequestError as e:
            self.logger.error(f"AI请求连接错误 (sync): {repr(e)}\nprompt:{prompt}")
            should_retry = True
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"AI响应格式或值错误 (sync), 将尝试重试: {repr(e)}")
            should_retry = True

        # --- MODIFICATION START ---
        if current_partial_result:
            best_partial_result = current_partial_result
        # --- MODIFICATION END ---

        if should_retry and retry and retry_count < MAX_RETRY_COUNT:
            if retry_count == 0:
                if self.total_error_counter.add():
                    self.logger.error("错误次数过多，已达到上限，不再重试。")
                    return best_partial_result if best_partial_result else (
                        prompt if error_result_handler is None else error_result_handler(prompt, self.logger))
            elif self.total_error_counter.reach_limit():
                self.logger.error("错误次数过多，已达到上限，不再为该请求重试。")
                return best_partial_result if best_partial_result else (
                    prompt if error_result_handler is None else error_result_handler(prompt, self.logger))

            self.logger.info(f"正在重试第 {retry_count + 1}/{MAX_RETRY_COUNT} 次...")
            time.sleep(0.5)
            return self.send(client, prompt, system_prompt, retry=True, retry_count=retry_count + 1,
                             pre_send_handler=pre_send_handler,
                             result_handler=result_handler,
                             error_result_handler=error_result_handler,
                             best_partial_result=best_partial_result)
        else:
            if should_retry:
                self.logger.error(f"所有重试均失败，已达到重试次数上限。")

            # --- MODIFICATION START ---
            if best_partial_result:
                self.logger.info("所有重试失败，但存在部分翻译结果，将使用该结果。")
                return best_partial_result
            # --- MODIFICATION END ---

            return prompt if error_result_handler is None else error_result_handler(prompt, self.logger)

    def _send_prompt_count(self, client: httpx.Client, prompt: str, system_prompt: None | str, count: PromptsCounter,
                           pre_send_handler,
                           result_handler,
                           error_result_handler) -> Any:
        result = self.send(client, prompt, system_prompt, pre_send_handler=pre_send_handler,
                           result_handler=result_handler,
                           error_result_handler=error_result_handler)
        count.add()
        return result

    def send_prompts(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None
    ) -> list[Any]:
        self.logger.info(
            f"base-url:{self.baseurl},model-id:{self.model_id},concurrent:{self.max_concurrent},temperature:{self.temperature}")
        self.logger.info(f"预计发送{len(prompts)}个请求，并发请求数:{self.max_concurrent}")
        self.total_error_counter.max_errors_count = len(prompts) // MAX_REQUESTS_PER_ERROR
        counter = PromptsCounter(len(prompts), self.logger)

        system_prompts = itertools.repeat(system_prompt, len(prompts))
        counters = itertools.repeat(counter, len(prompts))
        pre_send_handlers = itertools.repeat(pre_send_handler, len(prompts))
        result_handlers = itertools.repeat(result_handler, len(prompts))
        error_result_handlers = itertools.repeat(error_result_handler, len(prompts))

        proxies = get_httpx_proxies() if USE_PROXY else None
        with httpx.Client(trust_env=False, proxies=proxies, verify=False) as client:
            clients = itertools.repeat(client, len(prompts))
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                results_iterator = executor.map(self._send_prompt_count, clients, prompts, system_prompts, counters,
                                                pre_send_handlers,
                                                result_handlers,
                                                error_result_handlers)
                output_list = list(results_iterator)
        return output_list


if __name__ == '__main__':
    pass
