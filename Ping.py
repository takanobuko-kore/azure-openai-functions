import logging

import azure.functions as func

Ping = func.Blueprint()


@Ping.function_name(name="Ping")
@Ping.route(route="Ping")
def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    return func.HttpResponse(status_code=200)
