from enum import Enum

class NGDAPIEndpoint(Enum):
    """
    Enum for the OS NGD API Endpoints

    Get information about the collections available and query available features
    """
    BASE_PATH = "https://api.os.uk/features/ngd/ofa/v1/{}"
    LINKED_BASE_PATH = "https://api.os.uk/search/links/v1/{}"
    COLLECTIONS = BASE_PATH.format("collections")
    COLLECTION_INFO = BASE_PATH.format("collections/{}")
    COLLECTION_SCHEMA = BASE_PATH.format("collections/{}/schema")
    COLLECTION_QUERYABLES = BASE_PATH.format("collections/{}/queryables")
    COLLECTION_FEATURES = BASE_PATH.format("collections/{}/items")
    COLLECTION_FEATURE_BY_ID = BASE_PATH.format("collections/{}/items/{}")
    LINKED_IDENTIFIERS = LINKED_BASE_PATH.format("identifierTypes/{}/{}")

