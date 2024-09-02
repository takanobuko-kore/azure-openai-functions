# Azure OpenAI Functions
Azure OpenAI の埋め込み (Embeddings) を用いて FAQ 回答したり、検索サービス (Azure AI Search) を利用して検索・要約をしたりするための関数アプリ (Azure Functions)

## 前提
Kore.ai XO Platform のナレッジ AI でも V10.1 から同様の機能が標準搭載される予定だが、2023/11 時点では日本語に対応していないため本機能を作成

## 構築手順

### 必要コンポーネント (ローカルテスト含む)
- Azure Function Core Tools v4
- Python 3.11
- VSCode
  - 拡張機能: Azure Functions

### 初期構築手順
1. Azure OpenAI をデプロイ
2. Azure OpenAI のモデルをデプロイ
3. VSCode の `Azure: RESOURCES` から Azure にログイン
4. 関数アプリを作成
5. [設定] - [構成] - [アプリケーション設定] に下記を追加

    | App Setting Name | Value |
    | --- | --- |
    | AZURE_OPENAI_ENDPOINT | [Azure OpenAI] - [キーとエンドポイント] - [エンドポイント] |
    | OPENAI_API_VERSION | "2023-05-15"<br>cf. https://github.com/Azure/azure-rest-api-specs/tree/main/specification/cognitiveservices/data-plane/AzureOpenAI/inference/stable |
    | AZURE_OPENAI_EMB_DEPLOYMENT | [Azure OpenAI] - [モデル デプロイ] - [モデル デプロイ名] |

6. [設定] - [ID] - [システム割り当て済み] から [状態] を「オン」にし、保存
7. 作成した Azure OpenAI の [アクセス制御 (IAM)] - [追加] - [ロールの割り当ての追加]
    - ロール: Cognitive Services OpenAI User
    - メンバー
      - アクセスの割り当て先: マネージド ID
      - メンバー
        - サブスクリプション: (Azure OpenAI をデプロイしたサブスクリプション)
        - マネージド ID: 関数アプリ
        - メンバー: (作成した関数アプリを選択)
8. `git clone`
9.  `./embedding_csv` に埋め込み済みのFAQファイルを配置
    - **desktop.ini が入らないように注意**
10. VSCode の `Azure: WORKSPACE` から Azure にデプロイ

![image](https://user-images.githubusercontent.com/110897881/232027696-ba6b54ad-9912-4a25-9510-92117cb158ca.png)

### 検索サービスを利用する場合
1. 検索サービスと関連リソースをデプロイ
    - [1つのリソースで複数テナント用にデータソースを分けて構築する方法](https://github.com/takanobuko-kore/azure-search-openai-demo/blob/main/docs/multitenant.md)
2. 作成した検索サービスの [アクセス制御 (IAM)] - [追加] - [ロールの割り当ての追加]
      - ロール: 検索インデックス データ閲覧者
      - メンバー
        - アクセスの割り当て先: マネージド ID
        - メンバー
          - サブスクリプション: (Azure OpenAI をデプロイしたサブスクリプション)
          - マネージド ID: 関数アプリ
          - メンバー: (作成した関数アプリを選択)
3. 作成したストレージ アカウントの [アクセス制御 (IAM)] - [追加] - [ロールの割り当ての追加]
      - ロール: ストレージ BLOB データ閲覧者
      - メンバー
        - アクセスの割り当て先: マネージド ID
        - メンバー
          - サブスクリプション: (Azure OpenAI をデプロイしたサブスクリプション)
          - マネージド ID: 関数アプリ
          - メンバー: (作成した関数アプリを選択)
4. [設定] - [構成] - [アプリケーション設定] に下記を追加

    | App Setting Name | Value |
    | --- | --- |
    | AZURE_SEARCH_SERVICE | [検索サービス] - [名前] |
    | AZURE_SEARCH_INDEX  | [検索サービス] - [インデックス] - [名前] |
    | AZURE_STORAGE_ACCOUNT | [ストレージ アカウント] - [名前] |
    | AZURE_STORAGE_CONTAINER  | [ストレージ アカウント] - [コンテナー] - [名前] |

## ローカル環境での実行

### テスト

1. Application Settings を右クリックし「Download Remote Settings...」をクリックして `local.settings.json` をダウンロード
2. `func start`
3. http://localhost:7071/api/<関数名> で関数を実行

### 埋め込み手順 (Training)

**ローカル環境でのみ実行可能**

1. `./csv` に FAQ ファイルを配置
    - ファイル形式: csv
    - エンコード: `UTF-8`
    - 予約ヘッダー: `target`, `n_tokens`, `embedding`, `url`
2. API 実行
    | リクエスト ||
    |-|-|
    | *メソッド* | POST |
    | *エンドポイント* | http://localhost:7071/api/Training |
    | *ヘッダ* | Content-Type: application/json |

    | *ボディ* ||||
    |-|-|-|-|
    | filename | 必須 | String | ファイル名 |
    | target | 必須 | String | 埋め込み対象項目 |
    | url | オプション | String | ファイル URL |

FAQ ファイルの **target** 列に対して、8192トークン以下であれば各行に `[embedding](埋め込みベクトル)` を追加する   
埋め込みされたファイルは `./embedding_csv/` に保存される  
**url** に値を入れると `[url]` という項目も追加される

![image](https://user-images.githubusercontent.com/110897881/232028331-f22e677d-f0ae-42d5-9ed1-cb8a8998d433.png)

## 関数一覧

#### (備考) リモート環境で実行するには
関数アプリのアプリ キーはエンドポイントの末尾に `?code=` として入れるか、ヘッダに `x-functions-key` として入れる

---

### Ping

| リクエスト ||
|-|-|
| *メソッド* | GET |
| *エンドポイント* | https://{{ENDPOINT}}/api/Ping |

URLへのPingを実施  
Azure Functionsのコールドスタート対策  

---

### 検索 (Search)

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
| top | オプション | Number<br>(1～) | 取得する検索結果の数<br>(デフォルト: 3) |
| orient | オプション | "split", "records", "index", "columns", "values", "table"<br>[参考](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_json.html) | 応答ボディのJSONフォーマット<br>(デフォルト: records) |

質問クエリの Embedding を計算後、FAQ 内の各 Embedding とコサイン類似度を取る  
最も近いデータを JSON で返す  
**filename** に与える値によって検索対象を変更できる
  - String を設定するとそのファイルのみから
  - Array を設定すると指定したファイル全てから
  - "all" を設定すると `./embedding_csv` 内のファイル全てから

検索結果には `[filename](ファイル名)`, `[similarities](類似度)` が追加され、`[embedding]` は削除される

![image](https://user-images.githubusercontent.com/110897881/232030768-165a5851-8d08-4486-80ef-8e300248128e.png)

---

### ドキュメント検索 (CogSearch)

| リクエスト ||
|-|-|
| *メソッド* | POST |
| *エンドポイント* | https://{{ENDPOINT}}/api/CogSearch |
| *ヘッダ* | Content-Type: application/json |

| *ボディ* ||||
|-|-|-|-|
| index_name | オプション | String | 対象のインデックス名<br>(デフォルト: 環境変数<AZURE_SEARCH_INDEX>) |
| question | 必須 | String | 質問クエリ |
| top | オプション | String | 取得する検索結果の数<br>(デフォルト: 3) |
| model | 必須 | String | GPT モデルデプロイ名 |

**question** から検索サービスでの検索用クエリを生成する  
**question** と生成された embedding で検索サービスで検索  
検索結果を要約して JSON で返す  
返す値は下記の通り
- answer: 要約文 
- data_points: 検索サービスでの検索結果
- thoughts: 検索サービスでの検索用クエリ

[参考](https://github.com/Azure-Samples/azure-search-openai-demo/blob/main/app/backend/approaches/retrievethenread.py)
- retrieval_mode: "hybrid"
- semantic_ranker: true
- query_type=QueryType.SEMANTIC,
- query_language="ja-JP",
- query_speller="none",
- semantic_configuration_name="default"

| リクエスト ||
|-|-|
| *メソッド* | GET |
| *エンドポイント* | https://{{ENDPOINT}}/api/CogSearch/content/{{filename}} |
| *ヘッダ* | Content-Type: application/json |

| *クエリ* ||||
|-|-|-|-|
| filename | 必須 | String | ファイル名 |

**AZURE_STORAGE_CONTAINER** 内の該当ファイルをダウンロード

---

### 生成 (ChatCompletion)

| リクエスト ||
|-|-|
| *メソッド* | POST |
| *エンドポイント* | https://{{ENDPOINT}}/api/ChatCompletion |
| *ヘッダ* | Content-Type: application/json |

| *ボディ* ||||
|-|-|-|-|
| model | 必須 | String | GPT モデルデプロイ名 |
| messages | 必須 | Array<br>[参考](https://learn.microsoft.com/ja-jp/azure/ai-services/openai/how-to/chatgpt?tabs=python-new&pivots=programming-language-chat-completions) | メッセージ |

**model** に対し **messages** を渡し、その結果を JSON で返す
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
