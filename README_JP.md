<center>
  <img src="./DocuTranslate.png" alt="プロジェクトロゴ" style="width: 150px">
</center>

# DocuTranslate

[![GitHub stars](https://img.shields.io/github/stars/xunbu/docutranslate?style=flats&logo=github&color=blue)](https://github.com/xunbu/docutranslate)
[![github下载数](https://img.shields.io/github/downloads/xunbu/docutranslate/total?logo=github)](https://github.com/xunbu/docutranslate/releases)
[![PyPI version](https://img.shields.io/pypi/v/docutranslate)](https://pypi.org/project/docutranslate/)
[![python版本](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![开源协议](https://img.shields.io/github/license/xunbu/docutranslate)](./LICENSE)

[**简体中文**](/README_ZH.md) / [**English**](/README.md) / [**日本語**](/README_JP.md)

**DocuTranslate** はファイル翻訳ツールで、[docling](https://github.com/docling-project/docling)や[minerU](https://mineru.net/)などの最先端の文書解析エンジンと大型言語モデル(LLM)を組み合わせ、さまざまな形式の文書を正確に翻訳します。

新しいバージョンのアーキテクチャは **ワークフロー(Workflow)** をコアとし、さまざまな種類の翻訳タスクに高いカスタマイズ性と拡張性を提供するソリューションを実現しています。

- ✅ **多形式ファイル対応**: `pdf`、`docx`、`xlsx`、`md`、`txt`、`json`、`epub`、`srt`など様々なファイル形式の翻訳が可能です。
- ✅ **表・数式・コード認識**: `docling`および`mineru`を活用し、学術論文で頻出する表、数式、コードの認識と翻訳を実現。
- ✅ **用語集の自動作成**: 用語の統一を実現するための用語集自動作成機能をサポート。
- ✅ **JSON翻訳**: JSONPath（`jsonpath-ng`構文規格）を用いて翻訳対象の値を指定可能。
- ✅ **Word/Excel高精度翻訳**: `docx`、`xlsx`ファイル（現在`doc`、`xls`ファイルは非対応）の元の書式を保持した翻訳をサポート。
- ✅ **複数AIプラットフォーム対応**: 主要なAIプラットフォームのほとんどに対応し、カスタムプロンプトを用いた高並列パフォーマンスAI翻訳を実現。
- ✅ **非同期処理対応**: 高性能シナリオ向けに設計された非同期処理を完全サポート。並列処理可能なサービスインターフェースを実装。
- ✅ **対話型Webインターフェース**: すぐに利用可能なWeb UIとRESTful APIを提供し、容易な統合と使用を実現。

> `pdf`や`html`などのファイルを翻訳する場合、まずmarkdownに変換されます。このため、元のレイアウトが**失われる可能性があります**。レイアウトに厳しい要件があるユーザーはご注意ください。

> QQ交流グループ：1047781902

**UIインターフェース**：
![翻译效果](/images/UI界面.png)

**論文翻訳**：
![翻译效果](/images/论文翻译.png)

**小説翻訳**：
![翻译效果](/images/小说翻译.png)

## 統合パッケージ

早速使い始めたいユーザーのために、GitHub Releases(https://github.com/xunbu/docutranslate/releases)に統合パッケージを提供しています。ダウンロードして解凍し、AIプラットフォームのAPI-Keyを入力するだけで使用を開始できます。

- **DocuTranslate**：標準版で、オンラインの`minerU`エンジンを使用して文書を解析し、ほとんどのユーザーにおすすめします。
- **DocuTranslate_full**：完全版で、ローカルの`docling`解析エンジンを組み込み、オフライン使用やデータプライバシーに高い要件があるシーンをサポートします。

## インストール

### pipを使う

```bash
# ベースインストール
pip install docutranslate

# doclingローカル解析エンジンを使用する場合
pip install docutranslate[docling]
```

### uvを使う

```bash
# 環境を初期化
uv init

# ベースインストール
uv add docutranslate

# docling拡張をインストール
uv add docutranslate[docling]
```

### gitを使う

```bash
# 環境を初期化
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

## コアコンセプト：ワークフロー (Workflow)

新しいDocuTranslateのコアは**ワークフロー (Workflow)** です。各ワークフローは、特定のファイルタイプ向けに設計された完全なエンドツーエンド翻訳パイプラインです。あなたはもはや巨大なクラスと対話するのではなく、ファイルタイプに基づいて適切なワークフローを選択して設定します。

**基本的な使用フローは以下の通りです：**

1. **ワークフローを選択**：入力ファイルタイプ（例：PDF/Word または TXT）に基づいて、`MarkdownBasedWorkflow` や `TXTWorkflow` などのワークフローを選択します。
2. **設定を構築**：選択したワークフローに対応する設定オブジェクト（例：`MarkdownBasedWorkflowConfig`）を作成します。この設定オブジェクトには、すべての必要なサブ設定が含まれています。例えば：
    * **コンバーター設定 (Converter Config)**：元のファイル（例：PDF）を Markdown に変換する方法を定義します。
    * **翻訳機設定 (Translator Config)**：使用する LLM、API-Key、ターゲット言語などを定義します。
    * **エクスポーター設定 (Exporter Config)**：出力フォーマット（例：HTML）の特定のオプションを定義します。
3. **ワークフローのインスタンス化**：設定オブジェクトを使用してワークフローのインスタンスを作成します。
4. **翻訳を実行**：ワークフローの `.read_*()` および `.translate()` / `.translate_async()` メソッドを呼び出します。
5. **結果のエクスポート/保存**：`.export_to_*()` または `.save_as_*()` メソッドを呼び出して、翻訳結果を取得または保存します。

## 利用可能なワークフロー

| ワークフロー                     | 適用シーン                                                  | 入力フォーマット                                 | 出力フォーマット               | コア設定クラス                   |
|:------------------------------|:-------------------------------------------------------|:--------------------------------------------|:--------------------------|:----------------------------|
| **`MarkdownBasedWorkflow`**   | リッチドキュメントを処理します。例えば、PDF、Word、画像など。フローは次の通り：`ファイル -> Markdown -> 翻訳 -> エクスポート`。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` など | `.md`, `.zip`, `.html`   | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**             | テキストファイルを処理します。フローは次の通り：`txt -> 翻訳 -> エクスポート`。               | `.txt` 及びその他のテキスト形式                      | `.txt`, `.html`          | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**            | JSONファイルを処理します。フローは次の通り：`json -> 翻訳 -> エクスポート`。                 | `.json`                                    | `.json`, `.html`         | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**            | DOCXファイルを処理します。フローは次の通り：`docx -> 翻訳 -> エクスポート`。                 | `.docx`                                    | `.docx`, `.html`         | `docxWorkflowConfig`          |
| **`XlsxWorkflow`**            | XLSXファイルを処理します。フローは次の通り：`xlsx -> 翻訳 -> エクスポート`。                 | `.xlsx`                                    | `.xlsx`, `.html`         | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**             | SRTファイルを処理します。フローは次の通り：`srt -> 翻訳 -> エクスポート`。                   | `.srt`                                     | `.srt`, `.html`          | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**            | EPUBファイルを処理します。フローは次の通り：`epub -> 翻訳 -> エクスポート`。                 | `.epub`                                    | `.epub`, `.html`         | `EpubWorkflowConfig`          |

> インタラクティブなインターフェースではPDF形式にエクスポートできます

## Web UI と API サービスの起動

使いやすさのために、DocuTranslateには機能豊富なWebインターフェースとRESTful APIが用意されています。

**サービスの起動:**

```bash
# サービスを起動します。デフォルトでポート8010をリッスンします
docutranslate -i

# ポートを指定して起動
docutranslate -i -p 8011

# 環境変数でポートを指定することもできます
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **対話型インターフェース**: サービスを起動後、ブラウザで `http://127.0.0.1:8010` (または指定したポート) にアクセスしてください。
- **APIドキュメント**: 完全なAPIドキュメント（Swagger UI）は `http://127.0.0.1:8010/docs` にあります。

## 使用方法

### 例 1: PDFファイルを翻訳する ( `MarkdownBasedWorkflow` を使用)

最も一般的なユースケースです。`minerU` エンジンを使用してPDFをMarkdownに変換し、次にLLMを使用して翻訳します。ここでは非同期を例にとります。

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 翻訳設定を構築
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AI プラットフォームのベース URL
        api_key="YOUR_ZHIPU_API_KEY",  # AI プラットフォームの API キー
        model_id="glm-4-air",  # モデル ID
        to_lang="English",  # 対象言語
        chunk_size=3000,  # テキストのチャンクサイズ
        concurrent=10  # 同時実行数
    )

    # 2. コンバーター設定を構築 (minerU を使用)
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # あなたの minerU トークン
        formula_ocr=True  # 数式認識を有効化
    )

    # 3. メインワークフロー設定を構築
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 解析エンジンを指定
        converter_config=converter_config,  # コンバーター設定を渡す
        translator_config=translator_config,  # 翻訳設定を渡す
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTML エクスポート設定
    )

    # 4. ワークフローをインスタンス化
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. ファイルを読み込み翻訳を実行
    print("ファイルの読み込みと翻訳を開始します...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()
    print("翻訳が完了しました！")

    # 6. 結果を保存
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 画像埋め込みのマークダウン
    print("ファイルが ./output フォルダに保存されました。")

    # または直接コンテンツ文字列を取得
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### 例 2: TXT ファイルの翻訳（`TXTWorkflow` を使用）

プレーンテキストファイルのフローはよりシンプルです。ドキュメント解析（変換）ステップが不要だからです。以下は非同期方式の例です。

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

    # 4. ファイルを読み込み翻訳を実行
    workflow.read_path("path/to/your/notes.txt")
    await workflow.translate_async()
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXTファイルが保存されました。")

    # 翻訳されたプレーンテキストをエクスポートすることも可能
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例3：JSONファイルを翻訳する（`JsonWorkflow`を使用）

ここでは非同期方式を例に示します。JsonTranslatorConfigのjson_paths項目には、翻訳するJSONパス（jsonpath-ng構文規準に準拠）を指定する必要があり、JSONパスに一致する値のみが翻訳されます。

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
        json_paths=["$.*", "$.name"]  # jsonpath-ngパス構文に準拠、一致するパスの値がすべて翻訳される
    )

    # 2. メインワークフロー設定を構築
    workflow_config = JsonWorkflowConfig(
        translator_config=translator_config,
        html_exporter_config=Json2HTMLExporterConfig(cdn=True)
    )

    # 3. ワークフローをインスタンス化
    workflow = JsonWorkflow(config=workflow_config)

    # 4. ファイルを読み込み翻訳を実行
    workflow.read_path("path/to/your/notes.json")
    await workflow.translate_async()
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_json(name="translated_notes.json")
    print("jsonファイルが保存されました。")

    # 翻訳されたJSONテキストをエクスポートすることも可能
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例4：DOCXファイルを翻訳する（`DocxWorkflow`を使用）

ここでは非同期方式を例に説明します。

```python
import asyncio

from docutranslate.exporter.docx.docx2html_exporter import Docx2HTMLExporterConfig
from docutranslate.translator.ai_translator.docx_translator import DocxTranslatorConfig
from docutranslate.workflow.docx_workflow import DocxWorkflowConfig, DocxWorkflow


async def main():
    # 1. 翻訳器の設定を構築
    translator_config = DocxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # 代替オプション "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用される区切り文字
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
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_docx(name="translated_notes.docx")
    print("docxファイルが保存されました。")

    # 翻訳後のdocxのバイナリをエクスポートすることも可能
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例 5: xlsxファイルの翻訳（`XlsxWorkflow`を使用）

ここでは非同期方式を例に説明します。

```python
import asyncio

from docutranslate.exporter.xlsx.xlsx2html_exporter import Xlsx2HTMLExporterConfig
from docutranslate.translator.ai_translator.xlsx_translator import XlsxTranslatorConfig
from docutranslate.workflow.xlsx_workflow import XlsxWorkflowConfig, XlsxWorkflow


async def main():
    # 1. 翻訳器の設定を構築
    translator_config = XlsxTranslatorConfig(
        base_url="https://api.openai.com/v1/",
        api_key="YOUR_OPENAI_API_KEY",
        model_id="gpt-4o",
        to_lang="日本語",
        insert_mode="replace",  # 代替オプション "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用される区切り文字
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
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_xlsx(name="translated_notes.xlsx")
    print("xlsxファイルが保存されました。")

    # 翻訳後のxlsxのバイナリをエクスポートすることも可能
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

## 前提条件と設定の詳細

### 1. 大規模言語モデルのAPIキーの取得

翻訳機能は大型言語モデルに依存しており、`base_url`、`api_key`、`model_id`を取得するためには、対応するAIプラットフォームから必要な情報を入手する必要があります。

> 推奨モデル：火山エンジンの`doubao-seed-1-6-flash-250715`、智譜の`glm-4-flash`、阿里雲の `qwen-plus`,``qwen-turbo`、deepseekの`deepseek-chat`など。

| プラットフォーム名       | APIkeyを取得                                                                              | baseurl                                                  |
|------------|---------------------------------------------------------------------------------------|----------------------------------------------------------|
| ollama     |                                                                                       | http://127.0.0.1:11434/v1                                |
| lm studio  |                                                                                       | http://127.0.0.1:1234/v1                                 |
| openrouter | [取得](https://openrouter.ai/settings/keys)                                           | https://openrouter.ai/api/v1                             |
| openai     | [取得](https://platform.openai.com/api-keys)                                          | https://api.openai.com/v1/                               |
| gemini     | [取得](https://aistudio.google.com/u/0/apikey)                                        | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek   | [取得](https://platform.deepseek.com/api_keys)                                        | https://api.deepseek.com/v1                              |
| 智譜ai       | [取得](https://open.bigmodel.cn/usercenter/apikeys)                                   | https://open.bigmodel.cn/api/paas/v4                     |
| 騰訊混元       | [取得](https://console.cloud.tencent.com/hunyuan/api-key)                             | https://api.hunyuan.cloud.tencent.com/v1                 |
| 阿里雲百錬      | [取得](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| 火山エンジン       | [取得](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| 硅基流動       | [取得](https://cloud.siliconflow.cn/account/ak)                                       | https://api.siliconflow.cn/v1                            |
| DMXAPI     | [取得](https://www.dmxapi.cn/token)                                                   | https://www.dmxapi.cn/v1                                 |

### 2. minerU Tokenを取得（オンライン解析）

`mineru`を文書解析エンジンとして選択した場合（`convert_engine="mineru"`）、無料のTokenを申請する必要があります。

1. [minerUの公式ウェブサイト](https://mineru.net/apiManage/docs)にアクセスして登録し、APIを申請します。
2. [API Token管理インターフェース](https://mineru.net/apiManage/token)で新しいAPI Tokenを作成します。

> **注意**: minerU Tokenは14日間有効期限があり、期限が切れた場合は再度作成してください。

### 3. doclingエンジンの設定（ローカル解析）

`docling`を文書解析エンジンとして選択した場合（`convert_engine="docling"`）、初回使用時にHugging Faceから必要なモデルがダウンロードされます。

**ネットワークの問題解決策:**

1. **Hugging Faceミラーの設定（推奨）:**

* **方法A（環境変数）:** システム環境変数`HF_ENDPOINT`を設定し、IDEまたはターミナルを再起動します。
   ```
   HF_ENDPOINT=https://hf-mirror.com
   ```
* **方法B（コード内で設定）:** Pythonスクリプトの先頭に以下のコードを追加します。

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **オフライン使用（事前にモデルパッケージをダウンロード）:**

* [GitHub Releases](https://github.com/xunbu/docutranslate/releases)から`docling_artifact.zip`をダウンロードします。
* プロジェクトディレクトリに解凍します。
* 設定でモデルパスを指定します：

```python
from docutranslate.converter.x2md.converter_docling import ConverterDoclingConfig

converter_config = ConverterDoclingConfig(
    artifact="./docling_artifact",  # 解凍したフォルダーを指定
    code_ocr=True,
    formula_ocr=True
)
```

## FAQ

**Q: 8010ポートが使用中の場合はどうすればよいですか？**
A: `-p`パラメータを使用して新しいポートを指定するか、`DOCUTRANSLATE_PORT`環境変数を設定します。

**Q: スキャンした文書の翻訳をサポートしていますか？**
A: サポートしています。`mineru`解析エンジンを使用してください。強力なOCR機能を持っています。

**Q: 初めて使用するとなぜ遅いですか？**
A: `docling`エンジンを使用している場合は、初回実行時にHugging Faceからモデルをダウンロードする必要があります。上記の「ネットワークの問題解決策」を参照して、プロセスを高速化してください。

**Q: 内部ネットワーク（オフライン）環境で使用する方法は？**
A: 完全に可能です。2つの条件を満たす必要があります：

1. **ローカル解析エンジン:** `docling` エンジンを使用し、上記の「オフライン使用」の手順に従って事前にモデルパッケージをダウンロードします。
2. **ローカル LLM:** [Ollama](https://ollama.com/) または [LM Studio](https://lmstudio.ai/) などのツールを使用して言語モデルをローカルにデプロイし、`TranslatorConfig` でローカルモデルの `base_url` を入力します。

**Q: キャッシュメカニズムはどのように動作しますか？**
A: `MarkdownBasedWorkflow` は、文書解析（ファイルから Markdown への変換）の結果を自動的にキャッシュし、重複する解析による時間とリソースの消費を防ぎます。キャッシュはデフォルトでメモリに保存され、最近の10回の解析が記録されます。キャッシュ数を変更するには `DOCUTRANSLATE_CACHE_NUM` 環境変数を使用できます。

## Star History

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>