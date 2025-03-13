from os_data_object import OSDataObject
from pprint import pprint
import asyncio

# Quickly test the OSDataObject
# TODO do a proper Pytest module
async def main():
    os_object = OSDataObject()
    test = await os_object.get_usrn_road_links("7001592")
    pprint(test)

if __name__ == "__main__":
    asyncio.run(main())
