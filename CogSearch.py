import json
import logging

import azure.functions as func
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from openai import AzureOpenAI

import libs.loadOpenAI as myopenAI

CogSearch = func.Blueprint()


@CogSearch.function_name(name="CogSearch")
@CogSearch.route(route="CogSearch")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function "CogSearch" processed a request.')

    query_prompt_template = """[Question] asked by the user that needs to be answered by searching in a knowledge base about help desk and product documents for Japanese client.
Generate a search query for Azure Cognitive Search based on [Question]. 
Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
Do not include any text inside [] or <<>> in the search query terms.

[Question]
{question}
"""

    prompt_prefix = """Answer [Question] ONLY with the facts listed in the list of [Sources] below. If there isn't enough information below, say "分かりませんでした". Do not generate answers that don't use the [Sources] below.
For tabular information return it as markdown format. Do not return an html table.
Each source has a name followed by colon and the actual information, always include the source name for each fact you use in the response. Use square brakets to reference the source, e.g. [info1.txt]. Don't combine sources, list each source separately, e.g. [info1.txt][info2.pdf].

[Question]
{question}

[Sources]
{sources}
"""

    # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
    model = req.params.get("model")
    if not model:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            model = req_body.get("model")

    question = req.params.get("question")
    if not question:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            question = req_body.get("question")

    client = AzureOpenAI()

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant helps the Japanese company employees with their questions about IT systems, troubles and products. Be brief and use polite Japanese in your answers.",
            },
            {
                "role": "user",
                "content": query_prompt_template.format(question=question),
            },
        ],
    )
    q = completion.choices[0].message.content

    # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
    search_client = SearchClient(
        endpoint=myopenAI.COGNITIVE_SEARCH_ENDPOINT,
        index_name=myopenAI.COGNITIVE_SEARCH_INDEX,
        credential=AzureKeyCredential(myopenAI.COGNITIVE_SEARCH_API_KEY),
    )

    r = search_client.search(
        q,
        top=3,
    )

    results = [
        doc["sourcepage"] + ": " + doc["content"].replace("\n", " ").replace("\r", " ")
        for doc in r
    ]

    if len(results) == 0:
        return func.HttpResponse(json.dumps({}))

    content = "\n".join(results)

    prompt = prompt_prefix.format(question=question, sources=content)

    completion = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are an assistant helps the Japanese company employees with their questions about IT systems, troubles and products. Be brief and use polite Japanese in your answers.",
            },
            {"role": "user", "content": prompt},
        ],
    )

    return func.HttpResponse(
        json.dumps(
            {
                "query": q,
                "data_points": results,
                "answer": completion.choices[0].message.content,
            },
            ensure_ascii=False,
        ),
        status_code=200,
    )
