import io
import json
import logging
import mimetypes

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.search.documents import SearchClient
from azure.search.documents.models import QueryType, RawVectorQuery, VectorQuery
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI

import libs.loadOpenAI as myopenAI

CogSearch = func.Blueprint()


@CogSearch.function_name(name="CogSearchContent")
@CogSearch.route(
    route="CogSearch/content/{filename}",
    auth_level=func.AuthLevel.ANONYMOUS,
)
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function "CogSearchContent" processed a request.')
    path = req.route_params.get("filename")

    # Remove page number from path, filename-1.txt -> filename.txt
    if path.find("#page=") > 0:
        path_parts = path.rsplit("#page=", 1)
        path = path_parts[0]

    blob_client = BlobServiceClient(
        account_url=f"https://{myopenAI.AZURE_STORAGE_ACCOUNT}.blob.core.windows.net",
        credential=DefaultAzureCredential(exclude_shared_token_cache_credential=True),
    )
    blob_container_client = blob_client.get_container_client(
        myopenAI.AZURE_STORAGE_CONTAINER
    )

    try:
        blob = blob_container_client.get_blob_client(path).download_blob()
    except ResourceNotFoundError:
        logging.exception("Path not found: %s", path)
        return func.HttpResponse(status_code=404)
    if not blob.properties or not blob.properties.has_key("content_settings"):
        return func.HttpResponse(status_code=404)
    mime_type = blob.properties["content_settings"]["content_type"]
    if mime_type == "application/octet-stream":
        mime_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
    blob_file = io.BytesIO()
    blob.readinto(blob_file)
    blob_file.seek(0)

    return func.HttpResponse(blob_file.read(), status_code=200, mimetype=mime_type)


@CogSearch.function_name(name="CogSearch")
@CogSearch.route(route="CogSearch")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function "CogSearch" processed a request.')

    q = req.params.get("question")
    if not q:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            q = req_body.get("question")

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

    model = req.params.get("model")
    if not model:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            model = req_body.get("model")

    client = AzureOpenAI(
        azure_ad_token_provider=get_bearer_token_provider(
            DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
        )
    )

    # If retrieval mode includes vectors, compute an embedding for the query
    embedding = client.embeddings.create(
        model=myopenAI.AZURE_OPENAI_EMB_DEPLOYMENT, input=q
    )

    vectors: list[VectorQuery] = []
    vectors.append(
        RawVectorQuery(vector=embedding.data[0].embedding, k=50, fields="embedding")
    )

    # Only keep the text query if the retrieval mode uses text, otherwise drop it
    search_client = SearchClient(
        endpoint=f"https://{myopenAI.AZURE_SEARCH_SERVICE}.search.windows.net",
        index_name=myopenAI.AZURE_SEARCH_INDEX,
        credential=DefaultAzureCredential(exclude_shared_token_cache_credential=True),
    )

    r = search_client.search(
        q,
        query_type=QueryType.SEMANTIC,
        query_language="ja-JP",
        query_speller="none",
        semantic_configuration_name="default",
        top=top,
        vector_queries=vectors,
    )
    results = [
        doc["sourcepage"] + ": " + doc["content"].replace("\n", " ").replace("\r", " ")
        for doc in r
    ]

    content = "\n".join(results)

    messages = [
        {
            "role": "system",
            "content": """You are an intelligent assistant helping Contoso Inc employees with their healthcare plan questions and employee handbook questions.
Use 'you' to refer to the individual asking the questions even if they ask with 'I'.
Answer the following question in Japanese using only the data provided in the sources below.
For tabular information return it as an html table. Do not return markdown format.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response.
If you cannot answer using the sources below, say you don't know. Use below example to answer""",
        }
    ]

    # Add shots/samples. This helps model to mimic response and make sure they match rules laid out in system message.
    messages.append(
        {
            "role": "user",
            "content": """'What is the deductible for the employee plan for a visit to Overlake in Bellevue?'

Sources:
info1.txt: deductibles depend on whether you are in-network or out-of-network. In-network deductibles are $500 for employee and $1000 for family. Out-of-network deductibles are $1000 for employee and $2000 for family.
info2.pdf: Overlake is in-network for the employee plan.
info3.pdf: Overlake is the name of the area that includes a park and ride near Bellevue.
info4.pdf: In-network institutions include Overlake, Swedish and others in the region""",
        }
    )
    messages.append(
        {
            "role": "assistant",
            "content": "In-network deductibles are $500 for employee and $1000 for family [[info1.txt]] and Overlake is in-network for the employee plan [[info2.pdf]][[info4.pdf]].",
        }
    )

    # add user question
    user_content = q + "\n" + f"Sources:\n {content}"
    messages.append({"role": "user", "content": user_content})

    chat_completion = client.chat.completions.create(model=model, messages=messages)

    return func.HttpResponse(
        json.dumps(
            {
                "answer": chat_completion.choices[0].message.content,
                "data_points": results,
                "thoughts": f"Question:<br>{q}<br><br>Prompt:<br>"
                + "\n\n".join([str(message) for message in messages]),
            },
            ensure_ascii=False,
        ),
        status_code=200,
    )
