import os

from operator import itemgetter
from typing import Optional, Literal
from os_endpoints import NGDFeaturesAPIEndpoint
from helper_functions import fetch_data, fetch_data_auth

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
        query_attr: Optional[Literal["usrn"]] = None,
        query_attr_value: Optional[str] = None
    ):
        """
        Fetches collection features with optional USRN filter
        Args:
            collection_id: str - The ID of the collection
            query_attr: Optional[Literal["usrn"]] - Optional query attribute (only "usrn" allowed at the moment)
            query_attr_value: Optional[str] - Value for the query attribute (e.g. USRN number)
        Returns:
            API response with collection features
        """
        endpoint: str = NGDFeaturesAPIEndpoint.COLLECTION_FEATURES.value.format(collection_id)

        if query_attr and query_attr_value:
            endpoint = f"{endpoint}?filter={query_attr}%3D{query_attr_value}"

        try:
            result = fetch_data_auth(endpoint)
            return result
        except Exception:
            raise
