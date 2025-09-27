# SPDX-FileCopyrightText: 2025 QinHan
# SPDX-License-Identifier: MPL-2.0
import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Self, Literal, List, Dict, Any, Tuple

import docx
from docx.document import Document as DocumentObject
from docx.text.paragraph import Paragraph
from docx.text.run import Run

from collabtrans.agents.segments_agent import SegmentsTranslateAgentConfig, SegmentsTranslateAgent
from collabtrans.ir.document import Document
from collabtrans.translator.ai_translator.base import AiTranslatorConfig, AiTranslator


def is_image_run(run: Run) -> bool:
    """检查一个 run 是否包含图片。"""
    # w:drawing 是嵌入式图片的标志, w:pict 是 VML 图片的标志
    return '<w:drawing' in run.element.xml or '<w:pict' in run.element.xml


def get_font_for_language(target_language: str) -> str:
    """
    根据目标语言返回合适的字体
    
    Args:
        target_language: 目标语言名称
        
    Returns:
        推荐的字体名称
    """
    # 语言到字体的映射
    language_font_map = {
        # 中文
        "中文": "Microsoft YaHei",  # 微软雅黑
        "简体中文": "Microsoft YaHei",
        "繁体中文": "Microsoft JhengHei",  # 微软正黑体
        
        # 英文
        "英文": "Calibri",
        "English": "Calibri",
        
        # 日文
        "日文": "Yu Gothic",  # 游ゴシック
        "日本語": "Yu Gothic",
        "Japanese": "Yu Gothic",
        
        # 韩文
        "韩文": "Malgun Gothic",  # 맑은 고딕
        "한국어": "Malgun Gothic",
        "Korean": "Malgun Gothic",
        
        # 俄文
        "俄文": "Times New Roman",  # 俄文常用字体
        "Русский": "Times New Roman",
        "Russian": "Times New Roman",
        
        # 阿拉伯文
        "阿拉伯文": "Arial Unicode MS",  # 支持阿拉伯文字符
        "العَرَبِيَّة": "Arial Unicode MS",
        "Arabic": "Arial Unicode MS",
        
        # 其他欧洲语言
        "西班牙文": "Calibri",
        "Español": "Calibri",
        "Spanish": "Calibri",
        
        "法文": "Calibri",
        "Français": "Calibri",
        "French": "Calibri",
        
        "德文": "Calibri",
        "Deutsch": "Calibri",
        "German": "Calibri",
        
        "葡萄牙文": "Calibri",
        "Português": "Calibri",
        "Portuguese": "Calibri",
        
        # 越南文
        "越南文": "Arial Unicode MS",  # 支持越南文字符
        "tiếng Việt": "Arial Unicode MS",
        "Vietnamese": "Arial Unicode MS",
        
        # 希伯来文
        "希伯来文": "Arial Unicode MS",  # 支持希伯来文字符
        "Hebrew": "Arial Unicode MS",
        "עברית": "Arial Unicode MS",
        
        # 泰文
        "泰文": "Arial Unicode MS",  # 支持泰文字符
        "Thai": "Arial Unicode MS",
        "ไทย": "Arial Unicode MS",
        
        # 印地文
        "印地文": "Arial Unicode MS",  # 支持印地文字符
        "Hindi": "Arial Unicode MS",
        "हिन्दी": "Arial Unicode MS",
    }
    
    # 查找匹配的字体
    font = language_font_map.get(target_language)
    
    # 如果没有找到匹配的字体，返回默认字体
    if not font:
        # 根据语言特征进行智能选择
        if any(char in target_language for char in ['中文', 'Chinese', '简体', '繁体']):
            font = "Microsoft YaHei"
        elif any(char in target_language for char in ['日文', 'Japanese', '日本語']):
            font = "Yu Gothic"
        elif any(char in target_language for char in ['韩文', 'Korean', '한국어']):
            font = "Malgun Gothic"
        elif any(char in target_language for char in ['俄文', 'Russian', 'Русский']):
            font = "Times New Roman"
        elif any(char in target_language for char in ['阿拉伯文', 'Arabic', 'العَرَبِيَّة']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['越南文', 'Vietnamese', 'tiếng Việt']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['希伯来文', 'Hebrew', 'עברית']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['泰文', 'Thai', 'ไทย']):
            font = "Arial Unicode MS"
        elif any(char in target_language for char in ['印地文', 'Hindi', 'हिन्दी']):
            font = "Arial Unicode MS"
        else:
            # 默认使用Calibri（适用于大多数拉丁字母语言）
            font = "Calibri"
    
    return font


@dataclass
class DocxTranslatorConfig(AiTranslatorConfig):
    """
    DocxTranslator 的配置类。
    """
    insert_mode: Literal["replace", "append", "prepend"] = "replace"
    separator: str = "\n"


class DocxTranslator(AiTranslator):
    """
    用于翻译 .docx 文件的翻译器。
    此版本经过优化，可以处理图文混排的段落而不会丢失图片。
    """

    def __init__(self, config: DocxTranslatorConfig):
        super().__init__(config=config)
        self.chunk_size = config.chunk_size
        self.translate_agent = None
        if not self.skip_translate:
            agent_config = SegmentsTranslateAgentConfig(
                custom_prompt=config.custom_prompt,
                to_lang=config.to_lang,
                base_url=config.base_url,
                api_key=config.api_key,
                model_id=config.model_id,
                temperature=config.temperature,
                thinking=config.thinking,
                concurrent=config.concurrent,
                timeout=config.timeout,
                logger=self.logger,
                glossary_dict=config.glossary_dict,
                retry=config.retry
            )
            self.translate_agent = SegmentsTranslateAgent(agent_config)
        self.insert_mode = config.insert_mode
        self.separator = config.separator

    def _pre_translate(self, document: Document) -> Tuple[DocumentObject, List[Dict[str, Any]], List[str]]:
        """
        [已重构] 预处理 .docx 文件，在 Run 级别上提取文本，以避免破坏图片。
        :param document: 包含 .docx 文件内容的 Document 对象。
        :return: 一个元组，包含：
                 - docx.Document 对象
                 - 一个包含文本块信息的列表 (每个元素代表一组连续的文本 run)
                 - 一个包含所有待翻译原文的列表
        """
        doc = docx.Document(BytesIO(document.content))
        elements_to_translate = []
        original_texts = []

        def process_paragraph(para: Paragraph):
            nonlocal elements_to_translate, original_texts
            current_text_segment = ""
            current_runs = []

            for run in para.runs:
                if is_image_run(run):
                    # 遇到图片，将之前累积的文本作为一个翻译单元
                    if current_text_segment.strip():
                        elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                        original_texts.append(current_text_segment)
                    # 重置累加器
                    current_text_segment = ""
                    current_runs = []
                else:
                    # 累积文本 run
                    current_runs.append(run)
                    current_text_segment += run.text

            # 处理段落末尾的最后一个文本块
            if current_text_segment.strip():
                elements_to_translate.append({"type": "text_runs", "runs": current_runs})
                original_texts.append(current_text_segment)

        # 遍历所有段落
        for para in doc.paragraphs:
            process_paragraph(para)

        # 遍历所有表格
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        process_paragraph(para)

        return doc, elements_to_translate, original_texts

    def _after_translate(self, doc: DocumentObject, elements_to_translate: List[Dict[str, Any]],
                         translated_texts: List[str], original_texts: List[str]) -> bytes:
        """
        [已重构] 将翻译后的文本写回到对应的 text runs 中，保留图片和样式。
        """
        translation_map = dict(zip(original_texts, translated_texts))

        for i, element_info in enumerate(elements_to_translate):
            runs = element_info["runs"]
            original_text = original_texts[i]
            translated_text = translated_texts[i]

            # 根据插入模式确定最终文本
            if self.insert_mode == "replace":
                final_text = translated_text
            elif self.insert_mode == "append":
                final_text = original_text + self.separator + translated_text
            elif self.insert_mode == "prepend":
                final_text = translated_text + self.separator + original_text
            else:
                self.logger.error("不正确的DocxTranslatorConfig参数")
                final_text = translated_text

            if not runs:
                continue

            # --- 这是修改的核心部分 ---
            # 1. 将完整的翻译文本写入第一个 run
            first_run = runs[0]
            first_run.text = final_text
            
            # 2. 根据目标语言设置合适的字体，避免字体兼容性问题
            if first_run.font:
                # 根据目标语言选择字体
                target_font = get_font_for_language(self.config.to_lang)
                first_run.font.name = target_font
                
                # 如果首选字体不可用，尝试备选字体
                if not first_run.font.name:
                    # 根据语言类型选择备选字体
                    if any(char in self.config.to_lang for char in ['中文', 'Chinese', '简体', '繁体']):
                        # 中文备选字体
                        fallback_fonts = ['SimSun', 'SimHei', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['日文', 'Japanese', '日本語']):
                        # 日文备选字体
                        fallback_fonts = ['MS Gothic', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['韩文', 'Korean', '한국어']):
                        # 韩文备选字体
                        fallback_fonts = ['Gulim', 'Arial Unicode MS', 'Times New Roman']
                    elif any(char in self.config.to_lang for char in ['俄文', 'Russian', 'Русский']):
                        # 俄文备选字体
                        fallback_fonts = ['Times New Roman', 'Arial', 'Calibri']
                    elif any(char in self.config.to_lang for char in ['阿拉伯文', 'Arabic', 'العَرَبِيَّة']):
                        # 阿拉伯文备选字体
                        fallback_fonts = ['Arial Unicode MS', 'Times New Roman', 'Arial']
                    else:
                        # 其他语言的备选字体
                        fallback_fonts = ['Calibri', 'Times New Roman', 'Arial']
                    
                    # 尝试备选字体
                    for fallback_font in fallback_fonts:
                        first_run.font.name = fallback_font
                        if first_run.font.name:
                            break

            # 3. 清空该文本块中其余 run 的内容，但保留 run 本身及其格式
            #    这可以防止重复文本，同时保留文档结构
            for run in runs[1:]:
                run.text = ""
            # --- 修改结束 ---

        # 将修改后的文档保存到 BytesIO 流
        doc_output_stream = BytesIO()
        doc.save(doc_output_stream)
        return doc_output_stream.getvalue()

    def translate(self, document: Document) -> Self:
        """
        同步翻译 .docx 文件。
        """
        doc, elements_to_translate, original_texts = self._pre_translate(document)
        if not original_texts:
            print("\n文件中没有找到需要翻译的文本内容。")
            output_stream = BytesIO()
            doc.save(output_stream)
            document.content = output_stream.getvalue()
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = self.glossary_agent.send_segments(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # 调用翻译 agent
        if self.translate_agent:
            translated_texts = self.translate_agent.send_segments(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts

        # 将翻译结果写回文档
        document.content = self._after_translate(doc, elements_to_translate, translated_texts, original_texts)
        return self

    async def translate_async(self, document: Document) -> Self:
        """
        异步翻译 .docx 文件。
        """
        doc, elements_to_translate, original_texts = await asyncio.to_thread(self._pre_translate, document)
        if not original_texts:
            print("\n文件中没有找到需要翻译的文本内容。")
            # 在异步环境中正确保存和返回
            output_stream = BytesIO()
            doc.save(output_stream)
            document.content = output_stream.getvalue()
            return self

        if self.glossary_agent:
            self.glossary_dict_gen = await self.glossary_agent.send_segments_async(original_texts, self.chunk_size)
            if self.translate_agent:
                self.translate_agent.update_glossary_dict(self.glossary_dict_gen)

        # 异步调用翻译 agent
        if self.translate_agent:
            translated_texts = await self.translate_agent.send_segments_async(original_texts, self.chunk_size)
        else:
            translated_texts = original_texts
        # 将翻译结果写回文档
        document.content = await asyncio.to_thread(self._after_translate, doc, elements_to_translate, translated_texts,
                                                   original_texts)
        return self
