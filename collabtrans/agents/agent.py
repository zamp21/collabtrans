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

from collabtrans.global_values import USE_PROXY
from collabtrans.logger import global_logger
from collabtrans.utils.utils import get_httpx_proxies

MAX_REQUESTS_PER_ERROR = 15

ThinkingMode = Literal["enable", "disable", "default"]


class AgentResultError(ValueError):
    """A special exception used to indicate that the result was returned normally by AI, but the returned result has issues. This error is not counted in the total error count"""

    def __init__(self, message):
        super().__init__(message)


class PartialAgentResultError(ValueError):
    """A special exception used to indicate that the result is incomplete but contains partially successful data to trigger retry. This error is not counted in the total error count"""

    def __init__(self, message, partial_result: dict):
        super().__init__(message)
        self.partial_result = partial_result


@dataclass(kw_only=True)
class AgentConfig:
    logger: logging.Logger = global_logger
    base_url: str
    api_key: str | None = None
    model_id: str
    temperature: float = 0.7
    concurrent: int = 30
    timeout: int = 1200  # Unit (seconds), this value is the read value in httpx.TimeOut, not the total timeout time
    thinking: ThinkingMode = "default"
    retry: int = 2


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
                self.logger.info(f"Too many error responses")
            return self.reach_limit()

    def reach_limit(self):
        return self.count > self.max_errors_count


# Only used for counting in multi-threading
class PromptsCounter:
    def __init__(self, total: int, logger: logging.Logger):
        self.lock = Lock()
        self.count = 0
        self.total = total
        self.logger = logger

    def add(self):
        with self.lock:
            self.count += 1
            self.logger.info(f"Multi-threading - Completed: {self.count}/{self.total}")


def extract_token_info(response_data: dict) -> tuple[int, int, int, int]:
    """
    Extract token information from API response

    Supports multiple response formats:
    1. Format 1: usage.input_tokens_details.cached_tokens and usage.output_tokens_details.reasoning_tokens
    2. Format 2: usage.prompt_tokens_details.cached_tokens
    3. Format 3: usage.prompt_cache_hit_tokens and usage.completion_tokens_details.reasoning_tokens

    Args:
        response_data: API response data

    Returns:
        tuple: (input_tokens, cached_tokens, output_tokens, reasoning_tokens)
    """
    if "usage" not in response_data:
        return 0, 0, 0, 0

    usage = response_data["usage"]
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Initialize token detailed statistics
    cached_tokens = 0
    reasoning_tokens = 0

    # Try to get cached_tokens from different formats
    # Format 1: input_tokens_details.cached_tokens
    if (
            "input_tokens_details" in usage
            and "cached_tokens" in usage["input_tokens_details"]
    ):
        cached_tokens = usage["input_tokens_details"]["cached_tokens"]
    # Format 2: prompt_tokens_details.cached_tokens
    elif (
            "prompt_tokens_details" in usage
            and "cached_tokens" in usage["prompt_tokens_details"]
    ):
        cached_tokens = usage["prompt_tokens_details"]["cached_tokens"]
    # Format 3: prompt_cache_hit_tokens (directly under usage)
    elif "prompt_cache_hit_tokens" in usage:
        cached_tokens = usage["prompt_cache_hit_tokens"]

    # Try to get reasoning_tokens from different formats
    # Format 1: output_tokens_details.reasoning_tokens
    if (
            "output_tokens_details" in usage
            and "reasoning_tokens" in usage["output_tokens_details"]
    ):
        reasoning_tokens = usage["output_tokens_details"]["reasoning_tokens"]
    # Format 2: completion_tokens_details.reasoning_tokens
    elif (
            "completion_tokens_details" in usage
            and "reasoning_tokens" in usage["completion_tokens_details"]
    ):
        reasoning_tokens = usage["completion_tokens_details"]["reasoning_tokens"]

    return input_tokens, cached_tokens, output_tokens, reasoning_tokens


class TokenCounter:
    def __init__(self, logger: logging.Logger):
        self.lock = Lock()
        self.input_tokens = 0
        self.cached_tokens = 0
        self.output_tokens = 0
        self.reasoning_tokens = 0
        self.total_tokens = 0
        self.logger = logger

    def add(
            self,
            input_tokens: int,
            cached_tokens: int,
            output_tokens: int,
            reasoning_tokens: int,
    ):
        with self.lock:
            self.input_tokens += input_tokens
            self.cached_tokens += cached_tokens
            self.output_tokens += output_tokens
            self.reasoning_tokens += reasoning_tokens
            self.total_tokens += input_tokens + output_tokens
            # self.logger.debug(
            #     f"Token usage statistics - Input: {self.input_tokens}(including cached: {self.cached_tokens}), "
            #     f"Output: {self.output_tokens}(including reasoning: {self.reasoning_tokens}), Total: {self.total_tokens}"
            # )

    def get_stats(self):
        with self.lock:
            return {
                "input_tokens": self.input_tokens,
                "cached_tokens": self.cached_tokens,
                "output_tokens": self.output_tokens,
                "reasoning_tokens": self.reasoning_tokens,
                "total_tokens": self.total_tokens,
            }

    def reset(self):
        with self.lock:
            self.input_tokens = 0
            self.cached_tokens = 0
            self.output_tokens = 0
            self.reasoning_tokens = 0
            self.total_tokens = 0


PreSendHandlerType = Callable[[str, str], tuple[str, str]]
ResultHandlerType = Callable[[str, str, logging.Logger], Any]
ErrorResultHandlerType = Callable[[str, logging.Logger], Any]


class Agent:
    _think_factory = {
        "open.bigmodel.cn": ("thinking", {"type": "enabled"}, {"type": "disabled"}),
        "dashscope.aliyuncs.com": (
            "extra_body",
            {"enable_thinking": True},
            {"enable_thinking": False},
        ),
        "ark.cn-beijing.volces.com": (
            "thinking",
            {"type": "enabled"},
            {"type": "disabled"},
        ),
        "generativelanguage.googleapis.com": (
            "extra_body",
            {
                "google": {
                    "thinking_config": {"thinking_budget": -1, "include_thoughts": True}
                }
            },
            {
                "google": {
                    "thinking_config": {"thinking_budget": 0, "include_thoughts": False}
                }
            },
        ),
        "api.siliconflow.cn": ("enable_thinking", True, False),
    }

    def __init__(self, config: AgentConfig):

        self.baseurl = config.base_url.strip()
        if self.baseurl.endswith("/"):
            self.baseurl = self.baseurl[:-1]
        self.domain = urlparse(self.baseurl).netloc
        self.key = config.api_key.strip() if config.api_key else "xx"
        self.model_id = config.model_id.strip()
        self.system_prompt = ""
        self.temperature = config.temperature
        self.max_concurrent = config.concurrent
        self.timeout = httpx.Timeout(connect=5, read=config.timeout, write=300, pool=10)
        self.thinking = config.thinking
        self.logger = config.logger
        self.total_error_counter = TotalErrorCounter(logger=self.logger)
        # New: for counting final unresolved errors
        self.unresolved_error_lock = Lock()
        self.unresolved_error_count = 0
        # New: for counting token usage
        self.token_counter = TokenCounter(logger=self.logger)

        self.retry = config.retry

    def _add_thinking_mode(self, data: dict):
        if self.domain not in self._think_factory:
            return
        field_thinking, val_enable, val_disable = self._think_factory[self.domain]
        if self.thinking == "enable":
            data[field_thinking] = val_enable
        elif self.thinking == "disable":
            data[field_thinking] = val_disable

    def _prepare_request_data(
            self, prompt: str, system_prompt: str, temperature=None, top_p=0.9
    ):
        if temperature is None:
            temperature = self.temperature
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }
        data = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
            "top_p": top_p,
        }
        if self.thinking != "default":
            self._add_thinking_mode(data)
        return headers, data

    async def send_async(
            self,
            client: httpx.AsyncClient,
            prompt: str,
            system_prompt: None | str = None,
            retry=True,
            retry_count=0,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None,
            best_partial_result: dict | None = None,
    ) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)
        
        # Print prompt logs for agent
        self.logger.debug("=" * 80)
        self.logger.debug("🤖 Prompt sent to Agent:")
        self.logger.debug(f"📋 System Prompt:\n{system_prompt}")
        self.logger.debug(f"💬 User Prompt:\n{prompt}")
        self.logger.debug("=" * 80)

        headers, data = self._prepare_request_data(prompt, system_prompt)
        should_retry = False
        is_hard_error = False  # New flag to distinguish whether it's a hard error
        current_partial_result = None
        input_tokens = 0
        output_tokens = 0

        try:
            response = await client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            # print(f"[Test] resp:\n{response.json()}")
            result = response.json()["choices"][0]["message"]["content"]
            
            # Print AI response logs
            self.logger.debug("=" * 80)
            self.logger.debug("🤖 Agent Response:")
            self.logger.debug(f"📄 Response Content:\n{result}")
            self.logger.debug("=" * 80)

            # Get token usage information
            response_data = response.json()
            input_tokens, cached_tokens, output_tokens, reasoning_tokens = (
                extract_token_info(response_data)
            )

            # Update token counter
            self.token_counter.add(
                input_tokens, cached_tokens, output_tokens, reasoning_tokens
            )

            if retry_count > 0:
                self.logger.info(
                    f"Retry successful (attempt {retry_count}/{self.retry})."
                )

            # print(f"result:=============================================================\n{result}\n================\n")
            return (
                result
                if result_handler is None
                else result_handler(result, prompt, self.logger)
            )

        except AgentResultError as e:
            self.logger.error(f"AI returned incorrect result: {e}")
            should_retry = True
        # Specifically catch partial translation errors (soft errors)
        except PartialAgentResultError as e:
            # print(f"[Test]\nprompt:\n{prompt}\nresp:\n{result}")
            self.logger.error(f"Received partial result, will retry: {e}")
            current_partial_result = e.partial_result
            should_retry = True
            # is_hard_error remains False

        # Catch hard errors
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"AI request HTTP status error (async): {e.response.status_code} - {e.response.text}"
            )
            should_retry = True
            is_hard_error = True
        except httpx.RequestError as e:
            self.logger.error(f"AI request connection error (async): {repr(e)}")
            should_retry = True
            is_hard_error = True
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"AI response format or value error (async), will retry: {repr(e)}")
            should_retry = True
            is_hard_error = True

        if current_partial_result:
            best_partial_result = current_partial_result

        if should_retry and retry and retry_count < self.retry:
            # Only increase total error count for hard errors
            if is_hard_error:
                if retry_count == 0:
                    if self.total_error_counter.add():
                        self.logger.error("Too many errors, reached limit, no more retries.")
                        return (
                            best_partial_result
                            if best_partial_result
                            else (
                                prompt
                                if error_result_handler is None
                                else error_result_handler(prompt, self.logger)
                            )
                        )
                elif self.total_error_counter.reach_limit():
                    self.logger.error("Too many errors, reached limit, no more retries for this request.")
                    return (
                        best_partial_result
                        if best_partial_result
                        else (
                            prompt
                            if error_result_handler is None
                            else error_result_handler(prompt, self.logger)
                        )
                    )

            self.logger.info(f"Retrying attempt {retry_count + 1}/{self.retry}...")
            await asyncio.sleep(0.5)
            return await self.send_async(
                client,
                prompt,
                system_prompt,
                retry=True,
                retry_count=retry_count + 1,
                pre_send_handler=pre_send_handler,
                result_handler=result_handler,
                error_result_handler=error_result_handler,
                best_partial_result=best_partial_result,
            )
        else:
            if should_retry:
                self.logger.error(f"All retries failed, reached retry limit.")
                # New: increase unresolved error count after all retries fail
                with self.unresolved_error_lock:
                    self.unresolved_error_count += 1

            if best_partial_result:
                self.logger.info("All retries failed, but partial translation result exists, will use it.")
                return best_partial_result

            return (
                prompt
                if error_result_handler is None
                else error_result_handler(prompt, self.logger)
            )

    async def send_prompts_async(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            max_concurrent: int | None = None,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None,
    ) -> list[Any]:
        max_concurrent = (
            self.max_concurrent if max_concurrent is None else max_concurrent
        )
        total = len(prompts)
        self.logger.info(
            f"base-url:{self.baseurl},model-id:{self.model_id},concurrent:{max_concurrent},temperature:{self.temperature}"
        )
        self.logger.info(f"Planned to send {total} requests, concurrent requests: {max_concurrent}")
        self.total_error_counter.max_errors_count = (
                len(prompts) // MAX_REQUESTS_PER_ERROR
        )

        # New: reset counter before each batch send
        self.unresolved_error_count = 0
        # Reset token counter
        self.token_counter.reset()

        count = 0
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        proxies = get_httpx_proxies() if USE_PROXY else None

        limits = httpx.Limits(
            max_connections=self.max_concurrent * 2,  # Reserve space for retries and concurrency
            max_keepalive_connections=self.max_concurrent,  # Keep alive connections
        )

        async with httpx.AsyncClient(
                trust_env=False, proxies=proxies, verify=False, limits=limits
        ) as client:
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
                    self.logger.info(f"Coroutine completed {count}/{total}")
                    return result

            for p_text in prompts:
                task = asyncio.create_task(send_with_semaphore(p_text))
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=False)

            # New: print total unresolved errors after all tasks complete
            self.logger.info(
                f"All requests processed. Total unresolved errors: {self.unresolved_error_count}"
            )

            # New: print token usage statistics
            token_stats = self.token_counter.get_stats()
            self.logger.info(
                f"Token usage statistics - Input: {token_stats['input_tokens'] / 1000:.2f}K(including cached: {token_stats['cached_tokens'] / 1000:.2f}K), "
                f"Output: {token_stats['output_tokens'] / 1000:.2f}K(including reasoning: {token_stats['reasoning_tokens'] / 1000:.2f}K), "
                f"Total: {token_stats['total_tokens'] / 1000:.2f}K"
            )

            return results

    def send(
            self,
            client: httpx.Client,
            prompt: str,
            system_prompt: None | str = None,
            retry=True,
            retry_count=0,
            pre_send_handler=None,
            result_handler=None,
            error_result_handler=None,
            best_partial_result: dict | None = None,
    ) -> Any:
        if system_prompt is None:
            system_prompt = self.system_prompt
        if pre_send_handler:
            system_prompt, prompt = pre_send_handler(system_prompt, prompt)

        headers, data = self._prepare_request_data(prompt, system_prompt)
        should_retry = False
        is_hard_error = False  # New flag to distinguish whether it's a hard error
        current_partial_result = None
        input_tokens = 0
        output_tokens = 0

        try:
            response = client.post(
                f"{self.baseurl}/chat/completions",
                json=data,
                headers=headers,
                timeout=self.timeout,
            )
            response.raise_for_status()

            result = response.json()["choices"][0]["message"]["content"]
            
            # Print AI response logs
            self.logger.debug("=" * 80)
            self.logger.debug("🤖 Agent Response:")
            self.logger.debug(f"📄 Response Content:\n{result}")
            self.logger.debug("=" * 80)

            # Get token usage information
            response_data = response.json()
            input_tokens, cached_tokens, output_tokens, reasoning_tokens = (
                extract_token_info(response_data)
            )

            # Update token counter
            self.token_counter.add(
                input_tokens, cached_tokens, output_tokens, reasoning_tokens
            )

            if retry_count > 0:
                self.logger.info(
                    f"Retry successful (attempt {retry_count}/{self.retry})."
                )

            return (
                result
                if result_handler is None
                else result_handler(result, prompt, self.logger)
            )
        except AgentResultError as e:
            self.logger.error(f"AI returned incorrect result: {e}")
            should_retry = True
        # Specifically catch partial translation errors (soft errors)
        except PartialAgentResultError as e:
            self.logger.error(f"Received partial translation result, will retry: {e}")
            current_partial_result = e.partial_result
            should_retry = True
            # is_hard_error remains False

        # Catch hard errors
        except httpx.HTTPStatusError as e:
            self.logger.error(
                f"AI request HTTP status error (sync): {e.response.status_code} - {e.response.text}"
            )
            should_retry = True
            is_hard_error = True
        except httpx.RequestError as e:
            self.logger.error(f"AI request connection error (sync): {repr(e)}\nprompt:{prompt}")
            should_retry = True
            is_hard_error = True
        except (KeyError, IndexError, ValueError) as e:
            self.logger.error(f"AI response format or value error (sync), will retry: {repr(e)}")
            should_retry = True
            is_hard_error = True

        if current_partial_result:
            best_partial_result = current_partial_result

        if should_retry and retry and retry_count < self.retry:
            # Only increase total error count for hard errors
            if is_hard_error:
                if retry_count == 0:
                    if self.total_error_counter.add():
                        self.logger.error("Too many errors, reached limit, no more retries.")
                        return (
                            best_partial_result
                            if best_partial_result
                            else (
                                prompt
                                if error_result_handler is None
                                else error_result_handler(prompt, self.logger)
                            )
                        )
                elif self.total_error_counter.reach_limit():
                    self.logger.error("Too many errors, reached limit, no more retries for this request.")
                    return (
                        best_partial_result
                        if best_partial_result
                        else (
                            prompt
                            if error_result_handler is None
                            else error_result_handler(prompt, self.logger)
                        )
                    )

            self.logger.info(f"Retrying attempt {retry_count + 1}/{self.retry}...")
            time.sleep(0.5)
            return self.send(
                client,
                prompt,
                system_prompt,
                retry=True,
                retry_count=retry_count + 1,
                pre_send_handler=pre_send_handler,
                result_handler=result_handler,
                error_result_handler=error_result_handler,
                best_partial_result=best_partial_result,
            )
        else:
            if should_retry:
                self.logger.error(f"All retries failed, reached retry limit.")
                # New: increase unresolved error count after all retries fail
                with self.unresolved_error_lock:
                    self.unresolved_error_count += 1

            if best_partial_result:
                self.logger.info("All retries failed, but partial translation result exists, will use it.")
                return best_partial_result

            return (
                prompt
                if error_result_handler is None
                else error_result_handler(prompt, self.logger)
            )

    def _send_prompt_count(
            self,
            client: httpx.Client,
            prompt: str,
            system_prompt: None | str,
            count: PromptsCounter,
            pre_send_handler,
            result_handler,
            error_result_handler,
    ) -> Any:
        result = self.send(
            client,
            prompt,
            system_prompt,
            pre_send_handler=pre_send_handler,
            result_handler=result_handler,
            error_result_handler=error_result_handler,
        )
        count.add()
        return result

    def send_prompts(
            self,
            prompts: list[str],
            system_prompt: str | None = None,
            pre_send_handler: PreSendHandlerType = None,
            result_handler: ResultHandlerType = None,
            error_result_handler: ErrorResultHandlerType = None,
    ) -> list[Any]:
        self.logger.info(
            f"base-url:{self.baseurl},model-id:{self.model_id},concurrent:{self.max_concurrent},temperature:{self.temperature}"
        )
        self.logger.info(
            f"Planned to send {len(prompts)} requests, concurrent requests: {self.max_concurrent}"
        )
        self.total_error_counter.max_errors_count = (
                len(prompts) // MAX_REQUESTS_PER_ERROR
        )

        # New: reset counter before each batch send
        self.unresolved_error_count = 0
        # Reset token counter
        self.token_counter.reset()

        counter = PromptsCounter(len(prompts), self.logger)

        system_prompts = itertools.repeat(system_prompt, len(prompts))
        counters = itertools.repeat(counter, len(prompts))
        pre_send_handlers = itertools.repeat(pre_send_handler, len(prompts))
        result_handlers = itertools.repeat(result_handler, len(prompts))
        error_result_handlers = itertools.repeat(error_result_handler, len(prompts))
        limits = httpx.Limits(
            max_connections=self.max_concurrent * 2,  # Allow connection reuse
            max_keepalive_connections=self.max_concurrent,  # Keep active connections
        )
        proxies = get_httpx_proxies() if USE_PROXY else None
        with httpx.Client(
                trust_env=False, proxies=proxies, verify=False, limits=limits
        ) as client:
            clients = itertools.repeat(client, len(prompts))
            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                results_iterator = executor.map(
                    self._send_prompt_count,
                    clients,
                    prompts,
                    system_prompts,
                    counters,
                    pre_send_handlers,
                    result_handlers,
                    error_result_handlers,
                )
                output_list = list(results_iterator)

        # New: print total unresolved errors after all tasks complete
        self.logger.info(
            f"All requests processed. Total unresolved errors: {self.unresolved_error_count}"
        )

        # New: print token usage statistics
        token_stats = self.token_counter.get_stats()
        self.logger.info(
            f"Token usage statistics - Input: {token_stats['input_tokens'] / 1000:.2f}K(including cached: {token_stats['cached_tokens'] / 1000:.2f}K), "
            f"Output: {token_stats['output_tokens'] / 1000:.2f}K(including reasoning: {token_stats['reasoning_tokens'] / 1000:.2f}K), "
            f"Total: {token_stats['total_tokens'] / 1000:.2f}K"
        )

        return output_list


if __name__ == "__main__":
    pass
