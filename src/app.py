from robyn import Robyn, Request, Response
from robyn.logger import Logger
from robyn_lib.ngd_features import get_features, get_collections
from datetime import datetime

app = Robyn(__file__)

# SET UP LOGGER TO CAPTURE ALL REQUESTS
logger = Logger()

@app.before_request()
async def log_request(request: Request):
    logger.info(f"Request: method={request.method}, path={request.url.path}, ip_address={request.ip_addr}, time={datetime.now()}")
    return request

@app.after_request()
async def log_response(response: Response):
    logger.info(f"Response: status={response.status_code}, type={response.response_type}")
    return response

# DEFINE ROUTES
app.get("/features")(get_features.get_features_route)
app.get("/collections")(get_collections.get_all_collections_route)

if __name__ == "__main__":
    app.start(port=8080)
