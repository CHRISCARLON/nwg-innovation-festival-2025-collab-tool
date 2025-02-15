from abc import ABC, abstractmethod
from typing import Dict, Any

class OSFeatures(ABC):
    @abstractmethod
    async def get_features(
        self, 
        path_type: str,
        usrn: str,
        bbox: str,
        bbox_crs: str,
        crs: str
    ) -> Dict[str, Any]:
        pass

class LLMSummary(ABC):
    @abstractmethod
    async def summarize_results(self, data: Dict[str, Any], route_type: str) -> Dict[str, Any]:
        pass

class BBOXGeometry(ABC):
    @abstractmethod
    async def get_bbox_from_usrn(self, usrn: str, buffer_distance: float = 50) -> tuple:
        pass