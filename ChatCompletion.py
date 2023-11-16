import logging

import azure.functions as func
from openai import AzureOpenAI

ChatCompletion = func.Blueprint()


@ChatCompletion.function_name(name="ChatCompletion")
@ChatCompletion.route(route="ChatCompletion")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function "ChatCompletion" processed a request.')

    model = req.params.get("model")
    if not model:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            model = req_body.get("model")

    messages = req.params.get("messages")
    if not messages:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            messages = req_body.get("messages")

    client = AzureOpenAI()

    response = client.chat.completions.create(model=model, messages=messages)
    return func.HttpResponse(response.choices[0].message.content, status_code=200)
