import logging
import re

import azure.functions as func
import pandas as pd
import tiktoken
from openai import AzureOpenAI

import libs.loadOpenAI as myopenAI

Training = func.Blueprint()


@Training.function_name(name="Training")
@Training.route(route="Training")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    filename = req.params.get("filename")
    if not filename:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            filename = req_body.get("filename")

    target = req.params.get("target")
    if not target:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            target = req_body.get("target")

    url = req.params.get("url")
    if not url:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            url = req_body.get("url")

    # CSVファイル読み込み
    logging.info("csv/" + filename)
    df = pd.read_csv("csv/" + filename, encoding="utf8")

    # URLを付与
    if url != None:
        df["url"] = url

    # s is input text
    def normalize_text(s):
        s = re.sub(r"\s+", " ", s).strip()
        s = re.sub(r". ,", "", s)
        # remove all instances of multiple spaces
        s = s.replace("..", ".")
        s = s.replace(". .", ".")
        s = s.replace("\n", "")
        s = s.strip()

        return s

    # 質問文を正規化
    df[target] = df[target].apply(lambda x: normalize_text(x))

    # 質問文をトークン制限(8192トークン)
    tokenizer = tiktoken.get_encoding("cl100k_base")
    df["n_tokens"] = df[target].apply(lambda x: len(tokenizer.encode(x)))
    df = df[df.n_tokens < 8192]

    client = AzureOpenAI()

    # 埋め込み(embedding)
    df["embedding"] = df[target].apply(
        lambda x: client.embeddings.create(
            input=x, model=myopenAI.AZURE_OPENAI_EMB_DEPLOYMENT
        )
        .data[0]
        .embedding
    )

    # CSVファイル書き出し
    df.to_csv("embedding_csv/" + filename, encoding="utf8")

    return func.HttpResponse("トレーニングが完了しました。", status_code=200)
