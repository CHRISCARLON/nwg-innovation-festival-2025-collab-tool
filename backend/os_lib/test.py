from os_data_object import OSDataObject
from pprint import pprint
import asyncio

def get_roadlink_ids(street_data):
    roadlink_ids = []
    
    if 'properties' in street_data and 'roadlinkreference' in street_data['properties']:
        roadlink_references = street_data['properties']['roadlinkreference']
        
        for ref in roadlink_references:
            if 'roadlinkid' in ref:
                roadlink_ids.append(ref['roadlinkid'])
    
    return roadlink_ids

def get_roadnode_ids(roadlink_data):
    roadnode_ids = []
    
    if isinstance(roadlink_data, list):
        for feature in roadlink_data:
            if 'properties' in feature:
                if 'endnode' in feature['properties']:
                    roadnode_ids.append(feature['properties']['endnode'])
                if 'startnode' in feature['properties']:
                    roadnode_ids.append(feature['properties']['startnode'])

    elif isinstance(roadlink_data, dict):
        if 'properties' in roadlink_data:
            if 'endnode' in roadlink_data['properties']:
                roadnode_ids.append(roadlink_data['properties']['endnode'])
            if 'startnode' in roadlink_data['properties']:
                roadnode_ids.append(roadlink_data['properties']['startnode'])
    
    unique_nodes = []
    for node in roadnode_ids:
        if node not in unique_nodes:
            unique_nodes.append(node)
    
    return unique_nodes


# Quickly test the OSDataObject
# TODO do a proper Pytest module
async def main():
    os_object = OSDataObject()
    test_usrn = await os_object.get_single_collection_feature("trn-ntwk-street-1", "23012059")
    pprint(test_usrn)

    roadlink_ids = get_roadlink_ids(test_usrn)
    pprint(roadlink_ids)

    test_roadlink_bulk = await os_object.get_bulk_collection_feature(collection_id="trn-ntwk-roadlink-1", identifiers=roadlink_ids)
    pprint(test_roadlink_bulk)

    roadnode_ids = get_roadnode_ids(test_roadlink_bulk)
    pprint(roadnode_ids)

    test_roadnode_bulk = await os_object.get_bulk_collection_feature(collection_id="trn-ntwk-roadnode-1", identifiers=roadnode_ids)
    pprint(test_roadnode_bulk)

if __name__ == "__main__":
    asyncio.run(main())
