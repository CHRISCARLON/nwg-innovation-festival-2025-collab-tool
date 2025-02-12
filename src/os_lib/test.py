from os_data_object import OSDataObject
from pprint import pprint

if __name__ == "__main__":
    os_object = OSDataObject()
    test = os_object.get_collection_features("trn-rami-specialdesignationline-1", "usrn", "8100239")
    pprint(test)
