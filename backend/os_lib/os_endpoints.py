from enum import Enum

class NGDFeaturesAPIEndpoint(Enum):
    BASE_PATH = "https://api.os.uk/features/ngd/ofa/v1/{}"
    COLLECTIONS = BASE_PATH.format("collections")
    COLLECTION_INFO = BASE_PATH.format("collections/{}")
    COLLECTION_SCHEMA = BASE_PATH.format("collections/{}/schema")
    COLLECTION_QUERYABLES = BASE_PATH.format("collections/{}/queryables")
    COLLECTION_FEATURES = BASE_PATH.format("collections/{}/items")
