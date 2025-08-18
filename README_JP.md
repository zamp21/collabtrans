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

**DocuTranslate** は、先進的なドキュメント解析エンジン（[docling](https://github.com/docling-project/docling)
や[minerU](https://mineru.net/)など）と大規模言語モデル（LLM）を組み合わせたファイル翻訳ツールで、多様なフォーマットのドキュメントを高精度に翻訳します。

新バージョンでは、**ワークフロー(Workflow)**を中核としたアーキテクチャを採用し、様々なタイプの翻訳タスクに対して高度に設定可能で拡張性の高いソリューションを提供します。

- ✅ **多様なフォーマット対応**: `pdf`, `docx`, `xlsx`, `md`, `txt`, `json`, `epub`, `srt` など様々なファイル形式の翻訳が可能
- ✅ **表・数式・コード認識**: `docling` と `mineru` を活用し、学術論文で頻出する表、数式、コードの認識と翻訳を実現
- ✅ **json翻訳**: json内の翻訳対象値をjsonpath-ng構文で指定可能
- ✅ **Word/Excel高忠実度翻訳**: `docx`、`xlsx`ファイル（`doc`、`xls`は非対応）のフォーマットを保持した翻訳
- ✅ **複数AIプラットフォーム対応**: 主要なAIプラットフォームを網羅し、カスタムプロンプトを用いた高並列AI翻訳を実現
- ✅ **非同期サポート**: 高性能シナリオ向けに設計され、完全な非同期サポートとマルチタスク並列処理APIを提供
- ✅ **対話型Webインターフェース**: すぐに使えるWeb UIとRESTful APIを装備

> `pdf`翻訳時はmarkdownに変換されるため、**元のレイアウトが失われます**。レイアウト保持を重視される方はご注意ください

> QQ交流グループ: 1047781902

**UIインターフェース**:
![翻译效果](/images/UI界面.png)

**論文翻訳**:
![翻译效果](/images/论文翻译.png)

**小説翻訳**:
![翻译效果](/images/小说翻译.png)

## バンドル版

すぐに使い始めたい方向けに、[GitHub Releases](https://github.com/xunbu/docutranslate/releases)
でバンドル版を提供しています。ダウンロードして解凍し、AIプラットフォームのAPIキーを入力するだけで利用可能です。

- **DocuTranslate**: 標準版、オンラインの`minerU`エンジンを使用
- **DocuTranslate_full**: 完全版、ローカル`docling`解析エンジンを内蔵、オフライン環境やデータプライバシー重視の場面に最適

## インストール

### pipを使用

```bash
# 基本インストール
pip install docutranslate

# doclingローカル解析エンジンを使用する場合
pip install docutranslate[docling]
```

### uvを使用

```bash
# 環境初期化
uv init

# 基本インストール
uv add docutranslate

# docling拡張インストール
uv add docutranslate[docling]
```

### gitを使用

```bash
# 環境初期化
git clone https://github.com/xunbu/docutranslate.git

cd docutranslate

uv sync

```

## コアコンセプト：ワークフロー (Workflow)

新バージョンのDocuTranslateの中核は**ワークフロー (Workflow)**
です。各ワークフローは、特定のファイルタイプ向けに設計された完全なエンドツーエンドの翻訳パイプラインです。巨大なクラスとやり取りする代わりに、ファイルタイプに応じて適切なワークフローを選択・設定します。

**基本的な使用手順は以下の通りです：**

1. **ワークフローの選択**：入力ファイルのタイプ（例：PDF/WordまたはTXT）に基づき、`MarkdownBasedWorkflow`や`TXTWorkflow`
   などのワークフローを選択します。
2. **設定の構築**：選択したワークフローに対応する設定オブジェクト（例：`MarkdownBasedWorkflowConfig`
   ）を作成します。この設定オブジェクトには、以下のようなすべての必要なサブ設定が含まれます：
    * **コンバーター設定 (Converter Config)**: 元のファイル（PDFなど）をMarkdownに変換する方法を定義します。
    * **トランスレーター設定 (Translator Config)**: 使用するLLM、APIキー、ターゲット言語などを定義します。
    * **エクスポーター設定 (Exporter Config)**: 出力形式（HTMLなど）の特定のオプションを定義します。
3. **ワークフローのインスタンス化**：設定オブジェクトを使用してワークフローのインスタンスを作成します。
4. **翻訳の実行**：ワークフローの`.read_*()`および`.translate()` / `.translate_async()`メソッドを呼び出します。
5. **結果のエクスポート/保存**：`.export_to_*()`または`.save_as_*()`メソッドを呼び出して翻訳結果を取得または保存します。

## 利用可能なワークフロー

| ワークフロー                      | 適用シナリオ                                                             | 入力形式                                     | 出力形式                   | コア設定クラス                       |
|:----------------------------|:-------------------------------------------------------------------|:-----------------------------------------|:-----------------------|:------------------------------|
| **`MarkdownBasedWorkflow`** | PDF、Word、画像などのリッチテキストドキュメントを処理。「ファイル → Markdown → 翻訳 → エクスポート」の流れ。 | `.pdf`, `.docx`, `.md`, `.png`, `.jpg` 等 | `.md`, `.zip`, `.html` | `MarkdownBasedWorkflowConfig` |
| **`TXTWorkflow`**           | プレーンテキストドキュメントを処理。「txt → 翻訳 → エクスポート」の流れ。                          | `.txt` およびその他のプレーンテキスト形式                 | `.txt`, `.html`        | `TXTWorkflowConfig`           |
| **`JsonWorkflow`**          | jsonファイルを処理。「json → 翻訳 → エクスポート」の流れ。                               | `.json`                                  | `.json`, `.html`       | `JsonWorkflowConfig`          |
| **`DocxWorkflow`**          | docxファイルを処理。「docx → 翻訳 → エクスポート」の流れ。                               | `.docx`                                  | `.docx`, `.html`       | `docxWorkflowConfig`          |
| **`XlsxWorkflow`**          | xlsxファイルを処理。「xlsx → 翻訳 → エクスポート」の流れ。                               | `.xlsx`                                  | `.xlsx`, `.html`       | `XlsxWorkflowConfig`          |
| **`SrtWorkflow`**           | srtファイルを処理。「srt → 翻訳 → エクスポート」の流れ。                                 | `.srt`                                   | `.srt`, `.html`        | `SrtWorkflowConfig`           |
| **`EpubWorkflow`**          | epubファイルを処理。「epub → 翻訳 → エクスポート」の流れ。                               | `.epub`                                  | `.epub`, `.html`       | `EpubWorkflowConfig`          |
| **`HtmlWorkflow`**          | htmlファイルを処理。「html → 翻訳 → エクスポート」の流れ。                               | `.html`, `.htm`                          | `.html`                | `HtmlWorkflowConfig`          |

> インタラクティブインターフェースではPDF形式でエクスポート可能

## Web UIとAPIサービスの起動

利便性のため、DocuTranslateは機能豊富なWebインターフェースとRESTful APIを提供しています。

**サービスの起動:**

```bash
# サービスを起動（デフォルトポート: 8010）
docutranslate -i

# ポートを指定して起動
docutranslate -i -p 8011

# 環境変数でポートを指定することも可能
export DOCUTRANSLATE_PORT=8011
docutranslate -i
```

- **インタラクティブインターフェース**: サービス起動後、ブラウザで `http://127.0.0.1:8010`（または指定したポート）にアクセスしてください。
- **APIドキュメント**: 完全なAPIドキュメント（Swagger UI）は `http://127.0.0.1:8010/docs` で利用可能です。

## 使用方法

### 例1: PDFファイルの翻訳（`MarkdownBasedWorkflow`を使用）

これは最も一般的なユースケースです。`minerU`エンジンを使用してPDFをMarkdownに変換し、その後LLMで翻訳を行います。ここでは非同期方式を例示します。

```python
import asyncio
from docutranslate.workflow.md_based_workflow import MarkdownBasedWorkflow, MarkdownBasedWorkflowConfig
from docutranslate.converter.x2md.converter_mineru import ConverterMineruConfig
from docutranslate.translator.ai_translator.md_translator import MDTranslatorConfig
from docutranslate.exporter.md.md2html_exporter import MD2HTMLExporterConfig


async def main():
    # 1. 翻訳機設定の構築
    translator_config = MDTranslatorConfig(
        base_url="https://open.bigmodel.cn/api/paas/v4",  # AIプラットフォームのBase URL
        api_key="YOUR_ZHIPU_API_KEY",  # AIプラットフォームのAPI Key
        model_id="glm-4-air",  # モデルID
        to_lang="English",  # ターゲット言語
        chunk_size=3000,  # テキストチャンクサイズ
        concurrent=10  # 並列処理数
    )

    # 2. コンバーター設定の構築（minerUを使用）
    converter_config = ConverterMineruConfig(
        mineru_token="YOUR_MINERU_TOKEN",  # minerUトークン
        formula_ocr=True  # 数式認識を有効化
    )

    # 3. メインワークフロー設定の構築
    workflow_config = MarkdownBasedWorkflowConfig(
        convert_engine="mineru",  # 解析エンジンの指定
        converter_config=converter_config,  # コンバーター設定の適用
        translator_config=translator_config,  # 翻訳機設定の適用
        html_exporter_config=MD2HTMLExporterConfig(cdn=True)  # HTMLエクスポート設定
    )

    # 4. ワークフローのインスタンス化
    workflow = MarkdownBasedWorkflow(config=workflow_config)

    # 5. ファイルの読み込みと翻訳の実行
    print("ファイルの読み込みと翻訳を開始します...")
    workflow.read_path("path/to/your/document.pdf")
    await workflow.translate_async()
    # または同期方式を使用
    # workflow.translate()
    print("翻訳が完了しました！")

    # 6. 結果の保存
    workflow.save_as_html(name="translated_document.html")
    workflow.save_as_markdown_zip(name="translated_document.zip")
    workflow.save_as_markdown(name="translated_document.md")  # 画像埋め込みMarkdown
    print("ファイルは ./output フォルダに保存されました。")

    # または直接コンテンツ文字列を取得
    html_content = workflow.export_to_html()
    html_content = workflow.export_to_markdown()
    # print(html_content)


if __name__ == "__main__":
    asyncio.run(main())
```

### 例2: TXTファイルの翻訳（`TXTWorkflow`を使用）

プレーンテキストファイルの場合、ドキュメント解析（変換）ステップが不要なため、プロセスがよりシンプルになります。ここでは非同期方式を例示します。

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
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_txt(name="translated_notes.txt")
    print("TXTファイルが保存されました。")

    # 翻訳後のプレーンテキストをエクスポートすることも可能
    text = workflow.export_to_txt()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例3: JSONファイルを翻訳する（`JsonWorkflow`を使用）

ここでは非同期方式を例とします。JsonTranslatorConfigのjson_paths項目は、翻訳するJSONパス（jsonpath-ng構文に準拠）を指定する必要があり、
JSONパスに一致する値のみが翻訳されます。

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
        json_paths=["$.*", "$.name"]  # jsonpath-ngパス構文を満たし、一致するパスの値が翻訳されます
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
    # または同期メソッドを使用
    # workflow.translate()

    # 5. 結果を保存
    workflow.save_as_json(name="translated_notes.json")
    print("jsonファイルが保存されました。")

    # 翻訳後のjsonテキストをエクスポートすることも可能
    text = workflow.export_to_json()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例4: docxファイルを翻訳する（`DocxWorkflow`を使用）

ここでは非同期方式を例とします。

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
        insert_mode="replace",  # オプション "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用するセパレータ
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

    # 翻訳後のdocxをバイナリでエクスポートすることも可能
    text_bytes = workflow.export_to_docx()


if __name__ == "__main__":
    asyncio.run(main())
```

### 例5: xlsxファイルを翻訳する（`XlsxWorkflow`を使用）

ここでは非同期方式を例とします。

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
        insert_mode="replace",  # オプション "replace", "append", "prepend"
        separator="\n",  # "append", "prepend"モードで使用するセパレータ
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

    # 翻訳後のxlsxをバイナリでエクスポートすることも可能
    text_bytes = workflow.export_to_xlsx()


if __name__ == "__main__":
    asyncio.run(main())
```

## 前提条件と設定の詳細説明

### 1. 大規模言語モデルAPIキーの取得

翻訳機能は大規模言語モデルに依存しており、対応するAIプラットフォームから`base_url`、`api_key`、`model_id`を取得する必要があります。

> 推奨モデル：火山引擎の`doubao-seed-1-6-250615`、`doubao-seed-1-6-flash-250715`、智譜の`glm-4-flash`、阿里雲の`qwen-plus`、
> `qwen-turbo`、deepseekの`deepseek-chat`など。

| プラットフォーム名  | APIキー取得方法                                                                                 | baseurl                                                  |
|------------|-------------------------------------------------------------------------------------------|----------------------------------------------------------|
| ollama     |                                                                                           | http://127.0.0.1:11434/v1                                |
| lm studio  |                                                                                           | http://127.0.0.1:1234/v1                                 |
| openrouter | [クリックして取得](https://openrouter.ai/settings/keys)                                           | https://openrouter.ai/api/v1                             |
| openai     | [クリックして取得](https://platform.openai.com/api-keys)                                          | https://api.openai.com/v1/                               |
| gemini     | [クリックして取得](https://aistudio.google.com/u/0/apikey)                                        | https://generativelanguage.googleapis.com/v1beta/openai/ |
| deepseek   | [クリックして取得](https://platform.deepseek.com/api_keys)                                        | https://api.deepseek.com/v1                              |
| 智譜AI       | [クリックして取得](https://open.bigmodel.cn/usercenter/apikeys)                                   | https://open.bigmodel.cn/api/paas/v4                     |
| テンセント混元    | [クリックして取得](https://console.cloud.tencent.com/hunyuan/api-key)                             | https://api.hunyuan.cloud.tencent.com/v1                 |
| 阿里雲百煉      | [クリックして取得](https://bailian.console.aliyun.com/?tab=model#/api-key)                        | https://dashscope.aliyuncs.com/compatible-mode/v1        |
| 火山引擎       | [クリックして取得](https://console.volcengine.com/ark/region:ark+cn-beijing/apiKey?apikey=%7B%7D) | https://ark.cn-beijing.volces.com/api/v3                 |
| 硅基流動       | [クリックして取得](https://cloud.siliconflow.cn/account/ak)                                       | https://api.siliconflow.cn/v1                            |
| DMXAPI     | [クリックして取得](https://www.dmxapi.cn/token)                                                   | https://www.dmxapi.cn/v1                                 |

### 2. minerUトークンの取得（オンライン解析）

`mineru`をドキュメント解析エンジンとして選択する場合（`convert_engine="mineru"`）、無料のトークンを申請する必要があります。

1. [minerU公式サイト](https://mineru.net/apiManage/docs)にアクセスし、登録してAPIを申請します。
2. [APIトークン管理画面](https://mineru.net/apiManage/token)で新しいAPIトークンを作成します。

> **注意**: minerUトークンは14日間有効で、期限切れの場合は再作成してください。

### 3. doclingエンジンの設定（ローカル解析）

`docling`をドキュメント解析エンジンとして選択する場合（`convert_engine="docling"`）、初回使用時にHugging
Faceから必要なモデルがダウンロードされます。

**ネットワーク問題の解決策:**

1. **Hugging Faceミラーの設定（推奨）**:

* **方法A（環境変数）**: システム環境変数`HF_ENDPOINT`を設定し、IDEまたはターミナルを再起動します。

```
   HF_ENDPOINT=https://hf-mirror.com
   ```

* **方法B（コード内設定）**: Pythonスクリプトの先頭に以下のコードを追加します。

```python
import os

os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
```

2. **オフライン使用（モデルパッケージの事前ダウンロード）**:

* [GitHub Releases](https://github.com/xunbu/docutranslate/releases)から`docling_artifact.zip`をダウンロードします。
* 解凍してプロジェクトディレクトリに配置します。
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

**Q: 8010ポートが使用中の場合どうすればよいですか？**
A: `-p`パラメータで新しいポートを指定するか、`DOCUTRANSLATE_PORT`環境変数を設定してください。

**Q: スキャンした文書の翻訳はサポートされていますか？**
A: サポートされています。強力なOCR機能を備えた`mineru`解析エンジンを使用してください。

**Q: 初回使用時になぜ遅いのですか？**
A: `docling`エンジンを使用する場合、初回実行時にHugging Faceからモデルをダウンロードする必要があります。上記の「ネットワーク問題の解決策」を参照してこのプロセスを高速化してください。

**Q: イントラネット（オフライン）環境で使用するにはどうすればよいですか？**
A: 完全に可能です。以下の2つの条件を満たす必要があります：

1. **ローカル解析エンジン**: `docling`エンジンを使用し、上記の「オフライン使用」の手順に従ってモデルパッケージを事前にダウンロードします。
2. **ローカルLLM**: [Ollama](https://ollama.com/)や[LM Studio](https://lmstudio.ai/)などのツールを使用してローカルに言語モデルをデプロイし、
   `TranslatorConfig`にローカルモデルの`base_url`を入力します。

**Q: キャッシュメカニズムはどのように機能しますか？**
A: `MarkdownBasedWorkflow`
は、ドキュメント解析（ファイルからMarkdownへの変換）の結果を自動的にキャッシュし、時間とリソースを節約します。キャッシュはデフォルトでメモリに保存され、直近の10回の解析が記録されます。
`DOCUTRANSLATE_CACHE_NUM`環境変数でキャッシュ数を変更できます。

**Q: ソフトウェアをプロキシ経由で使用するにはどうすればよいですか？**
A: ソフトウェアはデフォルトでプロキシを使用しません。環境変数`DOCUTRANSLATE_USE_PROXY`を`true`に設定することでプロキシ経由で使用できます。

## スター履歴

<a href="https://www.star-history.com/#xunbu/docutranslate&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
   <img alt="スター履歴チャート" src="https://api.star-history.com/svg?repos=xunbu/docutranslate&type=Date" />
 </picture>
</a>