from os_lib.os_data_object import OSDataObject
from os_lib.os_ngd_features import OSNGDCollections
from typing import Dict, Any, Optional

async def process_features(
    collection_id: str,
    usrn: Optional[str] = None,
    bbox: Optional[str] = None,
    bbox_crs: Optional[str] = None,
    crs: Optional[str] = None
) -> Dict[str, Any]:
    """Get features from the OS data object with support for both RAMI and LUS collections"""
    if not collection_id:
        raise ValueError("A valid collection_id is required")

    # Create a OS data object to call methods
    os_data = OSDataObject()

    match collection_id:
        # For RAMI and NTWK collections that require USRN
        # Street info route
        case _ if collection_id in (OSNGDCollections.RAMI.value + OSNGDCollections.NTWK.value):
            if not usrn:
                raise ValueError("A valid usrn is required for the RAMI and NTWK collections")
            return await os_data.get_collection_features(
                collection_id=collection_id,
                usrn_attr="usrn",
                usrn_attr_value=usrn
            )
        
        # For LUS and BLD collections that require USRN
        # Land use route
        case _ if collection_id in (OSNGDCollections.LUS.value + OSNGDCollections.BLD.value):
            if not usrn:
                raise ValueError("A valid usrn is required for the LUS and BLD collections")
            
            return await os_data.get_collection_features(
                collection_id=collection_id,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs
            )

    raise ValueError(f"Unsupported collection_id: {collection_id}")