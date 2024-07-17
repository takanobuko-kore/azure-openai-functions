import glob
import logging

import azure.functions as func
import numpy as np
import pandas as pd
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from numba import jit
from openai import AzureOpenAI

import libs.loadOpenAI as myopenAI


@jit(nopython=True)
def cosine_similarity_numba(u: np.ndarray, v: np.ndarray):
    assert u.shape[0] == v.shape[0]
    uv = 0
    for i in range(u.shape[0]):
        uv += u[i] * v[i]
    return uv


Search = func.Blueprint()


@Search.function_name(name="Search")
@Search.route(route="Search")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function "Search" processed a request.')

    question = req.params.get("question")
    if not question:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            question = req_body.get("question")

    filename = req.params.get("filename")
    if not filename:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            filename = req_body.get("filename")
    if filename == None:
        filename = "all"

    threshold = req.params.get("threshold")
    if not threshold:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            threshold = req_body.get("threshold")
    if threshold == None:
        threshold = 0.8

    top = req.params.get("top")
    if not top:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            top = req_body.get("top")
    if top == None:
        top = 3

    orient = req.params.get("orient")
    if not orient:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            orient = req_body.get("orient")
    if orient == None:
        orient = "records"

    client = AzureOpenAI(
        azure_ad_token_provider=get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
    )

    embedding = np.array(
        client.embeddings.create(
            input=question, model=myopenAI.AZURE_OPENAI_EMB_DEPLOYMENT
        )
        .data[0]
        .embedding
    )

    # CSVファイル読み込み
    if filename != "all":
        if isinstance(filename, str):
            df = pd.read_csv("embedding_csv/" + filename, encoding="utf8")
            df["filename"] = filename
        else:
            df = pd.DataFrame()
            list_ = []

            for file_ in filename:
                df_ = pd.read_csv("embedding_csv/" + file_, encoding="utf8")
                df_["filename"] = file_
                list_.append(df_)
            df = pd.concat(list_)
    else:
        df = pd.DataFrame()
        list_ = []

        files = glob.glob("embedding_csv/*.*")
        for file_ in files:
            df_ = pd.read_csv(file_, encoding="utf8")
            df_["filename"] = file_.removeprefix("embedding_csv/")
            list_.append(df_)
        df = pd.concat(list_)

    df["similarities"] = df.embedding.apply(
        lambda x: cosine_similarity_numba(np.array(eval(x)), embedding)
    )
    res = (
        df[df["similarities"] >= threshold]
        .sort_values("similarities", ascending=False)
        .head(top)
        .drop("embedding", axis=1)
    )

    return func.HttpResponse(
        res.to_json(orient=orient),
        mimetype="application/json",
        status_code=200,
    )
