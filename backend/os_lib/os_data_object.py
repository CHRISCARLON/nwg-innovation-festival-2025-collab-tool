import os
from typing import Optional, Literal, Dict, Any, Union
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

    async def get_single_collection_feature(
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

    async def get_bulk_collection_feature(
        self, 
        identifiers: Union[list[str], dict[str, Any]], 
        collection_id: str,
        query_by_attr: Optional[Literal["usrn", "toid"]] = None
    ) -> list[dict[str, Any]]:
        """ 
        Get features by their feature IDs or by query attributes.

        This is useful for joining features together.

        For example all USRNs have a set of road links associated with them.

        If you have a list of USRNs you can use this function to get the road links for each USRN and join them together.
        
        Args:
            identifiers: Union[list[str], dict[str, Any]] - A list of feature IDs or attribute values (USRNs, TOIDs)
            collection_id: str - The collection ID
            query_by_attr: Optional[Literal["usrn", "toid"]] - If provided, query by this attribute instead of feature ID

        Returns:
            List of dictionaries containing the requested features
        """
        try: 
            id_list = identifiers if isinstance(identifiers, list) else []
            
            if query_by_attr:
                feature_id_tasks = [
                    self.get_single_collection_feature(
                        collection_id, 
                        query_attr=query_by_attr,
                        query_attr_value=identifier
                    ) 
                    for identifier in id_list
                ]
            else:
                feature_id_tasks = [
                    self.get_single_collection_feature(
                        collection_id, 
                        feature_id=identifier
                    ) 
                    for identifier in id_list
                ]
                
            feature_results = await asyncio.gather(*feature_id_tasks)

            return feature_results
        except Exception as e:
            raise e

    async def get_single_linked_features(
        self, 
        identifier_type: Literal[
            "TOID",
            "USRN",
            "UPRN"
        ], 
        identifier_value: str,
        feature_type: Optional[Literal[
            "RoadLink",
            "TopographicArea", 
            "BLPU",
            "Road",
            "Street"
        ]] = None
    ) -> Union[list[str], dict]:
        """
        Get linked features for a given feature type and feature ID
        If feature_type is provided, returns a list of identifiers for that feature type
        If feature_type is None, returns the raw correlation data

        Args:
            identifier_type: Literal[
                "TOID",
                "USRN",
                "UPRN"
            ]
            identifier_value: str
            feature_type: Optional feature type to filter by, if None returns raw data
        """
        endpoint: str = NGDAPIEndpoint.LINKED_IDENTIFIERS.value.format(identifier_type, identifier_value)
        
        try:
            result = await fetch_data_auth(endpoint)
            
            # If no feature_type is provided, return the raw result
            if feature_type is None:
                return result
            
            identifiers = []

            if 'correlations' in result and isinstance(result['correlations'], list):
                # Find the dictionary with correlatedFeatureType matching the specified feature_type
                for item in result['correlations']:
                    if item.get('correlatedFeatureType') == feature_type:
                        # Extract all identifiers from the correlatedIdentifiers list
                        if 'correlatedIdentifiers' in item and isinstance(item['correlatedIdentifiers'], list):
                            identifiers = [
                                id_obj['identifier'] 
                                for id_obj in item['correlatedIdentifiers']
                                if isinstance(id_obj, dict) and 'identifier' in id_obj
                            ]
                            break

            return identifiers
        except Exception as e:
            raise e
        
    async def get_bulk_linked_features(
        self, 
        identifier_type: Literal[
            "TOID",
            "USRN",
            "UPRN"
        ], 
        identifier_values: Union[list[str], dict[str, Any]],
        feature_type: Optional[Literal[
            "RoadLink",
            "TopographicArea", 
            "BLPU",
            "Road", 
            "Street"
        ]] = None
    ) -> list[Union[list[str], dict[str, Any]]]:
        """
        Get bulk linked features for a set of identifier values

        Args:
            identifier_type: Literal[
                "TOID",
                "USRN",
                "UPRN"
            ]
            identifier_values: Union[list[str], dict[str, Any]] - Either a list of identifiers or a raw correlation result
            feature_type: Optional feature type to filter by, if None returns raw data

        Returns:
            List of either lists of identifiers or raw correlation data dictionaries
        """
        try:
            identifier_tasks = [
                self.get_single_linked_features(
                    identifier_type, 
                    identifier_value, 
                    feature_type
                ) 
                for identifier_value in identifier_values
            ]   

            identifier_results = await asyncio.gather(*identifier_tasks)

            return identifier_results
        except Exception as e:
            raise e
