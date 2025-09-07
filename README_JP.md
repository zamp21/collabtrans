<p align="center">
  <img src="./DocuTranslate.png" alt="プロジェクトロゴ" style="width: 150px">
</p>

<h1 align="center">DocuTranslate</h1>

<p align="center">
  <a href="https://github.com/xunbu/docutranslate/stargazers"><img src="https://img.shields.io/github/stars/xunbu/docutranslate?style=flat-square&logo=github&color=blue" alt="GitHubスター"></a>
  <a href="https://github.com/xunbu/docutranslate/releases"><img src="https://img.shields.io/github/downloads/xunbu/docutranslate/total?logo=github&style=flat-square" alt="GitHubダウンロード数"></a>
  <a href="https://pypi.org/project/docutranslate/"><img src="https://img.shields.io/pypi/v/docutranslate?style=flat-square" alt="PyPIバージョン"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white&style=flat-square" alt="Pythonバージョン"></a>
  <a href="./LICENSE"><img src="https://img.shields.io/github/license/xunbu/docutranslate?style=flat-square" alt="ライセンス"></a>
</p>

<p align="center">
  <a href="/README_ZH.md"><strong>简体中文</strong></a> / <a href="/README.md"><strong>English</strong></a> / <a href="/README_JP.md"><strong>日本語</strong></a>
</p>

<p align="center">
  大規模言語モデルに基づく軽量なローカルファイル翻訳ツール
</p>

- ✅ **多様なフォーマットをサポート**：`pdf`、`docx`、`xlsx`、`md`、`txt`、`json`、`epub`、`srt` など、さまざまなファイルを翻訳できます。
- ✅ **用語集の自動生成**：用語集を自動生成し、専門用語の統一を実現します。
- ✅ **PDFの表、数式、コード認識**：`docling`、`mineru` PDF解析エンジンにより、学術論文によく見られる表、数式、コードを認識し、翻訳します。
- ✅ **JSON翻訳**：JSON Path (`jsonpath-ng`構文仕様) を用いて、翻訳対象の値を指定できます。
- ✅ **Word/Excelのフォーマットを維持した翻訳**：`docx`、`xlsx`ファイルの元のフォーマットを維持したまま翻訳をサポートします（現在
  `doc`、`xls`ファイルは未対応）。
- ✅ **マルチAIプラットフォーム対応**：ほとんどのAIプラットフォームをサポートし、カスタムプロンプトによる並列・高性能なAI翻訳を実現します。
- ✅ **非同期サポート**：高性能なシーン向けに設計され、完全な非同期サポートを提供し、マルチタスク並列処理が可能なサービスインターフェースを実現しています。
- ✅ **LAN、複数人利用をサポート**：LAN内での複数人による同時利用をサポートします。
- ✅ **インタラクティブなWeb UI**：すぐに使えるWeb UIとRESTful APIを提供し、統合や利用が容易です。
- ✅ **小容量・マルチプラットフォーム対応の簡単パッケージ**：40MB未満のWindows、Mac用簡単パッケージ（`docling`
  によるローカルPDF解析を使用しないバージョン）。

> `pdf`を翻訳する際、一度Markdownに変換されるため、元のレイアウトが**失われます**。レイアウトを重視するユーザーはご注意ください。

> QQ交流グループ：1047781902

**UI画面**：
![翻訳効果](/images/UI界面.png)

**論文翻訳**：
![翻訳効果](/images/論文翻訳.png)

**小説翻訳**：
![翻訳効果](/images/小説翻訳.png)

## 統合パッケージ

すぐに使い始めたいユーザーのために、[GitHub Releases](https://github.com/xunbu/docutranslate/releases)
で統合パッケージを提供しています。ダウンロードして解凍し、お使いのAIプラットフォームのAPIキーを入力するだけで使用を開始できます。

- **DocuTranslate**: 標準版。オンラインの`minerU`エンジンを使用してPDFドキュメントを解析します。ローカルでのPDF解析が不要な場合はこちらを選択してください（推奨）。
- **DocuTranslate_full**: 完全版。`docling`ローカルPDF解析エンジンを内蔵しています。ローカルでのPDF解析が必要な場合はこちらを選択してください。

## インストール

### pipを使用

```bash
# 基本インストール
pip install docutranslate

# doclingでローカルPDF解析を使用する場合
pip install docutranslate[docling]
```

### uvを使用

```bash
# 環境の初期化
uv init

# 基本インストール
uv add docutranslate

# docling拡張機能のインストール
uv add docutranslate[docling]
```

### gitを使用

```bash
# 環境の初期化
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

## 中心的な概念：ワークフロー (Workflow)

新バージョンのDocuTranslateの核心は**ワークフロー (Workflow)**
です。各ワークフローは、特定のファイルタイプ専用に設計された、完全なエンドツーエンドの翻訳パイプラインです。もはや巨大なクラスと対話するのではなく、ファイルタイプに応じて適切なワークフローを選択し、設定します。

**基本的な使用手順は以下の通りです：**

1. **ワークフローの選択**：入力ファイルの種類（例：PDF/WordまたはTXT）に応じて、`MarkdownBasedWorkflow`や`TXTWorkflow`
   などのワークフローを選択します。
2. **設定の構築**：選択したワークフローに対応する設定オブジェクト（例：`MarkdownBasedWorkflowConfig`
   ）を作成します。この設定オブジェクトには、必要なすべてのサブ設定が含まれています。
    * **コンバータ設定 (Converter Config)**: 元のファイル（例：PDF）をMarkdownに変換する方法を定義します。
    * **翻訳機設定 (Translator Config)**: 使用するLLM、APIキー、ターゲット言語などを定義します。
    * **エクスポータ設定 (Exporter Config)**: 出力フォーマット（例：HTML）の特定のオプションを定義します。
3. **ワークフローのインスタンス化**：設定オブジェクトを使用してワークフローのインスタンスを作成します。
4. **翻訳の実行**：ワークフローの`.read_*()`および`.translate()` / `.translate_async()`メソッドを呼び出します。
5. **結果のエクスポート/保存**：`.export_to_*()`または`.save_as_*()`メソッドを呼び出して、翻訳結果を取得または保存します。

## 利用可能なワークフロー

| ワークフロー                      | 適用シーン                                                                  | 入力フォーマット                                  | 出力フォーマット               | 主要設定クラス                       |
|:----------------------------|:-----------------------------------------------------------------------|:------------------------------------------|:-----------------------|:------------------------------|
| **`MarkdownBasedWorkflow`** | PDF、Word、画像などのリッチテキストドキュメントを処理。フロー：`ファイル -> Markdown -> 翻訳 -> エクスポート`。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` など | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | プレーンテキストドキュメントを処理。フロー：`txt -> 翻訳 -> エクスポート`。                           | `.txt` およびその他のプレーンテキスト形式                  | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | JSONファイルを処理。フロー：`json -> 翻訳 -> エクスポート`。                                | `.json`                                   | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | DOCXファイルを処理。フロー：`docx -> 翻訳 -> エクスポート`。                                | `.docx`                                   | `.docx`, `.html`       | `docxWorkflowConfig`          |
| **`XlsxWorkflow`**          | XLSXファイルを処理。フロー：`xlsx -> 翻訳 -> エクスポート`。                                | `.xlsx`、`.csv`                            | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | SRTファイルを処理。フロー：`srt -> 翻訳 -> エクスポート`。                                  | `.srt`                                    | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**          | EPUBファイルを処理。フロー：`epub -> 翻訳 -> エクスポート`。                                | `.epub`                                   | `.epub`, `.html`       | `EpubWorkflowConfig`          |
| **`HtmlWorkflow`**          | HTMLファイルを処理。フロー：`html -> 翻訳 -> エクスポート`。                                | `.html`, `.htm`                           | `.html`                | `HtmlWorkflowConfig`          |

> インタラクティブUIではPDF形式でのエクスポートが可能です

## Web UIとAPIサービスの起動

DocuTranslateは、使いやすさを考慮して、フル機能のWebインターフェースとRESTful APIを提供しています。

**サービスの起動:**

```bash
# サービスを起動、デフォルトはポート8010でリッスンします
docutranslate -i

# ポートを指定して起動
docutranslate -i -p 8011

# 環境変数でポートを指定することも可能です
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **インタラクティブUI**: サービス起動後、ブラウザで `http://127.0.0.1:8010` (または指定したポート) にアクセスしてください。
- **APIドキュメント**: 完全なAPIドキュメント (Swagger UI) は `http://127.0.0.1:8010/docs` にあります。

## 使用方法

### 例1: PDFファイルの翻訳 (`MarkdownBasedWorkflow`を使用)

これは最も一般的な使用例です。`minerU`エンジンを使用してPDFをMarkdownに変換し、LLMで翻訳します。ここでは非同期方式を例にとります。

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AIプラットフォームのBase URL
        api_key="YOUR_ZHIPU_API_KEY",  # AIプラットフォームのAPIキー
        model_id="glm-4-air",  # モデルID
        to_lang="English",  # ターゲット言語
        chunk_size=3000,  # テキストのチャンクサイズ
        concurrent=10,  # 並列処理数
        # glossary_generate_enable=True, # 用語集の自動生成を有効化
        # glossary_dict={"Jobs":"ジョブズ"} # 用語集を渡す
    )

    # 2. コンバータの設定を構築 (minerUを使用)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # あなたのminerUトークン
        formula_ocr=True  # 数式認識を有効化
    )

    # 3. メインワークフローの設定を構築
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 解析エンジンを指定
        converter_config=converter_config,  # コンバータ設定を渡す
        translator_config=translator_config,  # 翻訳機設定を渡す
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTMLエクスポート設定
    )

    # 4. ワークフローをインスタンス化
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. ファイルを読み込み、翻訳を実行
    print("ファイルの読み込みと翻訳を開始...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # または同期的な方法を使用
    # workflow.translate()
    print("翻訳完了！")

    # 6. 結果を保存
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 画像が埋め込まれたMarkdown
    print("ファイルは ./output フォルダに保存されました。")

    # または直接コンテンツ文字列を取得
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### 例2: TXTファイルの翻訳 (`TXTWorkflow`を使用)

プレーンテキストファイルの場合、ドキュメント解析（変換）ステップが不要なため、プロセスはよりシンプルになります。ここでは非同期方式を例にとります。

```python
import asyncio
from docutranslate.workflow.txt_workflow import TXTWorkflow, TXTWorkflowConfig
from docutranslate.translator.ai_translator.txt_translator import TXTTranslatorConfig
from docutranslate.exporter.txt.txt2html_exporter import TXT2HTMLExporterConfig


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = TXTTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
    )

    # 2. メインワークフローの設定を構築
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
    print("TXTファイルが保存されました。")

    # 翻訳後のプレーンテキストをエクスポートすることも可能
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例3: JSONファイルの翻訳 (`JsonWorkflow`を使用)

ここでは非同期方式を例にとります。`JsonTranslatorConfig`の`json_paths`項目で翻訳対象のJSONパスを指定する必要があります（
`jsonpath-ng`構文仕様に準拠）。JSONパスにマッチした値のみが翻訳されます。

```python
import asyncio

from docutranslate.exporter.js.json2html_exporter import Json2HTMLExporterConfig
from docutranslate.translator.ai_translator.json_translator import JsonTranslatorConfig
from docutranslate.workflow.json_workflow import JsonWorkflowConfig, JsonWorkflow


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = JsonTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        json_paths=["$.*", "$.name"]  # `jsonpath-ng`のパス構文に準拠し、マッチしたパスの値がすべて翻訳されます
    )

    # 2. メインワークフローの設定を構築
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
    print("JSONファイルが保存されました。")

    # 翻訳後のJSONテキストをエクスポートすることも可能
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例4: DOCXファイルの翻訳 (`DocxWorkflow`を使用)

ここでは非同期方式を例にとります。

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # 選択肢: "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用する区切り文字
    )

    # 2. メインワークフローの設定を構築
    workflow_config = DocxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Docx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = DocxWorkflow(config=workflow_config)

    # 4. ファイルを読み込み、翻訳を実行
    workflow.read_path("path/to/your/notes.docx")
    await workflow.translate_async()
    # または同期的な方法を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_docx(name="translated_notes.docx")
    print("DOCXファイルが保存されました。")

    # 翻訳後のDOCXのバイナリをエクスポートすることも可能
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例5: XLSXファイルの翻訳 (`XlsxWorkflow`を使用)

ここでは非同期方式を例にとります。

```python
import asyncio

from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. 翻訳機の設定を構築
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # 選択肢: "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用する区切り文字
    )

    # 2. メインワークフローの設定を構築
    workflow_config = XlsxWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Xlsx2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = XlsxWorkflow(config=workflow_config)

    # 4. ファイルを読み込み、翻訳を実行
    workflow.read_path("path/to/your/notes.xlsx")
    await workflow.translate_async()
    # または同期的な方法を使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("XLSXファイルが保存されました。")

    # 翻訳後のXLSXのバイナリをエクスポートすることも可能
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

## 前提条件と設定詳細

### 1. 大規模言語モデルのAPIキーを取得

翻訳機能は大規模言語モデルに依存しているため、対応するAIプラットフォームから`base_url`、`api_key`、`model_id`を取得する必要があります。

> 推奨モデル：火山引擎の`doubao-seed-1-6-250615`、`doubao-seed-1-6-flash-250715`、智谱の`glm-4-flash`、阿里云の`qwen-plus`、
`qwen-turbo`、deepseekの`
> deepseek-chat`など。

| プラットフォーム名  | APIキーの取得                                                                                  | baseurl                                                  |
|:-----------|:------------------------------------------------------------------------------------------|:---------------------------------------------------------|
| ollama     |                                                                                           | http://127.0.0.1:11434/v1                                |
| lm studio  |                                                                                           | http://127.0.0.1:1234/v1                                 |
| openrouter | [クリックして取得](https://openrouter.ai/settings/keys)                                           | https://openrouter.ai/api/v1                             |
| openai     | [クリックして取得](https://platform.openai.com/api-keys)                                          | https://api.openai.com/v1/                               |
| gemini     | [クリックして取得](https://aistudio.google.com/u/0/apikey)                                        | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek   | [クリックして取得](https://platform.deepseek.com/api_keys)                                        | https://api.deepseek.com/v1                              |
| 智谱ai       | [クリックして取得](https://open.bigmodel.cn/usercenter/apikeys)                                   | https://open.bigmodel.cn/api/paas/v4                     |
| 腾讯混元       | [クリックして取得](https://console.cloud.tencent.com/hunyuan/api-key)                             | https://api.hunyuan.cloud.tencent.com/v1                 |
| 阿里云百炼      | [クリックして取得](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| 火山引擎       | [クリックして取得](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| 硅基流动       | [クリックして取得](https://cloud.siliconflow.cn/account/ak)                                       | https://api.siliconflow.cn/v1                            |
| DMXAPI     | [クリックして取得](https://www.dmxapi.cn/token)                                                   | https://www.dmxapi.cn/v1                                 |

### 2. PDF解析エンジン（PDF翻訳が不要な場合は気にする必要はありません）

### 2.1 minerUトークンの取得 (オンラインPDF解析、無料、推奨)

ドキュメント解析エンジンとして`mineru`を選択した場合（`convert_engine="mineru"`）、無料のトークンを申請する必要があります。

1. [minerU公式サイト](https://mineru.net/apiManage/docs) にアクセスして登録し、APIを申請します。
2. [APIトークン管理画面](https://mineru.net/apiManage/token) で新しいAPIトークンを作成します。

> **注意**: minerUトークンには14日間の有効期限があります。期限が切れた場合は再作成してください。

### 2.2. doclingエンジンの設定 (ローカルPDF解析)

ドキュメント解析エンジンとして`docling`を選択した場合（`convert_engine="docling"`）、初回使用時にHugging
Faceから必要なモデルがダウンロードされます。

> より良い選択肢は、[github releases](https://github.com/xunbu/docutranslate/releases)から`docling_artifact.zip`
> をダウンロードし、作業ディレクトリに展開することです。

**`docling`モデルのダウンロードに関するネットワーク問題の解決策:**

1. **Hugging Faceミラーの設定 (推奨)**:

* **方法 A (環境変数)**: システム環境変数 `HF_ENDPOINT` を設定し、IDEまたはターミナルを再起動します。
  ```
  HF_ENDPOINT=https://hf-mirror.com
  ```
* **方法 B (コード内での設定)**: Pythonスクリプトの先頭に以下のコードを追加します。

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **オフラインでの使用 (事前にモデルパッケージをダウンロード)**:

* [GitHub Releases](https://github.com/xunbu/docutranslate/releases) から `docling_artifact.zip` をダウンロードします。
* プロジェクトディレクトリに展開します。
* 設定でモデルのパスを指定します（モデルがスクリプトと同じディレクトリにない場合）：

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # 展開後のフォルダを指す
    code_ocr=True,
    formula_ocr=True
)
```

## FAQ

**Q: ポート8010が使用中の場合はどうすればよいですか？**
A: `-p` パラメータを使用して新しいポートを指定するか、`DOCUTRANSLATE_PORT` 環境変数を設定してください。

**Q: スキャンされたPDFの翻訳はサポートしていますか？**
A: はい、サポートしています。強力なOCR機能を持つ`mineru`解析エンジンを使用してください。

**Q: 初回のPDF翻訳が非常に遅いのはなぜですか？**
A: `docling`エンジンを使用している場合、初回実行時にHugging
Faceからモデルをダウンロードする必要があります。このプロセスを高速化するには、上記の「ネットワーク問題の解決策」を参照してください。

**Q: LAN（オフライン）環境で使用するにはどうすればよいですか？**
A: 完全に可能です。以下の条件を満たす必要があります：

1. **ローカルLLM**: [Ollama](https://ollama.com/) や [LM Studio](https://lmstudio.ai/) などのツールを使用して言語モデルをローカルにデプロイし、
   `TranslatorConfig`にローカルモデルの`base_url`を記入します。
2. **ローカルPDF解析エンジン**（PDF解析が必要な場合のみ）: `docling`エンジンを使用し、上記の「オフラインでの使用」の指示に従って事前にモデルパッケージをダウンロードします。

**Q: PDF解析のキャッシュメカニズムはどのように機能しますか？**
A: `MarkdownBasedWorkflow`
は、ドキュメント解析（ファイルからMarkdownへの変換）の結果を自動的にキャッシュし、時間とリソースの重複消費を防ぎます。キャッシュはデフォルトでメモリに保存され、直近10回の解析結果が記録されます。キャッシュ数は
`DOCUTRANSLATE_CACHE_NUM`環境変数で変更できます。

**Q: ソフトウェアがプロキシ経由で通信するようにするにはどうすればよいですか？**
A: デフォルトではプロキシを使用しません。環境変数`DOCUTRANSLATE_PROXY_ENABLED`を`true`に設定することで、プロキシ経由での通信が可能になります。

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>

## 応援サポート

作者へのサポートを歓迎します。備考欄に応援の理由を記載していただけると幸いです。

<p align="center">
  <img src="./images/赞赏码.jpg" alt="赞赏码" style="width: 50vw;max-width: 300px"></p>