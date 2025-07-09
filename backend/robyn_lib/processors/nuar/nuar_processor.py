from typing import Dict, Any
from loguru import logger
from os_lib.request_functions import fetch_nuar_data


async def get_nuar_asset_count(bbox: str) -> Dict[str, Any]:
    """
    Get asset count from NUAR API for a given bounding box

    Args:
        bbox: str - Bounding box in format "minx,miny,maxx,maxy"

    Returns:
        Dict[str, Any] - Asset count data from NUAR API
    """
    try:
        # Construct the NUAR API endpoint
        base_url = "https://innovation.nuar-data-services.uk/services/generalised-data/api/v1/metrics/AssetCount/nuar/12/"
        endpoint = f"{base_url}?bbox={bbox}"

        logger.info(f"Fetching NUAR asset count for bbox: {bbox}")
        logger.debug(f"NUAR API endpoint: {endpoint}")

        result = await fetch_nuar_data(endpoint)

        logger.success("Successfully retrieved NUAR asset count data")
        return result

    except Exception as e:
        logger.error(f"Error fetching NUAR asset count: {str(e)}")
        # Return a structured error response instead of raising
        return {
            "error": f"Failed to fetch NUAR asset count: {str(e)}",
            "asset_count": None,
            "bbox": bbox,
        }
