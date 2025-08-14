<p align="center">
  <img src="./DocuTranslate.png" alt="プロジェクトロゴ" style="width: 150px">
</p>

# DocuTranslate

[![GitHub stars](https://img.shields.io/github/stars/xunbu/docutranslate?style=flats&logo=github&color=blue)](https://github.com/xunbu/docutranslate)
[![github下载数](https://img.shields.io/github/downloads/xunbu/docutranslate/total?logo=github)](https://github.com/xunbu/docutranslate/releases)
[![PyPI version](https://img.shields.io/pypi/v/docutranslate)](https://pypi.org/project/docutranslate/)
[![python版本](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![开源协议](https://img.shields.io/github/license/xunbu/docutranslate)](./LICENSE)

[**简体中文**](/README_ZH.md) / [**English**](/README.md) / [**日本語**](/README_JP.md)

**DocuTranslate**は、高度なドキュメント解析エンジン（[docling](https://github.com/docling-project/docling)や[minerU](https://mineru.net/)など）と大規模言語モデル（LLM）を組み合わせたファイル翻訳ツールです。多種多様なフォーマットのドキュメントを高精度に翻訳することができます。

新しいアーキテクチャでは**ワークフロー（Workflow）**を中核として採用し、さまざまなタイプの翻訳タスクに対して高度に設定可能で拡張性の高いソリューションを提供しています。

- ✅ **多種フォーマット対応**：`pdf`、`docx`、`xlsx`、`md`、`txt`、`json`、`epub`、`srt`など多くのファイルを翻訳可能です。
- ✅ **表、数式、コードの認識**：`docling`や`mineru`を搭載することで、学術論文によく出現する表、数式、コードの認識と翻訳を実現しています。
- ✅ **json翻訳**：jsonパス（`jsonpath-ng`構文仕様）を通じて、json内で翻訳が必要な値を指定することをサポートしています。
- ✅ **Word/Excel高忠実度翻訳**：`docx`、`xlsx`ファイル（`doc`、`xls`ファイルは暫定的にサポートしていません）の翻訳をサポートし、元のフォーマットを保持したまま翻訳を行います。
- ✅ **複数AIプラットフォーム対応**：ほとんどのAIプラットフォームに対応しており、カスタムプロンプトによる並行高性能AI翻訳を実現できます。
- ✅ **非同期対応**：高性能なシーンを念頭に設計されており、完全な非同期サポートを提供し、マルチタスク並行処理が可能なサービスインターフェースを実装しています。
- ✅ **インタラクティブWebインターフェース**：すぐに使えるWeb UIとRESTful APIを提供し、統合と使用が容易です。

> `pdf`、`html`などのファイルを翻訳する場合、まずmarkdownに変換されます。これにより元の排版が**失われる**可能性があるため、排版に関する要求があるユーザーはご注意ください。

> QQ交流グループ：1047781902

**UIインターフェース**：
![翻译效果](/images/UI界面.png)

**論文翻訳**：
![翻译效果](/images/论文翻译.png)

**小説翻訳**：
![翻译效果](/images/小说翻译.png)

## 統合パッケージ

すぐに始めたいユーザーのために、[GitHub Releases](https://github.com/xunbu/docutranslate/releases)で統合パッケージを提供しています。ダウンロードして解凍し、AIプラットフォームのAPIキーを入力するだけで使用を開始できます。

- **DocuTranslate**：標準版で、オンラインの`minerU`エンジンを使用してドキュメントを解析します。ほとんどのユーザーに推奨します。
- **DocuTranslate_full**：フル版で、`docling`ローカル解析エンジンを内蔵しています。オフライン環境またはデータプライバシーにより高い要求があるシーンに適しています。

## インストール

### pipを使用する場合


```bash
# 基本インストール
pip install docutranslate

# doclingローカル解析エンジンを使用する場合
pip install docutranslate[docling]
```


### uvを使用する場合


```bash
# 環境の初期化
uv init

# 基本インストール
uv add docutranslate

# docling拡張機能のインストール
uv add docutranslate[docling]
```


### gitを使用する場合


```bash
# 環境の初期化
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

## コアコンセプト：ワークフロー (Workflow)

新版DocuTranslateのコアは**ワークフロー (Workflow)** です。各ワークフローは、特定のファイルタイプ向けに設計された完全なエンドツーエンドの翻訳パイプラインです。これまでのように大きなクラスとやり取りするのではなく、ファイルタイプに応じて適切なワークフローを選択して設定することになります。

**基本的な使用手順は以下の通りです：**

1. **ワークフローの選択**：入力ファイルタイプ（例：PDF/Word または TXT）に基づいて、`MarkdownBasedWorkflow` や `TXTWorkflow` などのワークフローを選択します。
2. **設定の構築**：選択したワークフローに対応する設定オブジェクト（例：`MarkdownBasedWorkflowConfig`）を作成します。この設定オブジェクトには、以下のような必要なサブ設定がすべて含まれています：
    * **コンバーター設定 (Converter Config)**：PDFなどの元ファイルをMarkdownに変換する方法を定義します。
    * **翻訳者設定 (Translator Config)**：使用するLLM、APIキー、目標言語などを定義します。
    * **エクスポーター設定 (Exporter Config)**：HTMLなどの出力形式の特定オプションを定義します。
3. **ワークフローのインスタンス化**：設定オブジェクトを使用してワークフローのインスタンスを作成します。
4. **翻訳の実行**：ワークフローの `.read_*()` メソッドと `.translate()` / `.translate_async()` メソッドを呼び出します。
5. **結果のエクスポート/保存**：`.export_to_*()` メソッドまたは `.save_as_*()` メソッドを呼び出して、翻訳結果を取得または保存します。

## 使用可能なワークフロー

| ワークフロー                   | 適用シーン                                                      | 入力フォーマット                               | 出力フォーマット             | コア設定クラス                       |
|:--------------------------|:------------------------------------------------------------|:------------------------------------------|:-----------------------|:--------------------------------|
| **`MarkdownBasedWorkflow`** | PDF、Word、画像などのリッチテキスト文書を処理します。フロー：`ファイル -> Markdown -> 翻訳 -> エクスポート`。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` など | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig`   |
| **`TXTWorkflow`**           | プレーンテキスト文書を処理します。フロー：`txt -> 翻訳 -> エクスポート`。                | `.txt` 及びその他のプレーンテキストフォーマット          | `.txt`, `.html`        | `TXTWorkflowConfig`             |
| **`JsonWorkflow`**          | jsonファイルを処理します。フロー：`json -> 翻訳 -> エクスポート`。                      | `.json`                                  | `.json`, `.html`       | `JsonWorkflowConfig`            |
| **`DocxWorkflow`**          | docxファイルを処理します。フロー：`docx -> 翻訳 -> エクスポート`。                      | `.docx`                                  | `.docx`, `.html`       | `docxWorkflowConfig`            |
| **`XlsxWorkflow`**          | xlsxファイルを処理します。フロー：`xlsx -> 翻訳 -> エクスポート`。                      | `.xlsx`                                  | `.xlsx`, `.html`       | `XlsxWorkflowConfig`            |
| **`SrtWorkflow`**           | srtファイルを処理します。フロー：`srt -> 翻訳 -> エクスポート`。                        | `.srt`                                   | `.srt`, `.html`        | `SrtWorkflowConfig`             |
| **`EpubWorkflow`**          | epubファイルを処理します。フロー：`epub -> 翻訳 -> エクスポート`。                      | `.epub`                                  | `.epub`, `.html`       | `EpubWorkflowConfig`            |

> インタラクティブインターフェースではpdf形式でエクスポートできます

## Web UI と API サービスの起動

使いやすさを向上させるため、DocuTranslateは機能豊富なWebインターフェースとRESTful APIを提供しています。

**サービスの起動:**

```bash
# サービスを起動し、デフォルトで8010ポートを監視します
docutranslate -i

# ポートを指定して起動します
docutranslate -i -p 8011

# 環境変数でポートを指定することもできます
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **インタラクティブインターフェース**: サービスを起動した後、ブラウザで `http://127.0.0.1:8010`（または指定したポート）にアクセスしてください。
- **APIドキュメント**: 完全なAPIドキュメント（Swagger UI）は `http://127.0.0.1:8010/docs` にあります。

## 使用方法

### 例1: PDFファイルの翻訳（`MarkdownBasedWorkflow` 使用）

これは最も一般的なユースケースです。`minerU` エンジンを使用してPDFをMarkdownに変換し、LLMを使用して翻訳します。ここでは非同期方式を例として取り上げます。

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 翻訳者設定の構築
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AIプラットフォームのBase URL
        api_key="YOUR_ZHIPU_API_KEY",  # AIプラットフォームのAPI Key
        model_id="glm-4-air",  # モデルID
        to_lang="English",  # 目標言語
        chunk_size=3000,  # テキストのチャンクサイズ
        concurrent=10  # 並行数
    )

    # 2. コンバーター設定の構築（minerUを使用）
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # あなたのminerU Token
        formula_ocr=True  # 数式認識を有効にする
    )

    # 3. メインワークフロー設定の構築
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 解析エンジンを指定
        converter_config=converter_config,  # コンバーター設定を渡す
        translator_config=translator_config,  # 翻訳者設定を渡す
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTMLエクスポート設定
    )

    # 4. ワークフローのインスタンス化
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. ファイルを読み取り翻訳を実行
    print("ファイルの読み取りと翻訳を開始します...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()
    print("翻訳が完了しました！")

    # 6. 結果を保存
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 画像を埋め込んだmarkdown
    print("ファイルが ./output フォルダーに保存されました。")

    # または直接コンテンツ文字列を取得
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```


### 例 2: TXTファイルの翻訳（`TXTWorkflow`を使用）

純粋なテキストファイルの場合、ドキュメント解析（変換）ステップが不要なため、フローはより簡単です。ここでは非同期方式を例に挙げます。

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. 翻訳者設定を構築
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
    )

    # 2. メインワークフロー設定を構築
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = TXTWorkflow(config=workflow_config)

    # 4. ファイルを読み込み、翻訳を実行
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # または同期的な方法を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXT ファイルが保存されました。")

    # 翻訳後のプレーンテキストをエクスポートすることもできます
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```


### 例 3: json ファイルを翻訳する (`JsonWorkflow` を使用)

ここでは非同期方式を例に挙げます。JsonTranslatorConfigのjson_paths項目では、翻訳するjsonパスを指定する必要があります（jsonpath-ng構文規則に準拠）。jsonパスに一致する値のみが翻訳されます。


```python
import asyncio

from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. 翻訳者設定を構築
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        json_paths=["$.*", "$.name"]  # jsonpath-ngパス構文に準拠、パスに一致する値が翻訳されます
    )

    # 2. メインワークフロー設定を構築
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = JsonWorkflow(config=workflow_config)

    # 4. ファイルを読み込み、翻訳を実行
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # または同期的な方法を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_json(name="translated_notes.json")
    print("jsonファイルが保存されました。")

    # 翻訳後のjsonテキストをエクスポートすることもできます
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```


### 例 4: docx ファイルを翻訳する (`DocxWorkflow` を使用)

ここでは非同期方式を例に挙げます。

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. 翻訳者設定を構築する
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # オプション "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用するセパレータ
    )

    # 2. メインワークフロー設定を構築する
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化する
    workflow = DocxWorkflow(config=workflow_config)

    # 4. ファイルを読み込み、翻訳を実行する
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # または同期メソッドを使用する
    # workflow.translate()

    # 5. 結果を保存する
    workflow.save_as_docx(name="translated_notes.docx")
    print("docxファイルが保存されました。")

    # 翻訳されたdocxのバイナリをエクスポートすることもできます
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```


### 例 5: xlsxファイルを翻訳する (`XlsxWorkflow` を使用)

ここでは非同期方式を例に挙げます。


```python
import asyncio

from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. 翻訳者設定を構築する
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # オプション "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用するセパレータ
    )

    # 2. メインワークフロー設定を構築する
    workflow_config = XlsxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Xlsx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化する
    workflow = XlsxWorkflow(config=workflow_config)

    # 4. ファイルを読み込み、翻訳を実行する
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # または同期メソッドを使用する
    # workflow.translate()

    # 5. 結果を保存する
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("xlsxファイルが保存されました。")

    # 翻訳されたxlsxのバイナリをエクスポートすることもできます
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```


## 前提条件と設定の詳細説明

### 1. 大規模言語モデルAPIキーの取得

翻訳機能は大規模言語モデルに依存しているため、対応するAIプラットフォームから`base_url`、`api_key`、`model_id`を取得する必要があります。

> 推奨モデル：火山エンジンの`doubao-seed-1-6-250615`、`doubao-seed-1-6-flash-250715`、智譜の`glm-4-flash`、アリババクラウドの`qwen-plus`、`qwen-turbo`、deepseekの`deepseek-chat`など。

| プラットフォーム名 | APIキーの取得                                                                          | baseurl                                                  |
|------------|-------------------------------------------------------------------------------------|----------------------------------------------------------|
| ollama     |                                                                                     | http://127.0.0.1:11434/v1                                |
| lm studio  |                                                                                     | http://127.0.0.1:1234/v1                                 |
| openrouter | [クリックして取得](https://openrouter.ai/settings/keys)                               | https://openrouter.ai/api/v1                             |
| openai     | [クリックして取得](https://platform.openai.com/api-keys)                                | https://api.openai.com/v1/                               |
| gemini     | [クリックして取得](https://aistudio.google.com/u/0/apikey)                              | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek   | [クリックして取得](https://platform.deepseek.com/api_keys)                              | https://api.deepseek.com/v1                              |
| 智譜ai       | [クリックして取得](https://open.bigmodel.cn/usercenter/apikeys)                           | https://open.bigmodel.cn/api/paas/v4                     |
| 騰訊混元       | [クリックして取得](https://console.cloud.tencent.com/hunyuan/api-key)                     | https://api.hunyuan.cloud.tencent.com/v1                 |
| アリババクラウド百煉 | [クリックして取得](https://bailian.console.aliyun.com/?tab=model#/api-key)                | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| 火山エンジン     | [クリックして取得](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| シリコンフロー   | [クリックして取得](https://cloud.siliconflow.cn/account/ak)                               | https://api.siliconflow.cn/v1                            |
| DMXAPI     | [クリックして取得](https://www.dmxapi.cn/token)                                           | https://www.dmxapi.cn/v1                                 |

### 2. minerU Token の取得（オンライン解析）

ドキュメント解析エンジンとして `mineru` を選択した場合（`convert_engine="mineru"`）、無料の Token を申請する必要があります。

1. [minerU 公式サイト](https://mineru.net/apiManage/docs) にアクセスし、登録して API を申請します。
2. [API Token 管理画面](https://mineru.net/apiManage/token) で新しい API Token を作成します。

> **注意**: minerU Token の有効期限は14日です。期限切れの場合は再作成してください。

### 3. docling エンジン設定（ローカル解析）

ドキュメント解析エンジンとして `docling` を選択した場合（`convert_engine="docling"`）、初回使用時に必要なモデルが Hugging Face からダウンロードされます。

**ネットワーク問題の解決策:**

1. **Hugging Face ミラーの設定（推奨）**:

* **方法 A（環境変数）**: システム環境変数 `HF_ENDPOINT` を設定し、IDE またはターミナルを再起動します。
   
```
   HF_ENDPOINT=https://hf-mirror.com
   ```

* **方法 B（コード内設定）**: Python スクリプトの先頭に以下のコードを追加します。


```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```


2. **オフライン使用（事前モデルパッケージのダウンロード）**:

* [GitHub Releases](https://github.com/xunbu/docutranslate/releases) から `docling_artifact.zip` をダウンロードします。
* プロジェクトディレクトリに解凍します。
* 設定でモデルパスを指定します：


```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # 解凍後のフォルダを指定
    code_ocr=True,
    formula_ocr=True
)
```


## FAQ

**Q: 8010 ポートが占有されている場合はどうしますか？**
A: `-p` パラメータを使用して新しいポートを指定するか、`DOCUTRANSLATE_PORT` 環境変数を設定します。

**Q: スキャン文書の翻訳に対応していますか？**
A: 対応しています。強力な OCR 機能を備えた `mineru` 解析エンジンを使用してください。

**Q: 初回使用時に遅いのはなぜですか？**
A: `docling` エンジンを使用している場合、初回実行時に Hugging Face からモデルをダウンロードする必要があります。このプロセスを加速するには、上記の「ネットワーク問題の解決策」を参照してください。

**Q: イントラネット（オフライン）環境でどのように使用しますか？**
A: 完全に可能です。以下の2つの条件を満たす必要があります：

1. **ローカル解析エンジン**: `docling` エンジンを使用し、上記の「オフライン使用」のガイドに従って事前にモデルパッケージをダウンロードします。
2. **ローカル LLM**: [Ollama](https://ollama.com/) や [LM Studio](https://lmstudio.ai/) などのツールを使用してローカルに言語モデルをデプロイし、`TranslatorConfig` でローカルモデルの `base_url` を入力します。

**Q: キャッシュメカニズムはどのように機能しますか？**
A: `MarkdownBasedWorkflow` はドキュメント解析（ファイルからMarkdownへの変換）の結果を自動的にキャッシュし、繰り返し解析による時間とリソースの消費を回避します。キャッシュはデフォルトでメモリに保存され、直近の10回の解析が記録されます。`DOCUTRANSLATE_CACHE_NUM` 環境変数を通じてキャッシュ数を変更することができます。

## スター履歴

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>