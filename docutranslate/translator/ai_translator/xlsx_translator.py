import asyncio
from dataclasses import dataclass, field
from io import BytesIO
from typing import Self, Literal, List, Optional

import openpyxl
from openpyxl.cell import Cell

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig
from docutranslate.translator.base import Translator


@dataclass
class XlsxTranslatorConfig(AiTranslatorConfig):
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"
    # 指定翻译区域列表。
    # 示例: ["Sheet1!A1:B10", "C:D", "E5"]
    # 如果不指定表名 (如 "C:D")，则应用于所有表。
    # 如果为 None 或空列表，则翻译整个文件中的所有文本。
    translate_regions: Optional[List[str]] = None


class XlsxTranslator(Translator):
    def __init__(self, config: XlsxTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        agent_config = SegmentsTranslateAgentConfig(custom_prompt=config.custom_prompt,
                                                    to_lang=config.to_lang,
                                                    baseurl=config.base_url,
                                                    key=config.api_key,
                                                    model_id=config.model_id,
                                                    system_prompt=None,
                                                    temperature=config.temperature,
                                                    thinking=config.thinking,
                                                    max_concurrent=config.concurrent,
                                                    timeout=config.timeout,
                                                    logger=self.logger)
        self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator
        # --- 新增功能 ---
        self.translate_regions = config.translate_regions

    def _pre_translate(self, document: Document):
        workbook = openpyxl.load_workbook(BytesIO(document.content))
        cells_to_translate = []

        # --- 步骤 1: 根据是否指定区域，收集需要翻译的文本单元格 ---

        # 如果未指定翻译区域，则沿用旧逻辑，翻译所有单元格
        if self.translate_regions is None:
            for sheet in workbook.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if isinstance(cell.value, str) and cell.data_type == "s":
                            cells_to_translate.append({
                                "sheet_name": sheet.title,
                                "coordinate": cell.coordinate,
                                "original_text": cell.value,
                            })
        # 如果指定了翻译区域，则只在这些区域内查找
        else:
            # 用于防止重叠区域导致重复翻译
            processed_coordinates = set()

            # 1. 解析区域，区分“全局区域”和“指定工作表区域”
            regions_by_sheet = {}
            all_sheet_regions = []
            for region in self.translate_regions:
                if '!' in region:
                    sheet_name, cell_range = region.split('!', 1)
                    if sheet_name not in regions_by_sheet:
                        regions_by_sheet[sheet_name] = []
                    regions_by_sheet[sheet_name].append(cell_range)
                else:
                    all_sheet_regions.append(region)

            # 2. 遍历工作表，应用区域规则
            for sheet in workbook.worksheets:
                # 获取当前工作表的“指定区域”和“全局区域”
                sheet_specific_ranges = regions_by_sheet.get(sheet.title, [])
                total_ranges_for_this_sheet = sheet_specific_ranges + all_sheet_regions

                if not total_ranges_for_this_sheet:
                    continue

                # 3. 遍历区域内的单元格
                for cell_range in total_ranges_for_this_sheet:
                    try:
                        # sheet[cell_range] 可以获取单个单元格或一个元组的元组
                        cells_in_range = sheet[cell_range]
                        if isinstance(cells_in_range, Cell):
                            # 将单个单元格包装成与多单元格范围一致的结构
                            cells_in_range = ((cells_in_range,),)

                        for row_of_cells in cells_in_range:
                            for cell in row_of_cells:
                                full_coordinate = (sheet.title, cell.coordinate)
                                # 如果该单元格已处理，则跳过
                                if full_coordinate in processed_coordinates:
                                    continue

                                # 关键判断：值是字符串(str) 且 数据类型是 's' (string)
                                if isinstance(cell.value, str) and cell.data_type == "s":
                                    cell_info = {
                                        "sheet_name": sheet.title,
                                        "coordinate": cell.coordinate,
                                        "original_text": cell.value,
                                    }
                                    cells_to_translate.append(cell_info)
                                    processed_coordinates.add(full_coordinate)
                    except Exception as e:
                        self.logger.warning(f"跳过无效的区域 '{cell_range}' 在工作表 '{sheet.title}'. 错误: {e}")

        # 提取所有原文文本，准备进行批量翻译
        original_texts = [cell["original_text"] for cell in cells_to_translate]
        return workbook, cells_to_translate, original_texts

    def _after_translate(self, workbook, cells_to_translate, translated_texts, original_texts):
        for i, cell_info in enumerate(cells_to_translate):
            sheet_name = cell_info["sheet_name"]
            coordinate = cell_info["coordinate"]
            translated_text = translated_texts[i]
            original_text = original_texts[i]

            # 定位到工作表和单元格
            sheet = workbook[sheet_name]
            if self.insert_mode == "replace":
                sheet[coordinate] = translated_text
            elif self.insert_mode == "append":
                sheet[coordinate] = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                sheet[coordinate] = translated_text + self.separator + original_text
            else:
                self.logger.error("不正确的XlsxTranslatorConfig参数")

        workbook_output_stream = BytesIO()
        # 保存修改后的工作簿到新文件
        try:
            workbook.save(workbook_output_stream)
        finally:
            workbook.close()
        return workbook_output_stream.getvalue()

    def translate(self, document: Document) -> Self:

        workbook, cells_to_translate, original_texts = self._pre_translate(document)
        if not cells_to_translate:
            print("\n在指定区域中没有找到需要翻译的纯文本内容。")
            workbook.close()
            return self
        # --- 步骤 2: 调用翻译函数 ---
        translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)

        document.content = self._after_translate(workbook, cells_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:

        workbook, cells_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)
        if not cells_to_translate:
            print("\n在指定区域中没有找到需要翻译的纯文本内容。")
            workbook.close()
            return self
        # --- 步骤 2: 调用翻译函数 ---
        translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)

        document.content = await asyncio.to_thread(self._after_translate, workbook, cells_to_translate,
                                                   translated_texts, original_texts)
        return self