<p align="center">
  <img src="./DocuTranslate.png" alt="Project Logo" style="width: 150px">
</p>

# DocuTranslate

[![GitHub stars](https://img.shields.io/github/stars/xunbu/docutranslate?style=flats&logo=github&color=blue)](https://github.com/xunbu/docutranslate)
[![github下载数](https://img.shields.io/github/downloads/xunbu/docutranslate/total?logo=github)](https://github.com/xunbu/docutranslate/releases)
[![PyPI version](https://img.shields.io/pypi/v/docutranslate)](https://pypi.org/project/docutranslate/)
[![python版本](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![开源协议](https://img.shields.io/github/license/xunbu/docutranslate)](./LICENSE)

[**简体中文**](/README_ZH.md) / [**English**](/README.md) / [**日本語**](/README_JP.md)

**DocuTranslate** is a file translation tool that combines advanced document parsing engines (such
as [docling](https://github.com/docling-project/docling) and [minerU](https://mineru.net/)) with large language models (
LLMs) to accurately translate documents in various formats.

The new version adopts a **Workflow-centric** architecture, providing highly configurable and scalable solutions for
various types of translation tasks.

- ✅ **Support for Diverse Formats**: Capable of translating various file formats such as `pdf`, `docx`, `xlsx`, `md`,
  `txt`, `json`, `epub`, `srt`, etc.
- ✅ **Table, Formula, and Code Recognition**: Utilizes `docling` and `minerU` to recognize and translate tables,
  formulas, and code frequently found in academic papers.
- ✅ **JSON Translation**: Allows specifying translatable values within JSON using jsonpath-ng syntax.
- ✅ **High-Fidelity Word/Excel Translation**: Preserves the formatting of `docx` and `xlsx` files (note: `doc` and `xls`
  are not supported).
- ✅ **Multiple AI Platform Support**: Covers major AI platforms and enables high-parallel AI translation with custom
  prompts.
- ✅ **Asynchronous Support**: Designed for high-performance scenarios, offering full asynchronous support and multi-task
  parallel processing APIs.
- ✅ **Interactive Web Interface**: Equipped with a ready-to-use Web UI and RESTful API.

> When translating `pdf` files, they are converted to markdown, **resulting in loss of the original layout**. Please be
> cautious if layout preservation is a priority.

> QQ Discussion Group: 1047781902

**UI Interface**:
![翻译效果](/images/UI界面.png)

**Paper Translation**:
![翻译效果](/images/论文翻译.png)

**Novel Translation**:
![翻译效果](/images/小说翻译.png)

## Bundled Version

For users who want to get started quickly, we provide a bundled version
on [GitHub Releases](https://github.com/xunbu/docutranslate/releases). Simply download, extract, and input the API key
of your preferred AI platform to start using it.

- **DocuTranslate**: Standard version, uses the online `minerU` engine.
- **DocuTranslate_full**: Full version, includes the local `docling` parsing engine, ideal for offline environments or
  scenarios prioritizing data privacy.

## Installation

### Using pip

```bash
# Basic installation
pip install docutranslate

# When using the docling local analysis engine
pip install docutranslate[docling]
```

### Using uv

```bash
# Environment initialization
uv init

# Basic installation
uv add docutranslate

# Extended installation with docling
uv add docutranslate[docling]
```

### Using git

```bash
# Environment initialization
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync
```

## Core Concept: Workflow

The heart of the new version of DocuTranslate is the **Workflow**. Each workflow is a complete end-to-end translation
pipeline designed for a specific file type. Instead of interacting with large classes, you select and configure the
appropriate workflow based on the file type.

**The basic usage steps are as follows:**

1. **Select a Workflow**: Choose a workflow such as `MarkdownBasedWorkflow` or `TXTWorkflow` based on the input file
   type (e.g., PDF/Word or TXT).
2. **Build the Configuration**: Create a configuration object (e.g., `MarkdownBasedWorkflowConfig`) corresponding to the
   selected workflow. This configuration object includes all necessary sub-configurations, such as:
    * **Converter Config**: Defines how to convert the original file (e.g., PDF) into Markdown.
    * **Translator Config**: Defines the LLM to use, API keys, target language, etc.
    * **Exporter Config**: Defines specific options for the output format (e.g., HTML).
3. **Instantiate the Workflow**: Use the configuration object to create an instance of the workflow.
4. **Execute the Translation**: Call the workflow's `.read_*()` and `.translate()` / `.translate_async()` methods.
5. **Export/Save the Results**: Call the `.export_to_*()` or `.save_as_*()` methods to retrieve or save the translated
   results.

## Available Workflows

| Workflow                    | Applicable Scenarios                                                                                                  | Input Formats                                | Output Formats         | Core Configuration Class      |
|:----------------------------|:----------------------------------------------------------------------------------------------------------------------|:---------------------------------------------|:-----------------------|:------------------------------|
| **`MarkdownBasedWorkflow`** | Processes rich-text documents like PDF, Word, and images. Follows the flow: "File → Markdown → Translation → Export". | `.pdf`, `.docx`, `.md`, `.png`, `.jpg`, etc. | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | Processes plain text documents. Follows the flow: "txt → Translation → Export".                                       | `.txt` and other plain text formats          | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | Processes JSON files. Follows the flow: "json → Translation → Export".                                                | `.json`                                      | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | Processes DOCX files. Follows the flow: "docx → Translation → Export".                                                | `.docx`                                      | `.docx`, `.html`       | `docxWorkflowConfig`          |
| **`XlsxWorkflow`**          | Processes XLSX files. Follows the flow: "xlsx → Translation → Export".                                                | `.xlsx`                                      | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | Processes SRT files. Follows the flow: "srt → Translation → Export".                                                  | `.srt`                                       | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**          | Processes EPUB files. Follows the flow: "epub → Translation → Export".                                                | `.epub`                                      | `.epub`, `.html`       | `EpubWorkflowConfig`          |
| **`HtmlWorkflow`**          | Processes HTML files. Follows the flow: "html → Translation → Export".                                                | `.html`, `.htm`                              | `.html`                | `HtmlWorkflowConfig`          |

> The interactive interface supports exporting in PDF format.

## Launching Web UI and API Services

For convenience, DocuTranslate provides a feature-rich web interface and RESTful API.

**Starting the Service:**

```bash
# Start the service (default port: 8010)
docutranslate -i

# Start with a specified port
docutranslate -i -p 8011

# Alternatively, specify the port via environment variable
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **Interactive Interface**: After starting the service, access `http://127.0.0.1:8010` (or the specified port) in your
  browser.
- **API Documentation**: Complete API documentation (Swagger UI) is available at `http://127.0.0.1:8010/docs`.

## Usage

### Example 1: Translating PDF Files (Using `MarkdownBasedWorkflow`)

This is the most common use case. The `minerU` engine is used to convert PDFs to Markdown, followed by translation via
LLM. Here, an asynchronous approach is demonstrated.

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. Build translator configuration
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # Base URL of the AI platform
        api_key="YOUR_ZHIPU_API_KEY",  # API Key for the AI platform
        model_id="glm-4-air",  # Model ID
        to_lang="English",  # Target language
        chunk_size=3000,  # Text chunk size
        concurrent=10  # Number of concurrent processes
    )

    # 2. Build converter configuration (using minerU)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # minerU token
        formula_ocr=True  # Enable formula recognition
    )

    # 3. Build main workflow configuration
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # Specify the parsing engine
        converter_config=converter_config,  # Apply converter configuration
        translator_config=translator_config,  # Apply translator configuration
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML export configuration
    )

    # 4. Instantiate the workflow
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. Load file and execute translation
    print("Starting file loading and translation...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # Or use synchronous method
    # workflow.translate()
    print("Translation completed!")

    # 6. Save results
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # Image-embedded Markdown
    print("Files have been saved in the ./output folder.")

    # Or directly retrieve content strings
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. Build translator configuration
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Japanese",
    )

    # 2. Build main workflow configuration
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = TXTWorkflow(config=workflow_config)

    # 4. Load the file and execute translation
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # Alternatively, use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXT file has been saved.")

    # It's also possible to export the translated plain text
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

```python
import asyncio

from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. Configure the translator
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Japanese",
        json_paths=["$.*", "$.name"]  # Complies with jsonpath-ng syntax; values matching these paths will be translated
    )

    # 2. Configure the main workflow
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = JsonWorkflow(config=workflow_config)

    # 4. Load the file and execute the translation
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # Alternatively, use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_json(name="translated_notes.json")
    print("JSON file has been saved.")

    # The translated JSON text can also be exported
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. Configure the translator
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Japanese",
        insert_mode="replace",  # Options: "replace", "append", "prepend"
        separator="\n",  # Separator used in "append" or "prepend" mode
    )

    # 2. Configure the main workflow
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = DocxWorkflow(config=workflow_config)

    # 4. Load the file and execute translation
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # Alternatively, use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_docx(name="translated_notes.docx")
    print("The docx file has been saved.")

    # The translated docx can also be exported as binary
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

```python
import asyncio

from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. Build translator configuration
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Japanese",
        insert_mode="replace",  # Options: "replace", "append", "prepend"
        separator="\n",  # Separator used in "append" or "prepend" mode
    )

    # 2. Build main workflow configuration
    workflow_config = XlsxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Xlsx2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = XlsxWorkflow(config=workflow_config)

    # 4. Load the file and execute translation
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # Alternatively, use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("The xlsx file has been saved.")

    # It's also possible to export the translated xlsx as binary
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 1. Obtaining API Keys for Large-Scale Language Models

The translation functionality relies on large-scale language models, requiring the retrieval of `base_url`, `api_key`,
and `model_id` from the corresponding AI platform.

> Recommended models: Volcano Engine's `doubao-seed-1-6-250615`, `doubao-seed-1-6-flash-250715`, Zhipu's `glm-4-flash`,
> Alibaba Cloud's `qwen-plus`,  
> `qwen-turbo`, DeepSeek's `deepseek-chat`, etc.

| Platform Name         | API Key Retrieval Method                                                                           | Base URL                                                 |
|-----------------------|----------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| ollama                |                                                                                                    | http://127.0.0.1:11434/v1                                |
| lm studio             |                                                                                                    | http://127.0.0.1:1234/v1                                 |
| openrouter            | [Click to retrieve](https://openrouter.ai/settings/keys)                                           | https://openrouter.ai/api/v1                             |
| openai                | [Click to retrieve](https://platform.openai.com/api-keys)                                          | https://api.openai.com/v1/                               |
| gemini                | [Click to retrieve](https://aistudio.google.com/u/0/apikey)                                        | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek              | [Click to retrieve](https://platform.deepseek.com/api_keys)                                        | https://api.deepseek.com/v1                              |
| Zhipu AI              | [Click to retrieve](https://open.bigmodel.cn/usercenter/apikeys)                                   | https://open.bigmodel.cn/api/paas/v4                     |
| Tencent Hunyuan       | [Click to retrieve](https://console.cloud.tencent.com/hunyuan/api-key)                             | https://api.hunyuan.cloud.tencent.com/v1                 |
| Alibaba Cloud Bailian | [Click to retrieve](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| Volcano Engine        | [Click to retrieve](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| Silicon Flow          | [Click to retrieve](https://cloud.siliconflow.cn/account/ak)                                       | https://api.siliconflow.cn/v1                            |
| DMXAPI                | [Click to retrieve](https://www.dmxapi.cn/token)                                                   | https://www.dmxapi.cn/v1                                 |

### 2. Obtaining minerU Tokens (Online Parsing)

When selecting `mineru` as the document parsing engine (`convert_engine="mineru"`), you need to apply for a free token.

1. Visit the [minerU official website](https://mineru.net/apiManage/docs), register, and apply for the API.
2. Create a new API token in the [API Token Management page](https://mineru.net/apiManage/token).

> **Note**: minerU tokens are valid for 14 days. If expired, recreate them.

### 3. Configuring the docling Engine (Local Parsing)

When selecting `docling` as the document parsing engine (`convert_engine="docling"`), the required models will be
downloaded from Hugging Face upon first use.

**Solutions for Network Issues:**

1. **Setting Up Hugging Face Mirror (Recommended)**:

* **Method A (Environment Variable)**: Set the system environment variable `HF_ENDPOINT` and restart the IDE or
  terminal.

```
   HF_ENDPOINT=https://hf-mirror.com
   ```

* **Method B (In-Code Configuration)**: Add the following code at the beginning of your Python script.

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **Offline Usage (Pre-Downloading Model Packages)**:

* Download `docling_artifact.zip` from [GitHub Releases](https://github.com/xunbu/docutranslate/releases).
* Extract and place it in the project directory.
* Specify the model path in the configuration:

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # Specify the extracted folder
    code_ocr=True,
    formula_ocr=True
)
```

## FAQ

**Q: What should I do if port 8010 is already in use?**  
A: Specify a new port using the `-p` parameter or set the `DOCUTRANSLATE_PORT` environment variable.

**Q: Is scanned document translation supported?**  
A: Yes, it is supported. Use the `mineru` parsing engine, which features powerful OCR capabilities.

**Q: Why is it slow during the first use?**  
A: When using the `docling` engine, the model needs to be downloaded from Hugging Face during the first run. Refer to
the "Network Issue Solutions" section above to speed up this process.

**Q: How can I use it in an intranet (offline) environment?**  
A: It is entirely possible. You need to meet the following two conditions:

1. **Local Parsing Engine**: Use the `docling` engine and follow the "Offline Usage" steps above to download the model
   package in advance.
2. **Local LLM**: Deploy a local language model using tools like [Ollama](https://ollama.com/)
   or [LM Studio](https://lmstudio.ai/), then input the local model's `base_url` in `TranslatorConfig`.

**Q: How does the caching mechanism work?**  
A: `MarkdownBasedWorkflow` automatically caches the results of document parsing (conversion from files to Markdown),
saving time and resources. By default, the cache is stored in memory, recording the last 10 parsing operations. You can
adjust the cache size using the `DOCUTRANSLATE_CACHE_NUM` environment variable.

**Q: How can I use the software via a proxy?**  
A: The software does not use a proxy by default. You can enable proxy usage by setting the `DOCUTRANSLATE_USE_PROXY`
environment variable to `true`.

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">  
 <picture>  
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />  
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />  
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />  
 </picture>  
</a>