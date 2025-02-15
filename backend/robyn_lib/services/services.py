from ..interfaces.interfaces import OSFeatures, BBOXGeometry, LLMSummary
from ..processors.bbox_processor import get_bbox_from_usrn
from ..processors.feature_processor import process_features
from ..processors.langchain_processor import process_with_langchain
from typing import Dict, Any, Optional

class OSFeatureService(OSFeatures):
    async def get_features(
        self,
        path_type: str, 
        usrn: Optional[str] = None,
        bbox: Optional[str] = None,
        bbox_crs: Optional[str] = None,
        crs: Optional[str] = None
    ) -> Dict[str, Any]:
        return await process_features(
            path_type=path_type,
            usrn=usrn,
            bbox=bbox,
            bbox_crs=bbox_crs,
            crs=crs
        )
    
class LangChainSummaryService(LLMSummary):
    async def summarize_results(self, data: Dict[str, Any], route_type: str) -> Dict[str, Any]:
        return await process_with_langchain(data, route_type)

class BBOXGeometryService(BBOXGeometry):
    async def get_bbox_from_usrn(self, usrn: str, buffer_distance: float = 50) -> tuple:
        return await get_bbox_from_usrn(usrn, buffer_distance)