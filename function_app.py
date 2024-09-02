import azure.functions as func

from ChatCompletion import ChatCompletion
from CogSearch import CogSearch
from Ping import Ping
from Search import Search
from Training import Training

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

app.register_functions(ChatCompletion)
app.register_functions(CogSearch)
app.register_functions(Search)
app.register_functions(Training)
app.register_functions(Ping)
