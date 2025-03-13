from os_data_object import OSDataObject
from pprint import pprint
import asyncio

# Quickly test the OSDataObject
# TODO do a proper Pytest module
async def main():
    os_object = OSDataObject()
    test_usrn = await os_object.get_single_collection_features("trn-ntwk-roadlink-1", feature_id="fe9309e3-e4f0-4496-aa67-45035765bfdd")
    pprint(test_usrn)

    



if __name__ == "__main__":
    asyncio.run(main())
