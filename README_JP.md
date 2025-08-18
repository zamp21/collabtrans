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

**DocuTranslate** は、高度なドキュメント解析エンジン（[docling](https://github.com/docling-project/docling) や [minerU](https://mineru.net/) など）と大規模言語モデル（LLM）を組み合わせたファイル翻訳ツールです。多種多様な形式のドキュメントを高精度に翻訳することができます。

新しいバージョンのアーキテクチャでは **ワークフロー（Workflow）** を中核として採用し、さまざまなタイプの翻訳タスクに対して高度に設定可能かつ拡張性のあるソリューションを提供しています。

- ✅ **多種多様なフォーマットをサポート**：`pdf`、`docx`、`xlsx`、`md`、`txt`、`json`、`epub`、`srt` などのファイルを翻訳可能です。
- ✅ **表、数式、コードの認識**：`docling`、`mineru` を活用し、学術論文によく出現する表、数式、コードの認識と翻訳を実現します。
- ✅ **json翻訳**：jsonパス（`jsonpath-ng`構文規範）を通じてjson内で翻訳が必要な値を指定することをサポートします。
- ✅ **Word/Excel高忠実度翻訳**：`docx`、`xlsx`ファイル（`doc`、`xls`ファイルは現在サポートしていません）の翻訳をサポートし、元のフォーマットを保持して翻訳します。
- ✅ **複数AIプラットフォームのサポート**：ほとんどのAIプラットフォームをサポートし、カスタムプロンプトによる並行高性能AI翻訳を実現できます。
- ✅ **非同期サポート**：高性能なシナリオ向けに設計され、完全な非同期サポートを提供し、マルチタスク並行処理が可能なサービスインターフェースを実現しています。
- ✅ **インタラクティブWebインターフェース**：すぐに使用できるWeb UIとRESTful APIを提供し、統合と使用が容易です。

> `pdf`を翻訳する場合、最初にマークダウンに変換されるため、元の排版が**失われます**。排版に要件があるユーザーは注意してください。

> QQ交流グループ：1047781902

**UIインターフェース**：
![翻译效果](/images/UI界面.png)

**論文翻訳**：
![翻译效果](/images/论文翻译.png)

**小説翻訳**：
![翻译效果](/images/小说翻译.png)

## 統合パッケージ

すぐに始めたいユーザーのために、[GitHub Releases](https://github.com/xunbu/docutranslate/releases) で統合パッケージを提供しています。ダウンロードして解凍し、AIプラットフォームのAPIキーを入力するだけで使用を開始できます。

- **DocuTranslate**：標準版で、オンラインの `minerU` エンジンを使用してドキュメントを解析します。ほとんどのユーザーに推奨されます。
- **DocuTranslate_full**：完全版で、`docling` ローカル解析エンジンを内蔵しています。オフラインまたはデータプライバシーにより高い要件があるシナリオに適しています。

## インストール

### pipを使用する場合


```bash
# 基本インストール
pip install docutranslate

# docling ローカル解析エンジンを使用する場合は
pip install docutranslate[docling]
```


### uvを使用する場合


```bash
# 環境を初期化
uv init

# 基本インストール
uv add docutranslate

# docling 拡張機能をインストール
uv add docutranslate[docling]
```


### gitを使用する場合


```bash
# 環境を初期化
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

## コアコンセプト：ワークフロー (Workflow)

新バージョンの DocuTranslate のコアは **ワークフロー (Workflow)** です。各ワークフローは特定のファイルタイプ向けに設計された完全なエンドツーエンドの翻訳パイプラインです。これまでのように大きなクラスとやり取りするのではなく、ファイルタイプに応じて適切なワークフローを選択して設定することになります。

**基本的な使用手順は以下の通りです：**

1. **ワークフローの選択**：入力ファイルタイプ（例：PDF/Word または TXT）に基づいてワークフローを選択します。例えば、`MarkdownBasedWorkflow` または `TXTWorkflow` などです。
2. **設定の構築**：選択したワークフローに対応する設定オブジェクト（`MarkdownBasedWorkflowConfig` など）を作成します。この設定オブジェクトには、以下のような必要なすべてのサブ設定が含まれています：
    * **コンバーター設定 (Converter Config)**：PDF などの元ファイルを Markdown に変換する方法を定義します。
    * **翻訳者設定 (Translator Config)**：使用する LLM、API-Key、対象言語などを定義します。
    * **エクスポーター設定 (Exporter Config)**：HTML などの出力形式の特定オプションを定義します。
3. **ワークフローのインスタンス化**：設定オブジェクトを使用してワークフローのインスタンスを作成します。
4. **翻訳の実行**：ワークフローの `.read_*()` メソッドと `.translate()` / `.translate_async()` メソッドを呼び出します。
5. **結果のエクスポート/保存**：`.export_to_*()` メソッドまたは `.save_as_*()` メソッドを呼び出して、翻訳結果を取得または保存します。

## 使用可能なワークフロー

| ワークフロー                   | 適用シーン                                                              | 入力フォーマット                               | 出力フォーマット           | コア設定クラス                      |
|:--------------------------|:--------------------------------------------------------------------|:------------------------------------------|:-----------------------|:-----------------------------|
| **`MarkdownBasedWorkflow`** | PDF、Word、画像などのリッチテキスト文書を処理する。フロー：`ファイル -> Markdown -> 翻訳 -> エクスポート`。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` など | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | プレーンテキスト文書を処理する。フロー：`txt -> 翻訳 -> エクスポート`。                      | `.txt` およびその他のプレーンテキストフォーマット         | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | jsonファイルを処理する。フロー：`json -> 翻訳 -> エクスポート`。                          | `.json`                                   | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | docxファイルを処理する。フロー：`docx -> 翻訳 -> エクスポート`。                          | `.docx`                                   | `.docx`, `.html`       | `docxWorkflowConfig`          |
| **`XlsxWorkflow`**          | xlsxファイルを処理する。フロー：`xlsx -> 翻訳 -> エクスポート`。                          | `.xlsx`                                   | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | srtファイルを処理する。フロー：`srt -> 翻訳 -> エクスポート`。                            | `.srt`                                    | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**          | epubファイルを処理する。フロー：`epub -> 翻訳 -> エクスポート`。                          | `.epub`                                   | `.epub`, `.html`       | `EpubWorkflowConfig`          |
| **`HtmlWorkflow`**          | htmlファイルを処理する。フロー：`html -> 翻訳 -> エクスポート`。                          | `.html`, `.htm`                           | `.html`                | `HtmlWorkflowConfig`          |

> インタラクティブインターフェースではpdf形式でエクスポートできます

## Web UI と API サービスの起動

使いやすさを考慮して、DocuTranslateは機能豊富なWebインターフェースとRESTful APIを提供しています。

**サービスの起動:**

```bash
# サービスを起動し、デフォルトでポート8010を監視
docutranslate -i

# ポートを指定して起動
docutranslate -i -p 8011

# 環境変数でポートを指定することも可能
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **インタラクティブインターフェース**: サービスを起動した後、ブラウザで `http://127.0.0.1:8010`（または指定したポート）にアクセスしてください。
- **APIドキュメント**: 完全なAPIドキュメント（Swagger UI）は `http://127.0.0.1:8010/docs` にあります。

## 使用方法

### 例 1: PDFファイルの翻訳 (`MarkdownBasedWorkflow` を使用)

これは最も一般的なユースケースです。`minerU` エンジンを使用して PDF を Markdown に変換し、LLM で翻訳を行います。ここでは非同期方式を例に挙げます。


```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AI プラットフォームの Base URL
        api_key="YOUR_ZHIPU_API_KEY",  # AI プラットフォームの API Key
        model_id="glm-4-air",  # モデル ID
        to_lang="English",  # 目標言語
        chunk_size=3000,  # テキストのチャンクサイズ
        concurrent=10  # 同時実行数
    )

    # 2. コンバーターの設定を構築 (minerU を使用)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # あなたの minerU Token
        formula_ocr=True  # 数式認識を有効にする
    )

    # 3. メインワークフローの設定を構築
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 解析エンジンを指定
        converter_config=converter_config,  # コンバーターの設定を渡す
        translator_config=translator_config,  # 翻訳機の設定を渡す
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML エクスポート設定
    )

    # 4. ワークフローをインスタンス化
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. ファイルを読み込み、翻訳を実行
    print("ファイルの読み込みと翻訳を開始します...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()
    print("翻訳が完了しました！")

    # 6. 結果を保存
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 画像を埋め込んだ markdown
    print("ファイルが ./output フォルダに保存されました。")

    # または直接内容文字列を取得
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```


### 例 2: TXTファイルの翻訳 (`TXTWorkflow` を使用)

純粋なテキストファイルの場合、ドキュメントの解析（変換）ステップが不要なため、プロセスがより簡単です。ここでは非同期方式を例に挙げます。

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. 翻訳者設定を構築する
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
    )

    # 2. メインワークフロー設定を構築する
    workflow_config = TXTWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=TXT2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化する
    workflow = TXTWorkflow(config=workflow_config)

    # 4. ファイルを読み取り、翻訳を実行する
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # または同期メソッドを使用する
    # workflow.translate()

    # 5. 結果を保存する
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXT ファイルが保存されました。")

    # 翻訳されたプレーンテキストをエクスポートすることもできます
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```


### 例 3: json ファイルを翻訳する (`JsonWorkflow` を使用)

ここでは非同期方式を例として示します。JsonTranslatorConfig の json_paths 項目では、翻訳する json パスを指定する必要があります（jsonpath-ng 構文規則に準拠）。
json パスに一致する値のみが翻訳されます。


```python
import asyncio

from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. 翻訳者設定を構築する
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="中文",
        json_paths=["$.*", "$.name"]  # jsonpath-ngパス構文に準拠し、パスに一致する値がすべて翻訳されます
    )

    # 2. メインワークフロー設定を構築する
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化する
    workflow = JsonWorkflow(config=workflow_config)

    # 4. ファイルを読み取り、翻訳を実行する
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # または同期メソッドを使用する
    # workflow.translate()

    # 5. 結果を保存する
    workflow.save_as_json(name="translated_notes.json")
    print("jsonファイルが保存されました。")

    # 翻訳されたjsonテキストをエクスポートすることもできます
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```


### 例 4: docx ファイルを翻訳する (`DocxWorkflow` を使用)

ここでは非同期方式を例として示します。

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
        insert_mode="replace",  # オプション: "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用されるセパレータ
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

    # 翻訳されたdocxのバイナリをエクスポートすることもできる
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
        insert_mode="replace",  # オプション: "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用されるセパレータ
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

    # 翻訳されたxlsxのバイナリをエクスポートすることもできる
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```


## 前提条件と設定の詳細説明

### 1. 大規模言語モデルAPIキーの取得

翻訳機能は大規模言語モデルに依存しており、対応するAIプラットフォームから`base_url`、`api_key`、`model_id`を取得する必要があります。

> 推奨モデル：火山引擎の`doubao-seed-1-6-250615`、`doubao-seed-1-6-flash-250715`、智譜の`glm-4-flash`、アリババクラウドの`qwen-plus`、`qwen-turbo`、deepseekの`deepseek-chat`など。

| プラットフォーム名 | APIキーの取得方法                                                                      | baseurl                                                  |
|------------|-----------------------------------------------------------------------------------|----------------------------------------------------------|
| ollama     |                                                                                   | http://127.0.0.1:11434/v1                                |
| lm studio  |                                                                                   | http://127.0.0.1:1234/v1                                 |
| openrouter | [クリックして取得](https://openrouter.ai/settings/keys)                               | https://openrouter.ai/api/v1                             |
| openai     | [クリックして取得](https://platform.openai.com/api-keys)                                | https://api.openai.com/v1/                               |
| gemini     | [クリックして取得](https://aistudio.google.com/u/0/apikey)                              | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek   | [クリックして取得](https://platform.deepseek.com/api_keys)                              | https://api.deepseek.com/v1                              |
| 智譜ai       | [クリックして取得](https://open.bigmodel.cn/usercenter/apikeys)                         | https://open.bigmodel.cn/api/paas/v4                     |
| 騰訊混元       | [クリックして取得](https://console.cloud.tencent.com/hunyuan/api-key)                   | https://api.hunyuan.cloud.tencent.com/v1                 |
| 阿里云百煉      | [クリックして取得](https://bailian.console.aliyun.com/?tab=model#/api-key)              | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| 火山引擎       | [クリックして取得](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| 硅基流動       | [クリックして取得](https://cloud.siliconflow.cn/account/ak)                             | https://api.siliconflow.cn/v1                            |
| DMXAPI     | [クリックして取得](https://www.dmxapi.cn/token)                                           | https://www.dmxapi.cn/v1                                 |

### 2. minerU Token の取得（オンライン解析）

ドキュメント解析エンジンとして `mineru` を選択した場合（`convert_engine="mineru"`）、無料の Token を申請する必要があります。

1. [minerU 公式サイト](https://mineru.net/apiManage/docs) にアクセスし、登録して API を申請します。
2. [API Token 管理画面](https://mineru.net/apiManage/token) で新しい API Token を作成します。

> **注意**: minerU Token の有効期限は14日です。期限切れの場合は再作成してください。

### 3. docling エンジンの設定（ローカル解析）

ドキュメント解析エンジンとして `docling` を選択した場合（`convert_engine="docling"`）、初回使用時に必要なモデルが Hugging Face からダウンロードされます。

**ネットワーク問題の解決策:**

1. **Hugging Face ミラーの設定（推奨）**:

* **方法 A（環境変数）**: システム環境変数 `HF_ENDPOINT` を設定し、IDE またはターミナルを再起動します。
   
```
   HF_ENDPOINT=https://hf-mirror.com
   ```

* **方法 B（コード内で設定）**: Python スクリプトの先頭に以下のコードを追加します。


```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```


2. **オフライン使用（事前にモデルパッケージをダウンロード）**:

* [GitHub Releases](https://github.com/xunbu/docutranslate/releases) から `docling_artifact.zip` をダウンロードします。
* プロジェクトディレクトリに解凍します。
* 設定でモデルパスを指定します：


```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # 解凍したフォルダを指定
    code_ocr=True,
    formula_ocr=True
)
```


## FAQ

**Q: 8010ポートが占有されている場合はどうしますか？**
A: `-p` パラメータで新しいポートを指定するか、`DOCUTRANSLATE_PORT` 環境変数を設定してください。

**Q: スキャン文書の翻訳はサポートされていますか？**
A: サポートされています。強力なOCR機能を備えた `mineru` 解析エンジンを使用してください。

**Q: 初回使用時に遅いのはなぜですか？**
A: `docling` エンジンを使用する場合、初回実行時に Hugging Face からモデルをダウンロードする必要があります。このプロセスを加速するには、上記の「ネットワーク問題の解決策」を参照してください。

**Q: イントラネット（オフライン）環境でどのように使用できますか？**
A: 完全に可能です。以下の2つの条件を満たす必要があります：

1. **ローカル解析エンジン**: `docling` エンジンを使用し、上記の「オフライン使用」のガイドに従って事前にモデルパッケージをダウンロードします。
2. **ローカル LLM**: [Ollama](https://ollama.com/) や [LM Studio](https://lmstudio.ai/) などのツールを使用してローカルに言語モデルをデプロイし、`TranslatorConfig` でローカルモデルの `base_url` を入力します。

**Q: キャッシュメカニズムはどのように機能しますか？**
A: `MarkdownBasedWorkflow` はドキュメント解析（ファイルからMarkdownへの変換）の結果を自動的にキャッシュし、繰り返し解析による時間とリソースの浪費を回避します。キャッシュはデフォルトでメモリに保存され、直近の10回の解析が記録されます。環境変数 `DOCUTRANSLATE_CACHE_NUM` を通じてキャッシュ数を変更することができます。

**Q: ソフトウェアをプロキシ経由で使用するにはどうすればよいですか**
A: ソフトウェアはデフォルトでプロキシを使用しません。環境変数 `DOCUTRANSLATE_PROXY_ENABLED` を `true` に設定することで、ソフトウェアがプロキシ経由で通信するようになります。

## スター履歴

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>