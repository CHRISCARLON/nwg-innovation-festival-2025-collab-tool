from robyn import Robyn, Request, Response
from robyn.logger import Logger
from robyn_lib.ngd_features import get_features, get_collections
from datetime import datetime

app = Robyn(__file__)
logger = Logger()

def get_log_level_for_status(status_code: int) -> str:
    """Determine the appropriate log level based on status code"""
    match status_code:
        case _ if status_code >= 500:
            return "error"
        case _ if status_code >= 400:
            return "warning"
        case _:
            return "info"

@app.before_request()
async def log_request(request: Request):
    """Log requests made"""
    logger.info(f"Request: method={request.method}, params={request.query_params}, path={request.url.path}, ip_address={request.ip_addr}, time={datetime.now()}")
    return request

@app.after_request()
async def log_response(response: Response):
    """Log request outputs for erros etc"""
    # Log with appropriate level based on status code
    log_level = get_log_level_for_status(response.status_code)
    log_message = f"Response: status={response.status_code}, type={response.response_type}"

    match log_level:
        case _ if log_level == "error":
            logger.error(log_message)
        case _ if log_level == "warning":
            logger.warn(log_message)
        case _:
            logger.info(log_message)

    return response

# DEFINE ROUTES
app.get("/features")(get_features.get_features_route)
app.get("/collections")(get_collections.get_all_collections_route)

if __name__ == "__main__":
    app.start(port=8080)
