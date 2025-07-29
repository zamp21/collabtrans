from typing import Literal

from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig

convert_engin_type = Literal["mineru", "docling"]
x2md_convert_config_type = ConverterDoclingConfig | ConverterMineruConfig
