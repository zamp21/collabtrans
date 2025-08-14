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

**DocuTranslate** is a document translation tool that leverages advanced document parsing engines (such as [docling](https://github.com/docling-project/docling) and [minerU](https://mineru.net/)) combined with large language models (LLMs) to achieve precise translations for various document formats.

The new architecture adopts **Workflow** as its core, providing a highly configurable and extensible solution for different types of translation tasks.

- ✅ **Supports Multiple Formats**: Capable of translating `pdf`, `docx`, `xlsx`, `md`, `txt`, `json`, `epub`, `srt`, and more.
- ✅ **Table, Formula, and Code Recognition**: Utilizes `docling` and `mineru` to identify and translate tables, formulas, and code frequently found in academic papers.
- ✅ **JSON Translation**: Supports specifying values to be translated in JSON using `jsonpath-ng` syntax.
- ✅ **High-Fidelity Word/Excel Translation**: Supports translation of `docx` and `xlsx` files (currently does not support `doc` or `xls` files) while preserving the original formatting.
- ✅ **Multi-AI Platform Support**: Compatible with most AI platforms, enabling high-performance concurrent AI translation with customizable prompts.
- ✅ **Asynchronous Support**: Designed for high-performance scenarios, offering full asynchronous support and a service interface for parallel task execution.
- ✅ **Interactive Web Interface**: Provides an out-of-the-box Web UI and RESTful API for easy integration and usage.

> When translating `pdf`, `html`, and other files, they are first converted to markdown, which **may lose** the original formatting. Users with strict formatting requirements should take note.

> QQ Discussion Group: 1047781902

**UI Interface**:
![翻译效果](/images/UI界面.png)

**Paper Translation**:
![翻译效果](/images/论文翻译.png)

**Novel Translation**:
![翻译效果](/images/小说翻译.png)

## Bundled Packages

For users who wish to get started quickly, we provide bundled packages on [GitHub Releases](https://github.com/xunbu/docutranslate/releases). Simply download, extract, and fill in your AI platform API-Key to begin.

- **DocuTranslate**: Standard edition, uses the online `minerU` engine for document parsing, recommended for most users.
- **DocuTranslate_full**: Full edition, includes the `docling` local parsing engine, suitable for offline use or scenarios with higher data privacy requirements.

## Installation

### Using pip

```bash
# Basic installation
pip install docutranslate

# To use the docling local parsing engine
pip install docutranslate[docling]
```

### Using uv

```bash
# Initialize environment
uv init

# Basic installation
uv add docutranslate

# Install docling extension
uv add docutranslate[docling]
```

### Using git

```bash
# Initialize environment
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync
```

## Core Concept: Workflow

The heart of the new DocuTranslate is the **Workflow**. Each workflow is a complete end-to-end translation pipeline specifically designed for a particular type of file. Instead of interacting with a monolithic class, you now select and configure a suitable workflow based on your file type.

**Basic Usage Process:**

1. **Select a Workflow**: Choose a workflow based on your input file type (e.g., PDF/Word or TXT), such as `MarkdownBasedWorkflow` or `TXTWorkflow`.
2. **Build Configuration**: Create a corresponding configuration object for the selected workflow (e.g., `MarkdownBasedWorkflowConfig`). This configuration object includes all necessary sub-configurations, such as:
    * **Converter Config**: Defines how to convert the original file (e.g., PDF) into Markdown.
    * **Translator Config**: Specifies which LLM to use, API-Key, target language, etc.
    * **Exporter Config**: Defines specific options for the output format (e.g., HTML).
3. **Instantiate the Workflow**: Create an instance of the workflow using the configuration object.
4. **Execute Translation**: Call the workflow's `.read_*()` and `.translate()` / `.translate_async()` methods.
5. **Export/Save Results**: Invoke `.export_to_*()` or `.save_as_*()` methods to retrieve or save the translated results.

## Available Workflows

| Workflow                     | Applicable Scenarios                                      | Input Formats                            | Output Formats          | Core Configuration Class               |
|:----------------------------|:--------------------------------------------------------|:-----------------------------------------|:-----------------------|:--------------------------------------|
| **`MarkdownBasedWorkflow`** | Processing rich-text documents such as PDFs, Word files, images, etc. Process: `File -> Markdown -> Translation -> Export`. | `.pdf`, `.docx`, `.md`, `.png`, `.jpg`, etc. | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | Processing plain text documents. Process: `txt -> Translation -> Export`. | `.txt` and other plain text formats      | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | Processing JSON files. Process: `json -> Translation -> Export`. | `.json`                                  | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | Processing DOCX files. Process: `docx -> Translation -> Export`. | `.docx`                                  | `.docx`, `.html`       | `DocxWorkflowConfig`          |
| **`XlsxWorkflow`**          | Processing XLSX files. Process: `xlsx -> Translation -> Export`. | `.xlsx`                                  | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | Processing SRT files. Process: `srt -> Translation -> Export`. | `.srt`                                   | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**           | Processing EPUB files. Process: `epub -> Translation -> Export`. | `.epub`                                  | `.epub`, `.html`       | `EpubWorkflowConfig`          |

> PDF format can be exported in the interactive interface.

## Launching Web UI and API Services

For ease of use, DocuTranslate provides a fully functional web interface and RESTful API.

**Starting the Service:**

```bash
# Start the service, default listening on port 8010
docutranslate -i

# Start with a specified port
docutranslate -i -p 8011

# Alternatively, specify the port via environment variable
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **Interactive Interface**: After starting the service, access `http://127.0.0.1:8010` (or your specified port) in a browser.
- **API Documentation**: Complete API documentation (Swagger UI) is available at `http://127.0.0.1:8010/docs`.

## Usage Examples

### Example 1: Translating a PDF File (Using `MarkdownBasedWorkflow`)

This is the most common use case. We will use the `minerU` engine to convert the PDF to Markdown, then use LLM for translation. Here's an example in asynchronous mode.

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. Build translator configuration
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AI platform Base URL
        api_key="YOUR_ZHIPU_API_KEY",  # AI platform API Key
        model_id="glm-4-air",  # Model ID
        to_lang="English",  # Target language
        chunk_size=3000,  # Text chunk size
        concurrent=10  # Concurrency count
    )

    # 2. Build converter configuration (using minerU)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # Your minerU Token
        formula_ocr=True  # Enable formula recognition
    )

    # 3. Build main workflow configuration
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # Specify parsing engine
        converter_config=converter_config,  # Pass converter configuration
        translator_config=translator_config,  # Pass translator configuration
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML export configuration
    )

    # 4. Instantiate the workflow
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. Read file and execute translation
    print("Starting file reading and translation...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # Or use synchronous method
    # workflow.translate()
    print("Translation completed!")

    # 6. Save results
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # Markdown with embedded images
    print("Files saved to ./output folder.")

    # Or directly get content strings
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```


### Example 2: Translating a TXT File (Using `TXTWorkflow`)

For plain text files, the process is simpler as it doesn't require document parsing (conversion) steps. Here's an example using asynchronous method.

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. Configure the translator
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Chinese",
    )

    # 2. Configure the main workflow
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = TXTWorkflow(config=workflow_config)

    # 4. Read the file and perform translation
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # Alternatively, use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXT file saved.")

    # Optionally, export the translated plain text
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```


### Example 3: Translating a JSON File (Using `JsonWorkflow`)

This example demonstrates the asynchronous approach. The `json_paths` item in `JsonTranslatorConfig` specifies the JSON paths to be translated (following `jsonpath-ng` syntax), where only values matching these paths will be translated.


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
        to_lang="Chinese",
        json_paths=["$.*", "$.name"]  # Follows jsonpath-ng syntax; values matching these paths will be translated
    )

    # 2. Configure the main workflow
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = JsonWorkflow(config=workflow_config)

    # 4. Read the file and perform translation
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # Alternatively, use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_json(name="translated_notes.json")
    print("JSON file saved.")

    # Optionally, export the translated JSON text
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```


### Example 4: Translating a DOCX File (Using `DocxWorkflow`)

This example demonstrates the asynchronous approach.

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. Build translator configuration
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="Chinese",
        insert_mode="replace",  # Options: "replace", "append", "prepend"
        separator="\n",  # Separator used in "append" or "prepend" mode
    )

    # 2. Build main workflow configuration
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. Instantiate the workflow
    workflow = DocxWorkflow(config=workflow_config)

    # 4. Read the file and perform translation
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # Or use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_docx(name="translated_notes.docx")
    print("The docx file has been saved.")

    # Alternatively, export the translated docx as binary
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```


### Example 5: Translating an XLSX File (Using `XlsxWorkflow`)

Here, an asynchronous approach is demonstrated.


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
        to_lang="Chinese",
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

    # 4. Read the file and perform translation
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # Or use the synchronous method
    # workflow.translate()

    # 5. Save the results
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("The xlsx file has been saved.")

    # Alternatively, export the translated xlsx as binary
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```


## Prerequisites and Configuration Details

### 1. Obtaining Large Model API Keys

The translation functionality relies on large language models. You need to obtain `base_url`, `api_key`, and `model_id` from the respective AI platforms.

> Recommended models: Volcano Engine's `doubao-seed-1-6-250615`，`doubao-seed-1-6-flash-250715`, Zhipu's `glm-4-flash`, Alibaba Cloud's `qwen-plus`, `qwen-turbo`, Deepseek's `deepseek-chat`, etc.

| Platform Name | API Key Acquisition                                                                 | Base URL                                                  |
|---------------|------------------------------------------------------------------------------------|-----------------------------------------------------------|
| ollama        |                                                                                    | http://127.0.0.1:11434/v1                                 |
| lm studio     |                                                                                    | http://127.0.0.1:1234/v1                                  |
| openrouter    | [Click to Get](https://openrouter.ai/settings/keys)                                | https://openrouter.ai/api/v1                              |
| openai        | [Click to Get](https://platform.openai.com/api-keys)                               | https://api.openai.com/v1/                                |
| gemini        | [Click to Get](https://aistudio.google.com/u/0/apikey)                             | https://generativelanguage.googleapis.com/v1beta/openai/  |
| deepseek      | [Click to Get](https://platform.deepseek.com/api_keys)                             | https://api.deepseek.com/v1                               |
| Zhipu AI      | [Click to Get](https://open.bigmodel.cn/usercenter/apikeys)                        | https://open.bigmodel.cn/api/paas/v4                      |
| Tencent Hunyuan | [Click to Get](https://console.cloud.tencent.com/hunyuan/api-key)                  | https://api.hunyuan.cloud.tencent.com/v1                  |
| Alibaba Cloud Bailian | [Click to Get](https://bailian.console.aliyun.com/?tab=model#/api-key)           | https://dashscope.aliyuncs.com/compatible-mode/v1         |
| Volcano Engine | [Click to Get](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3          |
| Silicon Flow   | [Click to Get](https://cloud.siliconflow.cn/account/ak)                            | https://api.siliconflow.cn/v1                             |
| DMXAPI        | [Click to Get](https://www.dmxapi.cn/token)                                        | https://www.dmxapi.cn/v1                                  |

### 2. Obtain minerU Token (Online Parsing)

If you choose `mineru` as the document parsing engine (`convert_engine="mineru"`), you will need to apply for a free Token.

1. Visit the [minerU official website](https://mineru.net/apiManage/docs) to register and apply for an API.
2. Create a new API Token in the [API Token Management interface](https://mineru.net/apiManage/token).

> **Note**: The minerU Token is valid for 14 days. Please recreate it after expiration.

### 3. docling Engine Configuration (Local Parsing)

If you choose `docling` as the document parsing engine (`convert_engine="docling"`), it will download the required models from Hugging Face upon first use.

**Solutions for Network Issues:**

1. **Set Up Hugging Face Mirror (Recommended)**:

* **Method A (Environment Variable)**: Set the system environment variable `HF_ENDPOINT` and restart your IDE or terminal.
   
```
   HF_ENDPOINT=https://hf-mirror.com
   ```

* **Method B (Code Configuration)**: Add the following code at the beginning of your Python script.


```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```


2. **Offline Usage (Pre-download Model Package)**:

* Download `docling_artifact.zip` from [GitHub Releases](https://github.com/xunbu/docutranslate/releases).
* Extract it to your project directory.
* Specify the model path in the configuration:


```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # Point to the extracted folder
    code_ocr=True,
    formula_ocr=True
)
```


## FAQ

**Q: What if port 8010 is occupied?**
A: Use the `-p` parameter to specify a new port or set the `DOCUTRANSLATE_PORT` environment variable.

**Q: Does it support scanned document translation?**
A: Yes. Use the `mineru` parsing engine, which has powerful OCR capabilities.

**Q: Why is it slow the first time I use it?**
A: If you are using the `docling` engine, it needs to download models from Hugging Face during the first run. Refer to the "Solutions for Network Issues" above to speed up this process.

**Q: How can I use it in an intranet (offline) environment?**
A: It is entirely possible. You need to meet two conditions:

1. **Local Parsing Engine**: Use the `docling` engine and follow the "Offline Usage" instructions above to pre-download the model package.
2. **Local LLM**: Deploy a language model locally using tools like [Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/), and fill in the `base_url` of the local model in `TranslatorConfig`.

**Q: How does the caching mechanism work?**
A: `MarkdownBasedWorkflow` automatically caches the results of document parsing (conversion from file to Markdown) to avoid repetitive parsing that consumes time and resources. By default, the cache is stored in memory and records the most recent 10 parses. You can modify the cache size via the `DOCUTRANSLATE_CACHE_NUM` environment variable.

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>