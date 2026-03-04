# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0

import asyncio
import json
from dataclasses import dataclass
from json import JSONDecodeError
from logging import Logger

from json_repair import json_repair

from collabtrans.agents import AgentConfig, Agent
from collabtrans.agents.agent import PartialAgentResultError, AgentResultError
from collabtrans.glossary.glossary import Glossary
from collabtrans.utils.json_utils import segments2json_chunks, fix_json_string
from collabtrans.utils.memory_utils import log_memory


@dataclass
class SegmentsTranslateAgentConfig(AgentConfig):
    to_lang: str
    custom_prompt: str | None = None
    glossary_dict: dict[str, str] | None = None


class SegmentsTranslateAgent(Agent):
    def __init__(self, config: SegmentsTranslateAgentConfig):
        super().__init__(config)
        self.system_prompt = f"""
# Role
- You are a professional machine translation engine with expertise in natural, fluent translation.

# Task
- You will receive a sequence of segments to be translated, represented in JSON format. The keys are the segment IDs, and the values are the segments for translation.
- You need to translate these segments into {config.to_lang}.

# Requirements
- **Natural and Fluent Translation**: The translation must sound natural and fluent in the target language. Avoid literal word-for-word translations that sound awkward or unnatural.
- **Cultural Adaptation**: Adapt cultural references, idioms, and expressions to be appropriate for the target language and culture. Use equivalent expressions that native speakers would naturally use.
- **Professional Quality**: The translation must be professional, accurate, and maintain the original meaning while being easily readable.
- **No Explanations**: Do not output any explanations, annotations, or meta-commentary.
- **Format Preservation**: The format of the translated segments should be as close as possible to the source format.
- **Proper Nouns**: For personal names and proper nouns, use the most commonly accepted translations.
- **Technical Elements**: Keep special tags, codes, brand names, and technical jargon in their original form when appropriate.
- **Target Language Check**: If a segment is already in the target language({config.to_lang}), keep it as is.
- **Segment Integrity**: Do not merge multiple segment translations into one translation.
- **JSON Structure**: (very important) All keys that appear in the input JSON must exist in the output JSON.
# Output
- The translated sequence of segments, represented as JSON text (note: not a code block). The keys are the segment IDs, and the values are the translated segments.
- The response must be a JSON object with the following structure: 
{{
"<segment_id>": "<translation>"
}}
- (very important) The segment IDs in the output must exactly match those in the input. And all segment IDs in input must appear in the output.
# Example(Assuming the target language is English in the example, {config.to_lang} is the actual target language)
## Input
{{
"10": "Tom said: \"Hello\"",
"11": "Apple",
"12": true,
"13": "Error",
"14": null
}}
## Correct Output
{{
"21": "Tom says:\\\"hello\\\"",
"22": "apple",
"23": "error",
"24": "banana"
}}
"""
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

    def _result_handler(self, result: str, origin_prompt: str, logger: Logger, best_partial_result: dict = None):
        """
        Handle successful API response.
        - If keys match completely, return translation result.
        - If keys don't match, construct a partially successful result and throw PartialTranslationError exception to trigger retry.
        - Other errors (such as JSON parsing failure, model laziness) throw regular ValueError to trigger retry.
        - If best_partial_result is provided (from previous retry), merge it with new result.
        """
        if result == "":
            if origin_prompt.strip() != "":
                raise AgentResultError("Result is empty but original text is not empty")
            return {}
        try:
            result = fix_json_string(result)
            original_chunk = json.loads(origin_prompt)
            repaired_result = json_repair.loads(result)

            if not isinstance(repaired_result, dict):
                raise AgentResultError(f"Agent returned result is not in dict JSON format, result: {result}")

            # Check if result is identical to original - but allow certain cases
            if repaired_result == original_chunk:
                # Check if all values are likely to be technical codes/numbers that should remain unchanged
                # This includes: pure numbers, codes with slashes/dashes, or very short alphanumeric strings
                all_technical = True
                has_translatable_content = False
                
                for key, value in original_chunk.items():
                    val_str = str(value).strip()
                    if not val_str:
                        continue  # Empty strings are fine
                    
                    # Check if it's a pure number or very short code
                    if val_str.isdigit() or len(val_str) <= 3:
                        continue  # Pure numbers or very short codes are fine
                    
                    # Check if it's a technical code pattern (contains special chars like /, -, _, or tabs)
                    # Examples: "PULSE/AC02-DHF-035", "R1", "v1.0"
                    is_code_pattern = any(c in val_str for c in ['/', '-', '_', '\t']) and not ' ' in val_str
                    
                    # Check if it contains meaningful words that should be translated
                    # If it has spaces, it likely contains translatable text
                    # If it's longer than 10 chars without special code characters, it might be translatable
                    if ' ' in val_str:
                        has_translatable_content = True
                        all_technical = False
                        break
                    elif len(val_str) > 10 and not is_code_pattern:
                        # Long text without code patterns should be translated
                        has_translatable_content = True
                        all_technical = False
                        break
                
                if has_translatable_content:
                    # Contains translatable content but result is identical - likely translation failure
                    # However, if we have a best_partial_result that is also identical, it means we've retried multiple times
                    # In this case, accept the result (use original as translation) to allow file generation to continue
                    if best_partial_result and best_partial_result == original_chunk:
                        logger.warning(f"Translation result is identical to original text after multiple retries. Accepting original text as translation to allow file generation.")
                        return original_chunk
                    logger.warning(f"Translation result is identical to original text, but contains translatable content. Will retry.")
                    raise AgentResultError("Translation result is identical to original text, suspected translation failure, will retry.")
                elif all_technical:
                    # All values appear to be technical codes/numbers, keeping them unchanged is acceptable
                    logger.info(f"Translation result is identical to original text, but all values appear to be technical codes/numbers. Accepting result.")
                else:
                    # Mixed case - if we've retried multiple times, accept the result
                    if best_partial_result and best_partial_result == original_chunk:
                        logger.warning(f"Translation result is identical to original text after multiple retries. Accepting original text as translation to allow file generation.")
                        return original_chunk
                    # Mixed case - be conservative and retry
                    logger.warning(f"Translation result is identical to original text. Mixed content detected, will retry.")
                    raise AgentResultError("Translation result is identical to original text, suspected translation failure, will retry.")

            # If this is a retry with partial result, merge the new result with the existing partial result
            if best_partial_result:
                logger.info(f"Merging retry result with previous partial result. Previous keys: {set(best_partial_result.keys())}, New keys: {set(repaired_result.keys())}")
                # Merge: use new result for keys that exist in repaired_result, keep best_partial_result for others
                merged_result = best_partial_result.copy()
                for key, value in repaired_result.items():
                    merged_result[key] = str(value)
                repaired_result = merged_result
                logger.info(f"Merged result keys: {set(repaired_result.keys())}")

            original_keys = set(original_chunk.keys())
            result_keys = set(repaired_result.keys())

            # If keys don't match completely
            if original_keys != result_keys:
                # Still construct the most complete "partial result" first
                final_chunk = {}
                common_keys = original_keys.intersection(result_keys)
                missing_keys = original_keys - result_keys
                extra_keys = result_keys - original_keys

                logger.warning(f"Translation result keys don't match original text! Will retry.")
                if missing_keys: logger.warning(f"Missing keys: {missing_keys}")
                if extra_keys: logger.warning(f"Extra keys: {extra_keys}")

                for key in common_keys:
                    final_chunk[key] = str(repaired_result[key])
                for key in missing_keys:
                    final_chunk[key] = str(original_chunk[key])

                # Throw custom exception, passing partial result, missing keys, and original chunk for smart retry
                raise PartialAgentResultError(
                    "Key mismatch, triggering retry",
                    partial_result=final_chunk,
                    missing_keys=missing_keys,
                    original_chunk=original_chunk
                )

            # If keys match completely (ideal case), return normally
            for key, value in repaired_result.items():
                repaired_result[key] = str(value)

            return repaired_result

        except (RuntimeError, JSONDecodeError) as e:
            # For hard errors like JSON parsing, continue throwing regular ValueError
            raise AgentResultError(f"Result processing failed: {e.__repr__()}")

    def _error_result_handler(self, origin_prompt: str, logger: Logger):
        """
        Handle requests that still fail after all retries.
        As a fallback, return original content and convert all values to strings.
        """
        if origin_prompt == "":
            return {}
        try:
            original_chunk = json.loads(origin_prompt)
            # This logic is preserved as the final fallback solution
            for key, value in original_chunk.items():
                original_chunk[key] = f"{value}"
            return original_chunk
        except (RuntimeError, JSONDecodeError):
            logger.error(f"Original prompt is also not valid JSON format: {origin_prompt}")
            # If original prompt itself is also invalid, return a clear error object
            return {"error": f"{origin_prompt}"}

    def send_segments(self, segments: list[str], chunk_size: int) -> list[str]:
        indexed_originals, chunks, merged_indices_list = segments2json_chunks(segments, chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False, indent=0) for chunk in chunks]

        translated_chunks = super().send_prompts(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                 result_handler=self._result_handler,
                                                 error_result_handler=self._error_result_handler)

        indexed_translated = indexed_originals.copy()
        failed_segments = {}  # 记录失败的片段: {key: original_text}
        
        for i, chunk in enumerate(translated_chunks):
            try:
                if not isinstance(chunk, dict):
                    self.logger.error(f"Received chunk is not a valid dictionary, skipped: {chunk}")
                    # 记录整个 chunk 的所有片段为失败
                    original_chunk = chunks[i]
                    for key, val in original_chunk.items():
                        if key in indexed_originals:
                            failed_segments[key] = indexed_originals[key]
                    continue
                
                original_chunk = chunks[i]
                original_keys = set(original_chunk.keys())
                result_keys = set(chunk.keys())
                
                # 检查是否有缺失的 key
                missing_keys = original_keys - result_keys
                if missing_keys:
                    self.logger.warning(f"Chunk {i} missing keys: {missing_keys}, will retry these segments")
                    for key in missing_keys:
                        if key in indexed_originals:
                            failed_segments[key] = indexed_originals[key]
                
                # 优化：先检查整个 chunk 是否完全失败（所有值都与原文相同）
                # 如果是，直接标记整个 chunk 为失败，避免逐个 segment 检查
                all_identical = True
                has_translatable_content = False
                for key in original_keys:
                    if key not in chunk:
                        all_identical = False
                        break
                    original_val = indexed_originals.get(key, "")
                    result_val = chunk.get(key, "")
                    if result_val != original_val:
                        all_identical = False
                        break
                    # 检查是否有可翻译内容
                    if original_val.strip():
                        val_str = str(original_val).strip()
                        is_technical = (
                            val_str.isdigit() or 
                            len(val_str) <= 3 or 
                            (any(c in val_str for c in ['/', '-', '_', '\t']) and ' ' not in val_str)
                        )
                        if not is_technical:
                            has_translatable_content = True
                
                if all_identical and has_translatable_content:
                    # 整个 chunk 都失败了，直接标记所有 segment 为失败
                    self.logger.warning(f"Chunk {i} completely failed (all {len(original_keys)} segments identical to original), will retry entire chunk")
                    for key in original_keys:
                        if key in indexed_originals:
                            failed_segments[key] = indexed_originals[key]
                    # 不更新 indexed_translated，保持原文
                    continue
                
                # 部分成功或完全成功的情况，逐个处理 segment
                for key, val in chunk.items():
                    if key in indexed_translated:
                        original_val = indexed_originals.get(key, "")
                        # 如果翻译结果与原文完全相同，且原文不是空或纯技术代码，可能是翻译失败
                        if val == original_val and original_val.strip():
                            # 检查是否是纯技术代码（数字、短代码等）
                            val_str = str(val).strip()
                            is_technical = (
                                val_str.isdigit() or 
                                len(val_str) <= 3 or 
                                (any(c in val_str for c in ['/', '-', '_', '\t']) and ' ' not in val_str)
                            )
                            if not is_technical:
                                self.logger.warning(f"Segment {key} translation is identical to original, may be a failure. Will retry.")
                                failed_segments[key] = original_val
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"Unknown key '{key}' found in result chunk, ignored.")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"Type or attribute error occurred while processing chunk, skipped. Chunk: {chunk}, Error: {e.__repr__()}")
                # 记录整个 chunk 的所有片段为失败
                original_chunk = chunks[i]
                for key, val in original_chunk.items():
                    if key in indexed_originals:
                        failed_segments[key] = indexed_originals[key]
            except Exception as e:
                self.logger.error(f"Unknown error occurred while processing chunk: {e.__repr__()}")
                # 记录整个 chunk 的所有片段为失败
                original_chunk = chunks[i]
                for key, val in original_chunk.items():
                    if key in indexed_originals:
                        failed_segments[key] = indexed_originals[key]

        # 如果有失败的片段，进行第二次翻译
        if failed_segments:
            self.logger.info(f"Found {len(failed_segments)} failed segments, will retry translation")
            
            # 将失败的片段重新组装成 chunk
            failed_chunks, failed_merged_indices = self._create_chunks_from_segments(failed_segments, chunk_size)
            failed_prompts = [json.dumps(chunk, ensure_ascii=False, indent=0) for chunk in failed_chunks]
            
            # 第二次翻译
            self.logger.info(f"Retrying {len(failed_prompts)} chunks with {sum(len(c) for c in failed_chunks)} failed segments")
            retry_translated_chunks = super().send_prompts(
                prompts=failed_prompts, 
                pre_send_handler=self._pre_send_handler,
                result_handler=self._result_handler,
                error_result_handler=self._error_result_handler
            )
            
            # 合并第二次翻译结果
            retry_count = 0
            for chunk in retry_translated_chunks:
                try:
                    if not isinstance(chunk, dict):
                        self.logger.warning(f"Retry chunk is not a valid dictionary, skipped: {chunk}")
                        continue
                    for key, val in chunk.items():
                        if key in indexed_translated and key in failed_segments:
                            original_val = failed_segments[key]
                            # 检查重试结果是否真的与原文不同（成功翻译）
                            if val != original_val:
                                # 更新翻译结果
                                indexed_translated[key] = val
                                # 从失败列表中移除
                                failed_segments.pop(key, None)
                                retry_count += 1
                            else:
                                # 重试结果与原文相同，仍然是失败
                                # 检查是否是纯技术代码（如果是，可以接受）
                                val_str = str(val).strip()
                                is_technical = (
                                    val_str.isdigit() or 
                                    len(val_str) <= 3 or 
                                    (any(c in val_str for c in ['/', '-', '_', '\t']) and ' ' not in val_str)
                                )
                                if is_technical:
                                    # 技术代码，接受结果
                                    indexed_translated[key] = val
                                    failed_segments.pop(key, None)
                                    retry_count += 1
                                else:
                                    # 非技术代码但结果相同，重试失败
                                    self.logger.warning(f"Retry failed for segment {key}: result is still identical to original")
                except Exception as e:
                    self.logger.error(f"Error processing retry chunk: {e.__repr__()}")
            
            if retry_count > 0:
                self.logger.info(f"Successfully retranslated {retry_count} segments")
            if failed_segments:
                self.logger.warning(f"Still have {len(failed_segments)} segments that failed after retry")

        # Rebuild final list
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            result.extend(ls[last_end:start])
            merged_item = "".join(map(str, ls[start:end]))
            result.append(merged_item)
            last_end = end

        result.extend(ls[last_end:])
        return result

    async def send_segments_async(self, segments: list[str], chunk_size: int) -> list[str]:
        indexed_originals, chunks, merged_indices_list = await asyncio.to_thread(segments2json_chunks, segments,
                                                                                 chunk_size)
        prompts = [json.dumps(chunk, ensure_ascii=False, indent=0) for chunk in chunks]
        log_memory(self.logger, "segments: after building chunks", f"{len(chunks)} chunks, {len(segments)} segments")

        translated_chunks = await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)
        log_memory(self.logger, "segments: after all API chunks returned", f"{len(translated_chunks)} chunks")

        indexed_translated = indexed_originals.copy()
        failed_segments = {}  # 记录失败的片段: {key: original_text}
        
        for i, chunk in enumerate(translated_chunks):
            try:
                if not isinstance(chunk, dict):
                    self.logger.error(f"Received chunk is not a valid dictionary, skipped: {chunk}")
                    # 记录整个 chunk 的所有片段为失败
                    original_chunk = chunks[i]
                    for key, val in original_chunk.items():
                        if key in indexed_originals:
                            failed_segments[key] = indexed_originals[key]
                    continue
                
                original_chunk = chunks[i]
                original_keys = set(original_chunk.keys())
                result_keys = set(chunk.keys())
                
                # 检查是否有缺失的 key
                missing_keys = original_keys - result_keys
                if missing_keys:
                    self.logger.warning(f"Chunk {i} missing keys: {missing_keys}, will retry these segments")
                    for key in missing_keys:
                        if key in indexed_originals:
                            failed_segments[key] = indexed_originals[key]
                
                # 优化：先检查整个 chunk 是否完全失败（所有值都与原文相同）
                # 如果是，直接标记整个 chunk 为失败，避免逐个 segment 检查
                all_identical = True
                has_translatable_content = False
                for key in original_keys:
                    if key not in chunk:
                        all_identical = False
                        break
                    original_val = indexed_originals.get(key, "")
                    result_val = chunk.get(key, "")
                    if result_val != original_val:
                        all_identical = False
                        break
                    # 检查是否有可翻译内容
                    if original_val.strip():
                        val_str = str(original_val).strip()
                        is_technical = (
                            val_str.isdigit() or 
                            len(val_str) <= 3 or 
                            (any(c in val_str for c in ['/', '-', '_', '\t']) and ' ' not in val_str)
                        )
                        if not is_technical:
                            has_translatable_content = True
                
                if all_identical and has_translatable_content:
                    # 整个 chunk 都失败了，直接标记所有 segment 为失败
                    self.logger.warning(f"Chunk {i} completely failed (all {len(original_keys)} segments identical to original), will retry entire chunk")
                    for key in original_keys:
                        if key in indexed_originals:
                            failed_segments[key] = indexed_originals[key]
                    # 不更新 indexed_translated，保持原文
                    continue
                
                # 部分成功或完全成功的情况，逐个处理 segment
                for key, val in chunk.items():
                    if key in indexed_translated:
                        original_val = indexed_originals.get(key, "")
                        # 如果翻译结果与原文完全相同，且原文不是空或纯技术代码，可能是翻译失败
                        if val == original_val and original_val.strip():
                            # 检查是否是纯技术代码（数字、短代码等）
                            val_str = str(val).strip()
                            is_technical = (
                                val_str.isdigit() or 
                                len(val_str) <= 3 or 
                                (any(c in val_str for c in ['/', '-', '_', '\t']) and ' ' not in val_str)
                            )
                            if not is_technical:
                                self.logger.warning(f"Segment {key} translation is identical to original, may be a failure. Will retry.")
                                failed_segments[key] = original_val
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"Unknown key '{key}' found in result chunk, ignored.")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"Type or attribute error occurred while processing chunk, skipped. Chunk: {chunk}, Error: {e.__repr__()}")
                # 记录整个 chunk 的所有片段为失败
                original_chunk = chunks[i]
                for key, val in original_chunk.items():
                    if key in indexed_originals:
                        failed_segments[key] = indexed_originals[key]
            except Exception as e:
                self.logger.error(f"Unknown error occurred while processing chunk: {e.__repr__()}")
                # 记录整个 chunk 的所有片段为失败
                original_chunk = chunks[i]
                for key, val in original_chunk.items():
                    if key in indexed_originals:
                        failed_segments[key] = indexed_originals[key]
            log_memory(self.logger, f"segments: after merge chunk {i + 1}/{len(translated_chunks)}", f"chunk {i + 1}/{len(translated_chunks)}")

        # 如果有失败的片段，进行第二次翻译
        if failed_segments:
            self.logger.info(f"Found {len(failed_segments)} failed segments, will retry translation")
            
            # 将失败的片段重新组装成 chunk
            failed_chunks, failed_merged_indices = await asyncio.to_thread(
                self._create_chunks_from_segments, 
                failed_segments, 
                chunk_size
            )
            failed_prompts = [json.dumps(chunk, ensure_ascii=False, indent=0) for chunk in failed_chunks]
            
            # 第二次翻译
            self.logger.info(f"Retrying {len(failed_prompts)} chunks with {sum(len(c) for c in failed_chunks)} failed segments")
            retry_translated_chunks = await super().send_prompts_async(
                prompts=failed_prompts, 
                pre_send_handler=self._pre_send_handler,
                result_handler=self._result_handler,
                error_result_handler=self._error_result_handler
            )
            
            # 合并第二次翻译结果
            retry_count = 0
            for chunk in retry_translated_chunks:
                try:
                    if not isinstance(chunk, dict):
                        self.logger.warning(f"Retry chunk is not a valid dictionary, skipped: {chunk}")
                        continue
                    for key, val in chunk.items():
                        if key in indexed_translated and key in failed_segments:
                            original_val = failed_segments[key]
                            # 检查重试结果是否真的与原文不同（成功翻译）
                            if val != original_val:
                                # 更新翻译结果
                                indexed_translated[key] = val
                                # 从失败列表中移除
                                failed_segments.pop(key, None)
                                retry_count += 1
                            else:
                                # 重试结果与原文相同，仍然是失败
                                # 检查是否是纯技术代码（如果是，可以接受）
                                val_str = str(val).strip()
                                is_technical = (
                                    val_str.isdigit() or 
                                    len(val_str) <= 3 or 
                                    (any(c in val_str for c in ['/', '-', '_', '\t']) and ' ' not in val_str)
                                )
                                if is_technical:
                                    # 技术代码，接受结果
                                    indexed_translated[key] = val
                                    failed_segments.pop(key, None)
                                    retry_count += 1
                                else:
                                    # 非技术代码但结果相同，重试失败
                                    self.logger.warning(f"Retry failed for segment {key}: result is still identical to original")
                except Exception as e:
                    self.logger.error(f"Error processing retry chunk: {e.__repr__()}")
            
            if retry_count > 0:
                self.logger.info(f"Successfully retranslated {retry_count} segments")
            if failed_segments:
                self.logger.warning(f"Still have {len(failed_segments)} segments that failed after retry")

        # Rebuild final list
        result = []
        last_end = 0
        ls = list(indexed_translated.values())
        for start, end in merged_indices_list:
            result.extend(ls[last_end:start])
            merged_item = "".join(map(str, ls[start:end]))
            result.append(merged_item)
            last_end = end

        result.extend(ls[last_end:])
        return result
    
    def _create_chunks_from_segments(self, segments_dict: dict[str, str], chunk_size_max: int) -> tuple[list[dict[str, str]], list[tuple[int, int]]]:
        """
        从失败的片段字典创建 chunks，用于重试翻译
        返回: (chunks_list, merged_indices_list)
        """
        from collabtrans.utils.json_utils import get_json_size
        
        # 将字典转换为列表，保持 key 的顺序
        segments_list = [(key, val) for key, val in segments_dict.items()]
        chunks_list = []
        merged_indices_list = []
        
        if not segments_list:
            return [], []
        
        chunk = {}
        for key, val in segments_list:
            prospective_chunk = chunk.copy()
            prospective_chunk[key] = val
            
            if get_json_size(prospective_chunk) > chunk_size_max and chunk:
                chunks_list.append(chunk)
                chunk = {key: val}
            else:
                chunk = prospective_chunk
        
        if chunk:
            chunks_list.append(chunk)
        
        # merged_indices_list 对于重试场景可以返回空列表，因为不需要合并
        return chunks_list, []

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
