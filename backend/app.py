from robyn import Robyn, Request, Response
from robyn.logger import Logger
from robyn_lib.routes.route_handler import FeatureRouteHandler
from datetime import datetime
from robyn_lib.services.services import OSFeatureService, DataService, LangChainSummaryService

# TODO improve error handling

# DEFINE APP AND LOGGER
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
    logger.info(f"Request: method={request.method} params={request.query_params}, path={request.url.path}, params={request.body}, ip_address={request.ip_addr}, time={datetime.now()}")
    return request

@app.after_request()
async def log_response(response: Response):
    """Log responses - success status only for successful requests, full details for errors"""
    if response.status_code >= 400:  # Log full details for errors
        log_level = get_log_level_for_status(response.status_code)
        
        error_detail = response.description if hasattr(response, 'description') else ''

        log_message = f"Response: status={response.status_code}, type={response.response_type}, details={error_detail}"

        if log_level == "error":
            logger.error(log_message)
        else:
            logger.warn(log_message)
    else:  # Just log status for successful requests
        logger.info(f"Response: status={response.status_code}, type={response.response_type}")

    return response

# DEFINE ROUTES
# Initialize dependencies
feature_service = OSFeatureService()
data_service = DataService()
llm_summary_service = LangChainSummaryService()

# Create handler with dependencies
route_handler = FeatureRouteHandler(
    feature_service=feature_service,
    geometry_service=data_service,
    street_manager_service=data_service,
    llm_summary_service=llm_summary_service
)

# Create routes
app.get("/street-info")(route_handler.get_street_info_route)
app.get("/street-info-llm")(route_handler.get_street_info_route_llm)
app.get("/land-use-info")(route_handler.get_land_use_route)
app.get("/land-use-info-llm")(route_handler.get_land_use_route_llm)

if __name__ == "__main__":
    app.start(port=8080)
