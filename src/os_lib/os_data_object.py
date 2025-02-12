import os

from typing import Optional, Literal, Dict, Any
from urllib.parse import urlencode
from operator import itemgetter

from .os_endpoints import NGDFeaturesAPIEndpoint
from .request_functions import fetch_data, fetch_data_auth


class OSDataObject:
    def __init__(self):
        """Initialise with API key"""
        self.api_key = os.getenv('OS_KEY')
        if not self.api_key:
            raise ValueError("API key must be provided through environment variable 'OS_KEY'")

    def get_all_collections(self):
        """ TBC """
        endpoint: str = NGDFeaturesAPIEndpoint.COLLECTIONS.value
        try:
            result = fetch_data(endpoint)
            output = list(map(itemgetter('title', 'id'), result['collections']))
            return output
        except Exception:
            raise

    def get_collection(self, collection_id: str):
        """ TBC """
        endpoint: str = NGDFeaturesAPIEndpoint.COLLECTION_INFO.value.format(collection_id)
        try:
            result = fetch_data(endpoint)
            return result
        except Exception:
            raise

    def get_collection_schema(self, collection_id: str):
        """ TBC """
        endpoint: str = NGDFeaturesAPIEndpoint.COLLECTION_SCHEMA.value.format(collection_id)
        try:
            result = fetch_data(endpoint)
            return result
        except Exception:
            raise

    def get_collection_queryables(self, collection_id: str):
        """ TBC """
        endpoint: str = NGDFeaturesAPIEndpoint.COLLECTION_QUERYABLES.value.format(collection_id)
        try:
            result = fetch_data(endpoint)
            return result
        except Exception:
            raise

    def get_collection_features(
            self,
            collection_id: str,
            usrn_attr: Optional[Literal["usrn"]] = None,
            usrn_attr_value: Optional[str] = None,
            bbox: Optional[str] = None,
            bbox_crs: Optional[str] = None,
            crs: Optional[str] = None
        ):
            """
            Fetches collection features with optional USRN filter or bbox parameters
            Args:
                collection_id: str - The ID of the collection
                query_attr: Optional[Literal["usrn"]] - Optional query attribute (only "usrn" allowed at the moment)
                query_attr_value: Optional[str] - Value for the query attribute (e.g. USRN number)
                bbox: Optional[str] - Bounding box parameter
                bbox_crs: Optional[str] - CRS for the bounding box
                crs: Optional[str] - CRS for the response
            Returns:
                API response with collection features
            """
            endpoint: str = NGDFeaturesAPIEndpoint.COLLECTION_FEATURES.value.format(collection_id)

            # Build query parameters
            query_params: Dict[str, Any] = {}

            # Add USRN filter if provided
            if usrn_attr and usrn_attr_value:
                query_params['filter'] = f"{usrn_attr}={usrn_attr_value}"

            # Add bbox parameters if provided
            if bbox:
                query_params['bbox'] = bbox
            if bbox_crs:
                query_params['bbox-crs'] = bbox_crs
            if crs:
                query_params['crs'] = crs

            # Append query parameters to endpoint if any exist
            if query_params:
                endpoint = f"{endpoint}?{urlencode(query_params)}"

            try:
                result = fetch_data_auth(endpoint)
                return result
            except Exception:
                raise
