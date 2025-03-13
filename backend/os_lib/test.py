from os_data_object import OSDataObject
from pprint import pprint
import asyncio

def extract_feature_identifiers(api_response, feature_type):
    """
    Extract all identifiers for a specified correlatedFeatureType
    from a response with a 'correlations' list
    
    Args:
        api_response: Dictionary containing a 'correlations' key with a list value
        feature_type: The correlatedFeatureType to search for (e.g., 'RoadLink', 'TopographicArea')
        
    Returns:
        list: All identifiers for the specified feature type
    """
    identifiers = []
    
    # Check if the response has a 'correlations' key
    if 'correlations' in api_response and isinstance(api_response['correlations'], list):
        # Find the dictionary with correlatedFeatureType matching the specified feature_type
        for item in api_response['correlations']:
            if item.get('correlatedFeatureType') == feature_type:
                # Extract all identifiers from the correlatedIdentifiers list
                if 'correlatedIdentifiers' in item and isinstance(item['correlatedIdentifiers'], list):
                    identifiers = [
                        id_obj['identifier'] 
                        for id_obj in item['correlatedIdentifiers']
                        if isinstance(id_obj, dict) and 'identifier' in id_obj
                    ]
                    break  # Stop once we've found and processed the feature entry
    
    return identifiers

# Example usage:
# api_response = {'correlations': [{'correlatedFeatureType': 'TopographicArea', ...}, 
#                                 {'correlatedFeatureType': 'RoadLink', ...}, ...]}
# roadlink_ids = extract_feature_identifiers(api_response, 'RoadLink')
# topographic_ids = extract_feature_identifiers(api_response, 'TopographicArea')

# Quickly test the OSDataObject
# TODO do a proper Pytest module
async def main():
    os_object = OSDataObject()
    test_usrn = await os_object.get_linked_features_identifier("USRN", "23012059")
    correlated_features = extract_feature_identifiers(test_usrn, 'RoadLink')
    pprint(correlated_features)


if __name__ == "__main__":
    asyncio.run(main())
