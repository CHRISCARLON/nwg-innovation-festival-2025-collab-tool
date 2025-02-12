from robyn import Request, Response, jsonify
from robyn.robyn import QueryParams
from os_lib.os_data_object import OSDataObject
from typing import Dict, Any
import json

def get_features(collection_id: str, usrn: str) -> Dict[str, Any]:
    """Get features from the OS data object"""
    if not collection_id:
        raise ValueError("collection_id is required")
    if not usrn:
        raise ValueError("usrn is required")
    os_data = OSDataObject()
    return os_data.get_collection_features(
        collection_id=collection_id,
        query_attr="usrn",
        query_attr_value=usrn
    )

def get_features_route(query_params: QueryParams):
    """API route to get features data"""
    try:
        collection_id = query_params.get('collection_id')
        usrn = query_params.get('usrn')

        if not collection_id:
            error_response = json.dumps({"error": "collection_id is required"})
            return {
                "status_code": 400,
                "headers": {"Content-Type": "application/json"},
                "description": "Bad Request",
                "data": error_response
            }

        if not usrn:
            error_response = json.dumps({"error": "usrn is required"})
            return {
                "status_code": 400,
                "headers": {"Content-Type": "application/json"},
                "description": "Bad Request",
                "data": error_response
            }

        # GET THE DATA
        features = get_features(collection_id=collection_id, usrn=usrn)
        return Response(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps(features)
                )

    except ValueError as ve:
        error_response = json.dumps({"error": str(ve)})
        return {
            "status_code": 400,
            "headers": {"Content-Type": "application/json"},
            "description": "Bad Request",
            "data": error_response
        }

    except Exception as e:
        error_response = json.dumps({"error": str(e)})
        return {
            "status_code": 500,
            "headers": {"Content-Type": "application/json"},
            "description": "Internal Server Error",
            "data": error_response
        }
