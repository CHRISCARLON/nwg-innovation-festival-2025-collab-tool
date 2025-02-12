from robyn import Request, jsonify
from robyn.robyn import QueryParams
from os_lib.os_data_object import OSDataObject
from typing import Dict, Any, List

def get_all_collections() -> List[str]:
    """Get collections from the OS data object"""
    os_data = OSDataObject()
    return os_data.get_all_collections()

def get_all_collections_route():
    """API route to get collections data"""
    try:
        collections = get_all_collections()

        return {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "description": "OK",
            "data": collections
        }
    except ValueError as ve:
        return {
            "status_code": 400,
            "headers": {"Content-Type": "application/json"},
            "description": "Bad Request",
            "data": jsonify({"error": str(ve)})
        }
    except Exception as e:
        return {
            "status_code": 500,
            "headers": {"Content-Type": "application/json"},
            "description": "Internal Server Error",
            "data": jsonify({"error": str(e)})
        }
