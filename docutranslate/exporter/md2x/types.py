from typing import Literal, TYPE_CHECKING

from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.global_values.conditional_import import DOCLING_FLAG

if DOCLING_FLAG or TYPE_CHECKING:
    from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

convert_engin_type = Literal["mineru", "docling"]

if DOCLING_FLAG or TYPE_CHECKING:
    x2md_convert_config_type = ConverterDoclingConfig | ConverterMineruConfig
else:
    x2md_convert_config_type = ConverterMineruConfig
