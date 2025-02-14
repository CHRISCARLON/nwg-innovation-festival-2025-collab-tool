from robyn_lib.utils.utils import get_bbox_from_usrn
from os_lib.os_data_object import OSDataObject
from os_lib.os_ngd_features import NGDFeaturesAPI
from typing import Dict, Any, Optional

def process_features(
    collection_id: str,
    usrn: Optional[str] = None,
    bbox: Optional[str] = None,
    bbox_crs: Optional[str] = None,
    crs: Optional[str] = None,
    buffer_distance: float = 50
) -> Dict[str, Any]:
    """Get features from the OS data object with support for both RAMI and LUS collections"""
    if not collection_id:
        raise ValueError("A valid collection_id is required")

    # Create a OS data object to call methods
    os_data = OSDataObject()

    match collection_id:
        # For RAMI collections that require USRN
        case _ if collection_id in NGDFeaturesAPI.RAMI.value:
            if not usrn:
                raise ValueError("A valid usrn is required for the RAMI collections")
            return os_data.get_collection_features(
                collection_id=collection_id,
                usrn_attr="usrn",
                usrn_attr_value=usrn
            )

        # For LUS collections that support both USRN-derived bbox and direct bbox
        case _ if collection_id in NGDFeaturesAPI.LUS.value:
            # If USRN is provided, generate a bbox from it
            if usrn:
                try:
                    minx, miny, maxx, maxy = get_bbox_from_usrn(usrn, buffer_distance)
                    bbox = f"{minx},{miny},{maxx},{maxy}"
                    bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
                    crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
                except Exception as e:
                    raise ValueError(f"Failed to get bbox from USRN: {str(e)}")

            # Verify bbox parameters
            if not all([bbox, bbox_crs, crs]):
                raise ValueError("A bbox, bbox-crs, and crs are required for the LUS collections")

            return os_data.get_collection_features(
                collection_id=collection_id,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs
            )

    raise ValueError(f"Unsupported collection_id: {collection_id}")