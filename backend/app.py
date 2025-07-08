from robyn import Robyn, Request, Response
from robyn.logger import Logger
from robyn_lib.routes.route_handler import FeatureRouteHandler
from datetime import datetime
from robyn_lib.services.services import (
    OSFeatureService,
    DataService,
    LangChainSummaryService,
)

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
    logger.info(
        f"Request: method={request.method} params={request.query_params}, path={request.url.path}, params={request.body}, ip_address={request.ip_addr}, time={datetime.now()}"
    )
    return request


@app.after_request()
async def log_response(response: Response):
    """Log responses - success status only for successful requests, full details for errors"""
    if response.status_code >= 400:  # Log full details for errors
        log_level = get_log_level_for_status(response.status_code)

        error_detail = response.description if hasattr(response, "description") else ""

        log_message = f"Response: status={response.status_code}, type={response.response_type}, details={error_detail}"

        if log_level == "error":
            logger.error(log_message)
        else:
            logger.warn(log_message)
    else:  # Just log status for successful requests
        logger.info(
            f"Response: status={response.status_code}, type={response.response_type}"
        )

    return response


# DEFINE ROUTES
# Initialise dependencies
feature_service = OSFeatureService()
data_service = DataService()
llm_summary_service = LangChainSummaryService()

# Initialise route handler
route_handler = FeatureRouteHandler(
    feature_service=feature_service,
    geometry_service=data_service,
    street_manager_service=data_service,
    llm_summary_service=llm_summary_service,
)


# Define endpoints
@app.get("/street-info")
async def street_info_route(request):
    """
    Summary of network and RAMI data as well as street manager stats
    """
    return await route_handler.get_street_info_route(request)


@app.get("/street-info-llm")
async def street_info_llm_route(request):
    """
    Summary of network and RAMI data as well as street manager stats + llm summary of all data
    """
    return await route_handler.get_street_info_route_llm(request)


@app.get("/land-use-info")
async def land_use_route(request):
    """
    Summary of Land use and building information
    """
    return await route_handler.get_land_use_route(request)


@app.get("/land-use-info-llm")
async def land_use_llm_route(request):
    """
    Summary of Land use and building information + llm summary of all data
    """
    return await route_handler.get_land_use_route_llm(request)


@app.get("/collaborative-street-works")
async def collaborative_street_works_route(request):
    """
    Collaborative street works recommendation
    """
    return await route_handler.get_collaborative_street_works_route(request)


if __name__ == "__main__":
    app.start(host="0.0.0.0", port=8080)
