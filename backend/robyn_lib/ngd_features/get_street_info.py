import json
import requests
import asyncio
from loguru import logger
from robyn import Response
from robyn.robyn import QueryParams
from robyn_lib.utils.process_features import process_features
from typing import List, Dict, Any, Optional
from robyn_lib.langchain_processor.processor import process_with_langchain

async def get_street_info_route(query_params: QueryParams) -> Response:
    """
    API route to get features data with support for RAMI collection.
    
    Args:
        query_params (QueryParams): Query parameters containing USRN
        
    Returns:
        Response: HTTP response containing feature collection data
        
    Raises:
        ValueError: If USRN parameter is missing or invalid
        requests.exceptions.HTTPError: If upstream API request fails
        Exception: For other unexpected errors
    """
    # Define the collection IDs for the street info route
    COLLECTION_IDS = [
        "trn-ntwk-street-1",
        "trn-rami-specialdesignationarea-1",
        "trn-rami-specialdesignationline-1",
        "trn-rami-specialdesignationpoint-1"
    ]

    try:
        usrn = query_params.get('usrn')
        if not usrn:
            raise ValueError("Missing required parameter: usrn")

        # Create coroutines for concurrent execution
        feature_coroutines = [
            process_features(collection_id=collection_id, usrn=usrn)
            for collection_id in COLLECTION_IDS
        ]
        
        # Gather and await all coroutines
        feature_results = await asyncio.gather(*feature_coroutines, return_exceptions=True)
        
        all_features: List[Dict[str, Any]] = []
        latest_timestamp: Optional[str] = None

        # Process results and handle any individual collection failures
        for collection_id, result in zip(COLLECTION_IDS, feature_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to fetch {collection_id}: {str(result)}")
                continue
                
            if not isinstance(result, dict) or 'features' not in result:
                logger.error(f"Invalid response format from {collection_id}")
                continue

            # Remove filtering and directly add features
            all_features.extend(result['features'])
            
            # Keep track of the latest timestamp
            if result.get('timeStamp'):
                if latest_timestamp is None or result['timeStamp'] > latest_timestamp:
                    latest_timestamp = result['timeStamp']

        if not all_features:
            logger.warning(f"No features found for USRN: {usrn}")

        filtered_response = {
            'type': 'FeatureCollection',
            'numberReturned': len(all_features),
            'timeStamp': latest_timestamp or "",
            'features': all_features
        }

        # Process the features with LangChain
        analysis_result = await process_with_langchain(
            data=filtered_response,
            route_type="street_info" 
        )

        return Response(
            status_code=200,
            headers={"Content-Type": "application/json"},
            description=json.dumps(analysis_result),
        )

    except requests.exceptions.HTTPError as http_err:
        status_code = http_err.response.status_code if hasattr(http_err, 'response') else 500
        logger.error(f"HTTP error occurred: {http_err}")
        return Response(
            status_code=status_code,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(http_err)}),
        )

    except ValueError as ve:
        logger.error(f"Validation error: {ve}")
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(ve)}),
        )

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return Response(
            status_code=500,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(e)}),
        )