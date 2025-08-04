from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal

import openpyxl

from docutranslate.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from docutranslate.ir.document import Document
from docutranslate.translator.ai_translator.base import AiTranslatorConfig
from docutranslate.translator.base import Translator


@dataclass
class XlsxTranslatorConfig(AiTranslatorConfig):
    position: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


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
        self.position = config.position
        self.separator = config.separator

    def _pre_translate(self, document: Document):
        workbook = openpyxl.load_workbook(BytesIO(document.content))

        # --- 步骤 1: 收集所有需要翻译的文本单元格 ---
        cells_to_translate = []

        for sheet_name in workbook.sheetnames:
            sheet = workbook[sheet_name]
            for row in sheet.iter_rows():
                for cell in row:
                    # 关键判断：值是字符串(str) 且 数据类型是 's' (string)，以排除公式('f')
                    if isinstance(cell.value, str) and cell.data_type == "s":
                        cell_info = {
                            "sheet_name": sheet_name,
                            "coordinate": cell.coordinate,
                            "original_text": cell.value,
                        }
                        cells_to_translate.append(cell_info)
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
            if self.position == "replace":
                sheet[coordinate] = translated_text
            elif self.position == "append":
                sheet[coordinate] = original_text + self.separator + translated_text
            elif self.position == "prepend":
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
            print("\n文件中没有找到需要翻译的纯文本内容。")
            workbook.close()
            return
        # --- 步骤 2: 调用翻译函数 ---
        translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)

        document.content = self._after_translate(workbook, cells_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:

        workbook, cells_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)
        if not cells_to_translate:
            print("\n文件中没有找到需要翻译的纯文本内容。")
            workbook.close()
            return
        # --- 步骤 2: 调用翻译函数 ---
        translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)

        document.content = await asyncio.to_thread(self._after_translate, workbook, cells_to_translate,
                                                   translated_texts, original_texts)
        return self


if __name__ == '__main__':
    from pathlib import Path
    import asyncio

    config = XlsxTranslatorConfig(
        base_url=r"https://open.bigmodel.cn/api/paas/v4/",
        api_key=r"969ba51b61914cc2b710d1393dca1a3c.hSuATex5IoNVZNGu",
        model_id=r"glm-4-flash",
        to_lang="英文",
        position="append"
    )
    translator = XlsxTranslator(config)
    document = Document.from_path(r"C:\Users\jxgm\Desktop\translate\docutranslate\tests\files\工业互联分组表.xlsx")


    async def run():
        await translator.translate_async(document)
        path = Path(r"C:\Users\jxgm\Desktop\translate\docutranslate\tests\output\output.xlsx")
        path.write_bytes(document.content)
        print(f"已保存到{path.resolve()}")


    asyncio.run(run())
