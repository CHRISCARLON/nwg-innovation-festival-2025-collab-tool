import os
from typing import Optional, Literal, Dict, Any
from urllib.parse import urlencode
from operator import itemgetter
from os_endpoints import NGDAPIEndpoint
from request_functions import fetch_data, fetch_data_auth
import asyncio

# TODO add better more explicit error handling
class OSDataObject:
    """
    Returns an instance of the OSDataObject class which can be used to interact with the OS NGD API.
    """
    def __init__(self) -> None:
        """Initialise with the API key"""
        self.api_key = os.getenv('OS_KEY')
        if not self.api_key:
            raise ValueError("An API key must be provided through the environment variable 'OS_KEY'")

    def get_all_collections(self) -> list[Any]:
        """ Get info on all available collections """
        endpoint: str = NGDAPIEndpoint.COLLECTIONS.value
        try:
            result = fetch_data(endpoint)
            output = list(map(itemgetter('title', 'id'), result['collections']))
            return output
        except Exception as e:
            raise e

    def get_collection(self, collection_id: str) -> dict[Any, Any]:
        """ Get info on a single collection """
        endpoint: str = NGDAPIEndpoint.COLLECTION_INFO.value.format(collection_id)
        try:
            result = fetch_data(endpoint)
            return result
        except Exception as e:
            raise e

    def get_collection_schema(self, collection_id: str) -> dict[Any, Any]:
        """ Get the schema of a single collection """
        endpoint: str = NGDAPIEndpoint.COLLECTION_SCHEMA.value.format(collection_id)
        try:
            result = fetch_data(endpoint)
            return result
        except Exception as e:
            raise e

    def get_collection_queryables(self, collection_id: str) -> dict[Any, Any]:
        """ 
        Get the queryables of a single collection 
        
        This will tell you what you can filter by (the possible query parameters) - e.g. USRN, OSID, TOID, etc
        """
        endpoint: str = NGDAPIEndpoint.COLLECTION_QUERYABLES.value.format(collection_id)
        try:
            result = fetch_data(endpoint)
            return result
        except Exception as e:
            raise e

    async def get_single_collection_features(
            self,
            collection_id: str,
            feature_id: Optional[str] = None,
            query_attr: Optional[Literal["usrn", "toid"]] = None,
            query_attr_value: Optional[str] = None,
            bbox: Optional[str] = None,
            bbox_crs: Optional[str] = None,
            crs: Optional[str] = None
        ) -> dict[Any, Any]:
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

            if feature_id:
                endpoint: str = NGDAPIEndpoint.COLLECTION_FEATURE_BY_ID.value.format(collection_id, feature_id)
            else:
                endpoint: str = NGDAPIEndpoint.COLLECTION_FEATURES.value.format(collection_id)

            # Build query parameters
            query_params: Dict[str, Any] = {}

            # Add USRN filter if provided
            if query_attr and query_attr_value:
                query_params['filter'] = f"{query_attr}={query_attr_value}"

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
                result = await fetch_data_auth(endpoint)
                return result
            except Exception as e:
                raise e

    async def get_bulk_collection_features(self, feature_ids: list[str], collection_id: str) -> list[dict[str, Any]]:
        """ 
        Get features by their feature IDs.

        This is useful for joining features together.

        For example all USRNs have a set of road links associated with them.

        If you have a list of USRNs you can use this function to get the road links for each USRN and join them together.
        
        Args:
            filter_ids: list[str] - The feature IDs
            collection_id: str - The collection ID

        Returns:
            Dictionary containing the USRN info and all associated road links
        """
        try: 
            feature_id_tasks = [
                self.get_single_collection_features(
                    collection_id, 
                    feature_id=feature_id
                ) 
                for feature_id in feature_ids
            ]
                
            feature_results = await asyncio.gather(*feature_id_tasks)

            return feature_results
        except Exception as e:
            raise e

    async def get_linked_features_identifier(
        self, 
        identifier_type: Literal[
            "TOID",
            "USRN",
            "UPRN"
        ], 
        identifier_value: str
    ) -> dict[str, Any]:
        """
        Get linked features for a given feature type and feature ID

        Args:
            identifier_type: Literal[
                "TOID",
                "USRN",
                "UPRN"
            ]
            identifier_value: str
        """
        endpoint: str = NGDAPIEndpoint.LINKED_IDENTIFIERS.value.format(identifier_type, identifier_value)
        print(endpoint)
        try:
            result = await fetch_data_auth(endpoint)
            return result
        except Exception as e:
            raise e
