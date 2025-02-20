import json
from enum import Enum
from robyn import Response
from ..interfaces.interfaces import OSFeatures, BBOXGeometry, LLMSummary, StreetManagerStats
from robyn.robyn import Request

class RouteType(Enum):
    """
    Enum for the different route types
    """
    STREET_INFO = "street-info"
    LAND_USE = "land-use"
    COLLABORATIVE_STREET_WORKS = "collaborative-street-works"

class FeatureRouteHandler:
    """
    Route handler for the feature routes

    This class is used to handle the routes for the Rapid Street Assessments (RSAs).
    """
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
        """
        Get street info only
        """
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
            simplified_features = await self.llm_summary_service.pre_process_street_info(features)

            return Response(
                status_code=200,
                headers={"Content-Type": "application/json"},
                description=json.dumps(simplified_features)
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
        """
        Get street info with llm summary
        """
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
            simplified_features = await self.llm_summary_service.pre_process_street_info(features)
            llm_summary = await self.llm_summary_service.summarize_results(simplified_features, path_type)

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
        """
        Get land use only
        """
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

            simplified_features = await self.llm_summary_service.pre_process_land_use_info(features)

            return Response(
                status_code=200,
                headers={"Content-Type": "application/json"},
                description=json.dumps(simplified_features)
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
        """
        Get land use with llm summary
        """
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

            simplified_features = await self.llm_summary_service.pre_process_land_use_info(features)

            llm_summary = await self.llm_summary_service.summarize_results(simplified_features, path_type)

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

    async def get_collaborative_street_works_route(self,request: Request) -> Response:
        """
        Get collaborative street works recommendation
        """
        try:
            usrn = request.query_params.get('usrn')
            if not usrn:
                raise ValueError("Missing required parameter: usrn")

            path_type_land = RouteType.LAND_USE.value
            path_type_street = RouteType.STREET_INFO.value
            path_type_collab = RouteType.COLLABORATIVE_STREET_WORKS.value

            # Get bbox from USRN
            minx, miny, maxx, maxy = await self.geometry_service.get_bbox_from_usrn(usrn)
            bbox = f"{minx},{miny},{maxx},{maxy}"
            crs = "http://www.opengis.net/def/crs/EPSG/0/27700"
            bbox_crs = "http://www.opengis.net/def/crs/EPSG/0/27700"

            # LAND
            features_land = await self.feature_service.get_features(
                path_type=path_type_land,
                usrn=usrn,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs
            )
            simplified_features_land = await self.llm_summary_service.pre_process_land_use_info(features_land)

            # STREET
            street_manager_stats = await self.street_manager_service.get_street_manager_stats(usrn)
            features_street = await self.feature_service.get_features(
                path_type=path_type_street,
                usrn=usrn,
                bbox=bbox,
                bbox_crs=bbox_crs,
                crs=crs
            )
            features_street['street_manager_stats'] = street_manager_stats
            simplified_features_street = await self.llm_summary_service.pre_process_street_info(features_street)

            # COMBINE
            combined_features = {
                "land_use": simplified_features_land,
                "street_info": simplified_features_street
            }

            # LLM
            llm_summary = await self.llm_summary_service.summarize_results(combined_features, path_type_collab)

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