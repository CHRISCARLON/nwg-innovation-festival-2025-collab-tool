import json
from enum import Enum
from robyn import Response
from ..interfaces.interfaces import OSFeatures, BBOXGeometry, LLMSummary, StreetManagerStats
from robyn.robyn import Request

class RouteType(Enum):
    STREET_INFO = "street-info"
    LAND_USE = "land-use"

class FeatureRouteHandler:
    def __init__(
        self,
        feature_service: OSFeatures,
        geometry_service: BBOXGeometry,
        street_manager_service: StreetManagerStats,
        llm_summary_service: LLMSummary
    ):
        self.feature_service = feature_service
        self.geometry_service = geometry_service
        self.street_manager_service = street_manager_service
        self.llm_summary_service = llm_summary_service

    async def get_street_info_route(self, request: Request) -> Response:
        try:
            usrn = request.query_params.get('usrn')
            if not usrn:
                raise ValueError("Missing required parameter: usrn")
            
            path_type = RouteType.STREET_INFO.value

            # Get bbox from USRN
            minx, miny, maxx, maxy = await self.geometry_service.get_bbox_from_usrn(usrn)
            bbox = f"{minx},{miny},{maxx},{maxy}"
            crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
            bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

            # Get street manager stats
            street_manager_stats = await self.street_manager_service.get_street_manager_stats(usrn)

            # Process features
            features = await self.feature_service.get_features(
                path_type=path_type,
                usrn=usrn,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs
            )

            features['street_manager_stats'] = street_manager_stats

            return Response(
                status_code=200,
                headers={"Content-Type": "application/json"},
                description=json.dumps(features)
            )

        except ValueError as ve:
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(ve)})
            )
        except Exception as e:
            return Response(
                status_code=500,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(e)})
            )

    async def get_street_info_route_llm(self,request: Request) -> Response:
        try:
            usrn = request.query_params.get('usrn')
            if not usrn:
                raise ValueError("Missing required parameter: usrn")

            path_type = RouteType.STREET_INFO.value

            # Get bbox from USRN
            minx, miny, maxx, maxy = await self.geometry_service.get_bbox_from_usrn(usrn)
            bbox = f"{minx},{miny},{maxx},{maxy}"
            crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
            bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

            # Get street manager stats
            street_manager_stats = await self.street_manager_service.get_street_manager_stats(usrn)

            # Process features
            features = await self.feature_service.get_features(
                path_type=path_type,
                usrn=usrn,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs
            )

            features['street_manager_stats'] = street_manager_stats

            llm_summary = await self.llm_summary_service.summarize_results(features, path_type)

            return Response(
                status_code=200,
                headers={"Content-Type": "application/json"},
                description=json.dumps(llm_summary)
            )

        except ValueError as ve:
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(ve)})
            )
        except Exception as e:
            return Response(
                status_code=500,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(e)})
            )

    async def get_land_use_route(self,request: Request) -> Response:
            try:
                usrn = request.query_params.get('usrn')
                if not usrn:
                    raise ValueError("Missing required parameter: usrn")
                
                path_type = RouteType.LAND_USE.value

                # Get bbox from USRN
                minx, miny, maxx, maxy = await self.geometry_service.get_bbox_from_usrn(usrn)
                bbox = f"{minx},{miny},{maxx},{maxy}"
                crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
                bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

                # Process features
                features = await self.feature_service.get_features(
                    path_type=path_type,
                    usrn=usrn,
                    bbox=bbox,
                    bbox_crs=bbox_crs,
                    crs=crs
                )

                return Response(
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps(features)
                )

            except ValueError as ve:
                return Response(
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps({"error": str(ve)})
                )
            except Exception as e:
                return Response(
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                    description=json.dumps({"error": str(e)})
                )

    async def get_land_use_route_llm(self,request: Request) -> Response:
        try:
            usrn = request.query_params.get('usrn')
            if not usrn:
                raise ValueError("Missing required parameter: usrn")

            path_type = RouteType.LAND_USE.value

            # Get bbox from USRN
            minx, miny, maxx, maxy = await self.geometry_service.get_bbox_from_usrn(usrn)
            bbox = f"{minx},{miny},{maxx},{maxy}"
            crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
            bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

            # Process features
            features = await self.feature_service.get_features(
                path_type=path_type,
                usrn=usrn,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs
            )

            llm_summary = await self.llm_summary_service.summarize_results(features, path_type)

            return Response(
                status_code=200,
                headers={"Content-Type": "application/json"},
                description=json.dumps(llm_summary)
            )

        except ValueError as ve:
            return Response(
                status_code=400,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(ve)})
            )
        except Exception as e:
            return Response(
                status_code=500,
                headers={"Content-Type": "application/json"},
                description=json.dumps({"error": str(e)})
            )