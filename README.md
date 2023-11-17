# Azure OpenAI Functions
Azure OpenAIの埋め込み機能を用いてFAQ回答したり、Cognitive Searchを利用して検索・要約をしたりするためのAzure Fuctions

## 前提
Kore.ai PlatformのナレッジAIでもV10.1から同様の機能が標準搭載される予定だが、2023/11時点では日本語に対応していないため本機能を作成

## 構築手順

### 必要コンポーネント(ローカルテスト含む)
- Azure Function Core Tools v4
- Python 3.11
- VSCode
  - 拡張機能: Azure Functions

### 初期構築手順
Cognitive Searchを利用するなら → https://github.com/Azure-Samples/azure-search-openai-demo

1. Azure OpenAIリソースをデプロイ
2. Azure OpenAIのモデルをデプロイ
    - 2023/11時点では `text-embedding-ada-002` が最適
3. VSCodeの `Azure: RESOURCES` からAzureにログイン
4. Function Appを作成
5. Application Settingsに下記を追加

    | App Setting Name | Value |
    | --- | --- |
    | AZURE_OPENAI_API_KEY | [Azure OpenAI] - [キーとエンドポイント] - [キー1/2どちらか] |
    | AZURE_OPENAI_ENDPOINT | [Azure OpenAI] - [キーとエンドポイント] - [エンドポイント] |
    | OPENAI_API_VERSION | "2023-05-15"<br>cf. https://github.com/Azure/azure-rest-api-specs/tree/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable |
    | EMBEDDING_MODEL_DEPLOYMENT_NAME | [Azure OpenAI] - [モデル デプロイ] - [モデル デプロイ名] |
    | COGNITIVE_SEARCH_API_KEY | [検索サービス] - [キー] - [プライマリ管理者キー] |
    | COGNITIVE_SEARCH_ENDPOINT | [検索サービス] - [概要] - [URL] |
    | COGNITIVE_SEARCH_INDEX  | [検索サービス] - [インデックス] - [名前] |

6. `git clone`
7. `./embedding_csv` に埋め込み済みのFAQファイルを配置
8. VSCodeの `Azure: WORKSPACE` からAzureにデプロイ

![image](https://user-images.githubusercontent.com/110897881/232027696-ba6b54ad-9912-4a25-9510-92117cb158ca.png)

## ローカル環境での実行

### テスト

1. Application Settingsを右クリックし「Download Remote Settings...」をクリックして `local.settings.json` をダウンロード
2. `func start`
3. http://localhost:7071/api/<関数名> で関数を実行

### 埋め込み手順(Training)

**ローカル環境でのみ実行可能**

1. `./csv` にFAQファイルを配置
    - ファイル形式: csv
    - エンコード: `UTF-8`
2. API実行
    | リクエスト ||
    |-|-|
    | *メソッド* | POST |
    | *エンドポイント* | http://localhost:7071/api/Training |
    | *ヘッダ* | Content-Type: application/json |

    | *ボディ* ||||
    |-|-|-|-|
    | filename | 必須 | String | ファイル名 |
    | target | 必須 | String | 埋め込み対象項目 |
    | url | オプション | String | ファイルURL |

FAQファイルの **target** 列に対して各行に `[n_tokens](埋め込み対象項目のトークン数)`, `[embedding](埋め込みベクトル)` を追加する   
埋め込みされたファイルは `./embedding_csv/` に保存される  
**url** に値を入れると `[url]` という項目も追加される

![image](https://user-images.githubusercontent.com/110897881/232028331-f22e677d-f0ae-42d5-9ed1-cb8a8998d433.png)

## 関数一覧

#### (備考)リモート環境で実行するには
Azure Functionsのアプリ キーはエンドポイントの末尾に `?code=` として入れるか、ヘッダに `x-functions-key` として入れる

---

### 検索(Search)

| リクエスト ||
|-|-|
| *メソッド* | POST |
| *エンドポイント* | https://{{ENDPOINT}}/api/Search |
| *ヘッダ* | Content-Type: application/json |

| *ボディ* ||||
|-|-|-|-|
| question | 必須 | String | 質問クエリ |
| filename | オプション | String, Array, "all" | 検索対象ファイル名<br>(デフォルト: all) |
| threshold | オプション | Number<br>(0～1) | コサイン類似度の閾値<br>(デフォルト: 0.8) |
| top | オプション | Number<br>(1～) | 検索結果上位から表示する数<br>(デフォルト: 3) |
| orient | オプション | "split", "records", "index", "columns", "values", "table"<br>[参考](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html) | 応答ボディのJSONフォーマット<br>(デフォルト: records) |

質問クエリのEmbeddingを計算後、FAQ内の各Embeddingとコサイン類似度を取る  
最も近いデータをJSONで返す  
**filename** に与える値によって検索対象を変更できる
  - Stringを設定するとそのファイルのみから
  - Arrayを設定すると指定したファイル全てから
  - "all"を設定すると `./embedding_csv` 内のファイル全てから

検索結果には `[filename](ファイル名)`, `[similarities](類似度)` が追加され、`[embedding]` は削除される

![image](https://user-images.githubusercontent.com/110897881/232030768-165a5851-8d08-4486-80ef-8e300248128e.png)

---

### ドキュメント検索(CogSearch)

| リクエスト ||
|-|-|
| *メソッド* | POST |
| *エンドポイント* | https://{{ENDPOINT}}/api/CogSearch |
| *ヘッダ* | Content-Type: application/json |

| *ボディ* ||||
|-|-|-|-|
| model | 必須 | String | GPTモデルデプロイ名 |
| question | 必須 | String | 質問クエリ |

**model** に対し **question** からCognitive Searchでの検索用クエリを生成する  
Cognitive Searchで検索後、検索結果上位3件のデータを要約してJSONで返す  
返す値は下記の通り
- query: Cognitive Searchでの検索用クエリ
- data_points: Cognitive Searchでの検索結果
- answer: 要約文

[参考](https://github.com/Azure-Samples/azure-search-openai-demo/blob/6ac7c909c02d760bafd5e5e838fa8c2a46dd4aaf/app/backend/approaches/chatreadretrieveread.py)

---

### 生成(ChatCompletion)

| リクエスト ||
|-|-|
| *メソッド* | POST |
| *エンドポイント* | https://{{ENDPOINT}}/api/ChatCompletion |
| *ヘッダ* | Content-Type: application/json |

| *ボディ* ||||
|-|-|-|-|
| model | 必須 | String | GPTモデルデプロイ名 |
| messages | 必須 | Array<br>[参考](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/chatgpt?tabs=python-new&pivots=programming-language-chat-completions) | メッセージ |

**model** に対し **messages** を渡し、その結果をJSONで返す
**messages** の書式は下記の通り
```
[
  {"role": "system", "content": "Provide some context and/or instructions to the model."},
  {"role": "user", "content": "Example question goes here."},
  {"role": "assistant", "content": "Example answer goes here."}
]
```

## 参考
[クイックスタート: Visual Studio Code と Python を使用して Azure に関数を作成する](https://learn.microsoft.com/ja-jp/azure/azure-functions/create-first-function-vs-code-python?pivots=python-mode-configuration)

[Azure Functions の継続的なデプロイ](https://learn.microsoft.com/ja-jp/azure/azure-functions/functions-continuous-deployment)
