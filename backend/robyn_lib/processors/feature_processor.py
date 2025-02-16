import asyncio
from typing import Dict, Any, Optional, List
from loguru import logger
from os_lib.os_data_object import OSDataObject
from ..routes.route_handler import RouteType

async def process_features(
    path_type: str,
    usrn: str,
    bbox: str,
    bbox_crs: str,
    crs: str
) -> Dict[str, Any]:
    """
    Process features based on path type with support for both street info and land use routes
    
    Args:
        path_type: str - The route path type ('land-use' or 'street-info')
        usrn: Optional[str] - USRN for filtering
        bbox: Optional[str] - Bounding box for land use queries
        bbox_crs: Optional[str] - CRS for bounding box
        crs: Optional[str] - Target CRS for response
    
    Returns:
        Dict containing the combined feature collection
    
    Raises:
        ValueError: For validation errors
        Exception: For other errors
    """
    try:
        if not usrn:
            raise ValueError("A valid usrn is required")
        
        # Define route type as this is use to determine the collections to query
        route_type = RouteType(path_type)

        # Create OS data object
        os_data = OSDataObject()

        # Define collection IDs based on path type
        match route_type:
            case RouteType.STREET_INFO:
                logger.info(f"Processing street info for USRN: {usrn}")
                collection_ids = [
                    "trn-ntwk-street-1",
                    "trn-rami-specialdesignationarea-1",
                    "trn-rami-specialdesignationline-1",
                    "trn-rami-specialdesignationpoint-1"
                ]
                # Create coroutines for RAMI/Network collections
                feature_coroutines = [
                    os_data.get_collection_features(
                        collection_id=collection_id,
                        usrn_attr="usrn",
                        usrn_attr_value=usrn
                    )
                    for collection_id in collection_ids
                ]

            case RouteType.LAND_USE:
                logger.info(f"Processing land use for USRN: {usrn}")
                collection_ids = [
                    "bld-fts-building-1",
                    "lus-fts-site-1"
                ]
                if not bbox:
                    raise ValueError("A valid bbox is required for land use queries")
                
                # Create coroutines for Land Use/Building collections
                feature_coroutines = [
                    os_data.get_collection_features(
                        collection_id=collection_id,
                        bbox=bbox,
                        bbox_crs=bbox_crs or "http://www.opengis.net/def/crs/EPSG/0/27700",
                        crs=crs or "http://www.opengis.net/def/crs/EPSG/0/27700"
                    )
                    for collection_id in collection_ids
                ]

            case _:
                raise ValueError(f"Unsupported path type: {path_type}")

        # Gather and await all coroutines
        feature_results = await asyncio.gather(*feature_coroutines, return_exceptions=True)

        # Process results
        all_features: List[Dict[str, Any]] = []
        latest_timestamp: Optional[str] = None

        for collection_id, result in zip(collection_ids, feature_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {collection_id}: {str(result)}")
                continue

            if not isinstance(result, dict) or 'features' not in result:
                logger.error(f"Invalid response format from {collection_id}")
                continue

            # Filter out geometry from each feature
            filtered_features = []
            for feature in result['features']:
                feature_copy = feature.copy()
                if 'geometry' in feature_copy:
                    del feature_copy['geometry']
                
                if 'geometry' in feature_copy:
                    raise ValueError(f"Failed to remove geometry from feature in {collection_id}")
                
                
                filtered_features.append(feature_copy)

            # Remove geometry from each feature - as this creates too many tokens when using the llm service
            logger.success("Geometries Removed")
            all_features.extend(filtered_features)

            # Track latest timestamp
            if result.get('timeStamp'):
                if latest_timestamp is None or result['timeStamp'] > latest_timestamp:
                    latest_timestamp = result['timeStamp']

        if not all_features:
            logger.warning(f"No features found for USRN: {usrn}")

        return {
            'type': 'FeatureCollection',
            'numberReturned': len(all_features),
            'timeStamp': latest_timestamp or "",
            'features': all_features
        }

    except ValueError as ve:
        logger.error(f"Validation error in process_features: {ve}")
        raise
    except Exception as e:
        logger.error(f"Error in process_features: {e}")
        raise