from ..interfaces.interfaces import (
    OSFeatures,
    BBOXGeometry,
    LLMSummary,
    StreetManagerStats,
    NUARAssetStats,
)
from ..processors.bbox.bbox_processor import get_bbox_from_usrn
from ..processors.features.feature_processor import process_single_collection
from ..processors.langchain.langchain_processor import process_with_langchain
from ..processors.langchain.langchain_pre_processor import (
    langchain_pre_process_street_info,
    langchain_pre_process_land_use_info,
)
from ..processors.street_manager.street_manager_processor import (
    street_manager_processor,
)
from ..processors.nuar.nuar_processor import get_nuar_asset_count
from typing import Dict, Any, Optional


class OSFeatureService(OSFeatures):
    async def get_features(
        self,
        path_type: str,
        usrn: Optional[str] = None,
        bbox: Optional[str] = None,
        bbox_crs: Optional[str] = None,
        crs: Optional[str] = None,
    ) -> Dict[str, Any]:
        if usrn is None or bbox is None or bbox_crs is None or crs is None:
            raise ValueError("All parameters must be provided")

        return await process_single_collection(
            path_type=path_type, usrn=usrn, bbox=bbox, bbox_crs=bbox_crs, crs=crs
        )


class LangChainSummaryService(LLMSummary):
    async def pre_process_street_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await langchain_pre_process_street_info(data)

    async def pre_process_land_use_info(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return await langchain_pre_process_land_use_info(data)

    async def summarize_results(
        self, data: Dict[str, Any], route_type: str
    ) -> Dict[str, Any]:
        return await process_with_langchain(data, route_type)


class DataService(BBOXGeometry, StreetManagerStats, NUARAssetStats):
    async def get_bbox_from_usrn(self, usrn: str, buffer_distance: float = 50) -> tuple:
        return await get_bbox_from_usrn(usrn, buffer_distance)

    async def get_street_manager_stats(self, usrn: str) -> dict:
        processor = street_manager_processor()
        return await processor(usrn)

    async def get_asset_count(self, bbox: str) -> Dict[str, Any]:
        return await get_nuar_asset_count(bbox)
