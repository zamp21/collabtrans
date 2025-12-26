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

            if repaired_result == original_chunk:
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
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, dict):
                    self.logger.warning(f"Received chunk is not a valid dictionary, skipped: {chunk}")
                    continue
                for key, val in chunk.items():
                    if key in indexed_translated:
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"Unknown key '{key}' found in result chunk, ignored.")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"Type or attribute error occurred while processing chunk, skipped. Chunk: {chunk}, Error: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"Unknown error occurred while processing chunk: {e.__repr__()}")

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

        translated_chunks = await super().send_prompts_async(prompts=prompts, pre_send_handler=self._pre_send_handler,
                                                             result_handler=self._result_handler,
                                                             error_result_handler=self._error_result_handler)

        indexed_translated = indexed_originals.copy()
        for chunk in translated_chunks:
            try:
                if not isinstance(chunk, dict):
                    self.logger.error(f"Received chunk is not a valid dictionary, skipped: {chunk}")
                    continue
                for key, val in chunk.items():
                    if key in indexed_translated:
                        # str(val) is no longer needed here, as _result_handler has already handled it
                        indexed_translated[key] = val
                    else:
                        self.logger.warning(f"Unknown key '{key}' found in result chunk, ignored.")
            except (AttributeError, TypeError) as e:
                self.logger.error(f"Type or attribute error occurred while processing chunk, skipped. Chunk: {chunk}, Error: {e.__repr__()}")
            except Exception as e:
                self.logger.error(f"Unknown error occurred while processing chunk: {e.__repr__()}")

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

    def update_glossary_dict(self, update_dict: dict | None):
        if self.glossary_dict is None:
            self.glossary_dict = {}
        if update_dict is not None:
            self.glossary_dict = update_dict | self.glossary_dict
