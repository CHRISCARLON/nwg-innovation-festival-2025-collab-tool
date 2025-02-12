from robyn import Response
from robyn.robyn import QueryParams
from os_lib.os_data_object import OSDataObject
from os_lib.os_ngd_features import NGDFeaturesAPI
from typing import Dict, Any, Optional
import json
import requests
import os
import duckdb
from shapely.wkt import loads
from loguru import logger

def connect_to_motherduck() -> duckdb.DuckDBPyConnection:
    """Create a database connection object to MotherDuck"""
    database = os.getenv('MD_DB')
    token = os.getenv('MD_TOKEN')
    if token is None:
        raise ValueError("MotherDuck token not present in environment variables")

    connection_string = f'md:{database}?motherduck_token={token}'
    try:
        con = duckdb.connect(connection_string)
        return con
    except Exception as e:
        logger.warning(f"MotherDuck connection error: {e}")
        raise

def get_bbox_from_usrn(usrn: str, buffer_distance: float = 50) -> tuple:
    """Get bounding box coordinates for a given USRN

    Args:
        usrn: Street reference number
        buffer_distance: Buffer distance in meters

    Returns:
        tuple: (minx, miny, maxx, maxy) coordinates
    """
    try:
        con = connect_to_motherduck()
        schema = os.getenv('SCHEMA')
        table_name = os.getenv('TABLE')

        query = f"""
        SELECT geometry
        FROM {schema}.{table_name}
        WHERE usrn = ?
        """

        result = con.execute(query, [usrn])
        df = result.fetchdf()

        if df.empty:
            logger.warning(f"No geometry found for USRN: {usrn}")
            raise ValueError(f"No geometry found for USRN: {usrn}")

        geom = loads(df['geometry'].iloc[0])
        buffered = geom.buffer(buffer_distance)
        return tuple(round(coord) for coord in buffered.bounds)

    except Exception as e:
        logger.error(f"Error getting bbox from USRN: {e}")
        raise

def filter_feature_properties(feature: dict, collection_id: str) -> dict:
    """Extract key information from a feature based on collection type"""

    # Base properties that exist in both schemas
    essential_props = {
        'id': feature['id'],
        'properties': {
            'description': feature['properties'].get('description'),
        }
    }

    # For RAMI Special Designation collections
    if collection_id in NGDFeaturesAPI.RAMI.value:
        essential_props['properties'].update({
            'usrn': feature['properties'].get('usrn'),
            'designation': feature['properties'].get('designation'),
            'designationdescription': feature['properties'].get('designationdescription'),
            'effectivestartdate': feature['properties'].get('effectivestartdate'),
            'effectiveenddate': feature['properties'].get('effectiveenddate'),
            'timeinterval': feature['properties'].get('timeinterval'),
            'geometry_length': feature['properties'].get('geometry_length'),
            'authorityid': feature['properties'].get('authorityid'),
            'contactauthority_authorityname': feature['properties'].get('contactauthority_authorityname')
        })

    # For LUS collections
    elif collection_id in NGDFeaturesAPI.LUS.value:
        essential_props['properties'].update({
            'name1_text': feature['properties'].get('name1_text'),
            'name2_text': feature['properties'].get('name2_text'),
            'oslandusetiera': feature['properties'].get('oslandusetiera'),
            'oslandusetierb': feature['properties'].get('oslandusetierb', []),
            'primaryuprn': feature['properties'].get('primaryuprn'),
            'geometry_area': feature['properties'].get('geometry_area')
        })

    return essential_props

def get_features(
    collection_id: str,
    usrn: Optional[str] = None,
    bbox: Optional[str] = None,
    bbox_crs: Optional[str] = None,
    crs: Optional[str] = None,
    buffer_distance: float = 50
) -> Dict[str, Any]:
    """Get features from the OS data object with support for both RAMI and LUS collections"""
    if not collection_id:
        raise ValueError("collection_id is required")

    os_data = OSDataObject()

    # For RAMI collections that require USRN
    if collection_id in NGDFeaturesAPI.RAMI.value:
        if not usrn:
            raise ValueError("usrn is required for RAMI collections")
        return os_data.get_collection_features(
            collection_id=collection_id,
            usrn_attr="usrn",
            usrn_attr_value=usrn
        )

    # For LUS collections that support both USRN-derived bbox and direct bbox
    elif collection_id in NGDFeaturesAPI.LUS.value:
        # If USRN is provided, get bbox from it
        if usrn:
            try:
                minx, miny, maxx, maxy = get_bbox_from_usrn(usrn, buffer_distance)
                bbox = f"{minx},{miny},{maxx},{maxy}"
                bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
                crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
            except Exception as e:
                raise ValueError(f"Failed to get bbox from USRN: {str(e)}")

        # Verify bbox parameters
        if not all([bbox, bbox_crs, crs]):
            raise ValueError("bbox, bbox-crs, and crs are required for LUS collections")

        return os_data.get_collection_features(
            collection_id=collection_id,
            bbox=bbox,
            bbox_crs=bbox_crs,
            crs=crs
        )

    raise ValueError(f"Unsupported collection_id: {collection_id}")

def get_features_route(query_params: QueryParams) -> Response:
    """API route to get features data with support for both RAMI and LUS collections"""
    try:
        collection_id = query_params.get('collection_id')
        if not collection_id:
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": "collection_id is required"}),
            )

        usrn = query_params.get('usrn')
        bbox = query_params.get('bbox')
        bbox_crs = query_params.get('bbox-crs')
        crs = query_params.get('crs')

        try:
            features = get_features(
                collection_id=collection_id,
                usrn=usrn,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs,
            )

            # Filter the response to remove geometry
            filtered_response = {
                            'type': features['type'],
                            'numberReturned': features['numberReturned'],
                            'timeStamp': features['timeStamp'],
                            'features': [filter_feature_properties(feature, collection_id)
                                       for feature in features['features']]
                        }

            return Response(
                status_code=200,
                headers={"Content-Type": "application/json"},
                description=json.dumps(filtered_response),
            )

        except requests.exceptions.HTTPError as http_err:
            return Response(
                status_code=http_err.response.status_code if http_err.response else 500,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(http_err)}),
            )

    except ValueError as ve:
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(ve)}),
        )
    except Exception as e:
        return Response(
            status_code=500,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": str(e)}),
        )
