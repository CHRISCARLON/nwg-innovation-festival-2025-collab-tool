from os_data_object import OSDataObject

# Quickly test the OSDataObject
# TODO do a proper Pytest module
if __name__ == "__main__":
    os_object = OSDataObject()
    test = os_object.get_collection_features("trn-rami-specialdesignationline-1", "usrn", "8100239")
    print(type(test))
