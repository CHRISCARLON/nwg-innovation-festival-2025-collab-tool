import json
import requests

from loguru import logger

from robyn import Response
from robyn.robyn import QueryParams

from os_lib.os_ngd_features import NGDFeaturesAPI

from robyn_lib.utils.process_features import process_features
from robyn_lib.utils.utils import filter_feature_properties

def get_rami_route(query_params: QueryParams) -> Response:
    """API route to get features data with support for both RAMI and LUS collections"""
    collection_id = query_params.get('collection_id')
    
    if not collection_id:
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": "A valid collection_id is required"}),
        )

    if collection_id not in NGDFeaturesAPI.RAMI.value:
        return Response(
            status_code=400,
            headers={"Content-Type": "application/json"},
            description=json.dumps({"error": "The collection_id is not valid - it must be one of the following: " + str(NGDFeaturesAPI.RAMI.value)}),
        )
    try:
        # Pass in usrn query param
        usrn = query_params.get('usrn')

        try:
            features = process_features(
                collection_id=collection_id,
                usrn=usrn
            )

            # Filter the response to remove the geometry attribute and only keep key properties
            # This is done to reduce the size of the response and improve readability
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

        # Capture any HTTP errors from the OS data object
        # These will be handled by the App Logger in app.py
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