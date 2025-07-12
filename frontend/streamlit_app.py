import streamlit as st
from datetime import date
from typing import Optional
import requests  # Add this import
import pandas as pd
import duckdb
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from loguru import logger
from shapely.geometry import LineString, MultiLineString, Point, MultiPoint, Polygon
from typing import Union, List, cast
import math
import base64
import struct
from config import (
    SWACode,
    LocationType,
    SectorType,
    ActivityType,
    ProgrammeType,
    TTRORequired,
    PromoterOrganisation,
    InstallationMethod,
    get_enum_options,
)
import json
from pathlib import Path

# N3GB HEX GRID SYSTEM
# Constants for the n3gb hex grid system
GRID_EXTENTS = [0, 0, 750000, 1350000]
CELL_RADIUS = [
    1281249.9438829257,
    48304.58762201923,
    182509.65769514776,
    68979.50076169973,
    26069.67405498836,
    9849.595592375015,
    3719.867784388759,
    1399.497052515653,
    529.4301968468868,
    199.76319313961054,
    75.05553499465135,
    28.290163190291665,
    10.392304845413264,
    4.041451884327381,
    1.7320508075688774,
    0.5773502691896258,
]
CELL_WIDTHS = [
    2219190,
    83666,
    316116,
    119476,
    45154,
    17060,
    6443,
    2424,
    917,
    346,
    130,
    49,
    18,
    7,
    3,
    1,
]


def decode_hex_identifier(identifier):
    """Decode a hex grid identifier to get easting, northing, and zoom level"""
    # Add padding back if needed for base64 decoding
    padding = "=" * (-len(identifier) % 4)
    base64_str = identifier + padding

    # Decode the base64 string to binary
    binary_data = base64.urlsafe_b64decode(base64_str)

    # Unpack the binary data to get easting, northing, and zoom level
    easting_int, northing_int, zoom_level = struct.unpack(">QQB", binary_data)

    # Convert back to original easting and northing values
    easting = easting_int / 10000.0
    northing = northing_int / 10000.0

    return easting, northing, zoom_level


def create_hexagon(center_x, center_y, size):
    """Create a hexagon polygon centered at (center_x, center_y) with the given size"""
    points = [
        (
            center_x + size * math.cos(math.radians(angle)),
            center_y + size * math.sin(math.radians(angle)),
        )
        for angle in range(30, 390, 60)
    ]
    return Polygon(points)


def create_hex_grids_geodataframe(hex_ids_data):
    """Create a GeoDataFrame from hex grid IDs and asset counts"""
    if not hex_ids_data:
        return None

    hex_data = []

    for hex_info in hex_ids_data:
        grid_id = hex_info.get("grid_id")
        asset_count = hex_info.get("asset_count", 0)

        if grid_id:
            try:
                # Decode the hex identifier to get center coordinates and zoom level
                easting, northing, zoom_level = decode_hex_identifier(grid_id)

                # Create the hexagon polygon
                radius = (
                    CELL_RADIUS[zoom_level]
                    if zoom_level < len(CELL_RADIUS)
                    else CELL_RADIUS[-1]
                )
                hexagon = create_hexagon(easting, northing, radius)

                hex_data.append(
                    {
                        "grid_id": grid_id,
                        "easting": easting,
                        "northing": northing,
                        "zoom_level": zoom_level,
                        "asset_count": asset_count,
                        "geometry": hexagon,
                    }
                )

            except Exception as e:
                logger.warning(f"Error decoding hex grid ID {grid_id}: {e}")
                continue

    if not hex_data:
        return None

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(hex_data, crs="EPSG:27700")  # type: ignore

    # Convert to WGS84 (EPSG:4326) for display
    gdf = gdf.to_crs(epsg=4326)

    return gdf


# FETCH STREET INFO
def fetch_street_info(usrn: str):
    """Fetch street info from the backend API"""
    try:
        response = requests.get(f"http://localhost:8080/street-info?usrn={usrn}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching street info: {e}")
        return None


def fetch_bgs_corrosivity():
    """Fetch BGS corrosivity data from local JSON file"""
    try:
        current_dir = Path(__file__).parent
        bgs_file_path = current_dir / "bgs.json"

        if not bgs_file_path.exists():
            logger.warning(f"BGS JSON file not found at: {bgs_file_path}")
            st.warning("BGS corrosivity data file not found")
            return None

        logger.info(f"Loading BGS corrosivity data from local file: {bgs_file_path}")

        with open(bgs_file_path, "r", encoding="utf-8") as file:
            bgs_data = json.load(file)

        if not isinstance(bgs_data, dict) or "features" not in bgs_data:
            logger.error("Invalid BGS data structure - missing 'features' key")
            st.error("Invalid BGS corrosivity data format")
            return None

        features_count = len(bgs_data.get("features", []))
        logger.info(
            f"Successfully loaded BGS data with {features_count} features from local file"
        )

        return bgs_data

    except json.JSONDecodeError as e:
        logger.error(f"Error parsing BGS JSON file: {e}")
        st.error("Error reading BGS corrosivity data file - invalid JSON format")
        return None
    except FileNotFoundError:
        logger.error("BGS JSON file not found")
        st.warning("BGS corrosivity data file not found")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading BGS data: {e}")
        st.error(f"Error loading BGS corrosivity data: {e}")
        return None


def fetch_bgs_corrosivity_by_id(feature_id: str):
    """Fetch specific BGS corrosivity feature by ID from local JSON file"""
    try:
        bgs_data = fetch_bgs_corrosivity()

        if not bgs_data or "features" not in bgs_data:
            return None

        # Find the feature with the matching ID
        for feature in bgs_data["features"]:
            if str(feature.get("id")) == str(feature_id):
                logger.info(f"Found BGS feature with ID: {feature_id}")
                return feature

        logger.warning(f"BGS feature with ID {feature_id} not found")
        return None

    except Exception as e:
        logger.error(f"Error fetching BGS corrosivity feature by ID {feature_id}: {e}")
        return None


def get_bgs_data_summary():
    """Get a summary of the BGS corrosivity data for debugging/info purposes"""
    try:
        bgs_data = fetch_bgs_corrosivity()

        if not bgs_data or "features" not in bgs_data:
            return None

        features = bgs_data["features"]
        total_features = len(features)

        # Count features by score
        score_counts = {}
        for feature in features:
            score = feature.get("properties", {}).get("score", "Unknown")
            score_counts[score] = score_counts.get(score, 0) + 1

        # Get bounding box of all features
        all_coords = []
        for feature in features:
            geometry = feature.get("geometry", {})
            if geometry.get("type") == "Polygon":
                coords = geometry.get("coordinates", [[]])
                if coords and coords[0]:
                    all_coords.extend(coords[0])

        if all_coords:
            lons = [coord[0] for coord in all_coords]
            lats = [coord[1] for coord in all_coords]
            bbox = {
                "min_lon": min(lons),
                "max_lon": max(lons),
                "min_lat": min(lats),
                "max_lat": max(lats),
            }
        else:
            bbox = None

        summary = {
            "total_features": total_features,
            "score_distribution": score_counts,
            "bounding_box": bbox,
        }

        logger.info(
            f"BGS Data Summary: {total_features} features, Scores: {score_counts}"
        )
        return summary

    except Exception as e:
        logger.error(f"Error creating BGS data summary: {e}")
        return None


# COLABORATION INDEX
def calculate_enhanced_collaboration_index(
    location_type,
    sector_type,
    ttro_required,
    installation_method,
    street_info_data=None,
    usrn=None,
):
    """Calculate enhanced collaboration index including NUAR asset data, special designations, and work history"""
    if (
        not location_type
        or not sector_type
        or not ttro_required
        or not installation_method
    ):
        return {"total_score": 0, "breakdown": None}

    # Base scores
    location_score = location_type.score
    sector_score = sector_type.score
    ttro_score = ttro_required.score
    installation_score = installation_method.score
    base_score = location_score + sector_score + ttro_score + installation_score

    # NUAR enhancement factors
    asset_density_score = 0
    coverage_score = 0
    asset_metrics = {"total_assets": 0, "hex_grids": 0, "asset_density": 0}

    # Special designations scoring
    designation_scores = {
        "winter_maintenance": 0,
        "traffic_sensitive": 0,
        "environmentally_sensitive": 0,
    }
    designation_details = {}

    # Work history scoring
    work_history_scores = {
        "organization_count": 0,
        "total_works": 0,
        "multi_sector_bonus": 0,
    }
    work_history_details = {
        "organizations": [],
        "organization_count": 0,
        "sector_count": 0,
        "total_works": 0,
    }

    if street_info_data:
        stats = street_info_data.get("stats", {})
        nuar_summary = stats.get("nuar_summary", {})

        # Check if NUAR data exists and is valid
        if nuar_summary and nuar_summary.get("total_asset_count") is not None and usrn:
            hex_ids = nuar_summary.get("hex_ids", [])

            if hex_ids:
                # Fetch USRN geometry and filter hex grids
                logger.info(f"Fetching geometry for USRN: {usrn}")
                geodf = fetch_usrn_geometry(usrn)
                if geodf is not None and not geodf.empty:
                    logger.info(f"Successfully fetched geometry for USRN: {usrn}")
                    all_hex_gdf = create_hex_grids_geodataframe(hex_ids)
                    if all_hex_gdf is not None and not all_hex_gdf.empty:
                        logger.info(f"Created {len(all_hex_gdf)} hex grids")
                        filtered_hex_gdf = filter_hex_grids_by_usrn_intersection(
                            all_hex_gdf, geodf
                        )

                        if filtered_hex_gdf is not None and not filtered_hex_gdf.empty:
                            logger.info(
                                f"Filtered to {len(filtered_hex_gdf)} intersecting hex grids"
                            )
                            # Use FILTERED data for scoring
                            total_assets = filtered_hex_gdf["asset_count"].sum()
                            total_grids = len(filtered_hex_gdf)
                            logger.info(
                                f"Using filtered data: {total_assets} assets in {total_grids} grids"
                            )

                            if total_assets > 0 and total_grids > 0:
                                asset_density = total_assets / total_grids

                                # Asset density scoring
                                if asset_density >= 20:
                                    asset_density_score = 10  # High density
                                elif asset_density >= 15:
                                    asset_density_score = 7  # Medium density
                                elif asset_density >= 10:
                                    asset_density_score = 5  # Low-medium density
                                else:
                                    asset_density_score = 2  # Low density

                                # Grid coverage scoring
                                if total_grids >= 7:
                                    coverage_score = 10  # Large area
                                elif total_grids >= 5:
                                    coverage_score = 5  # Medium area
                                else:
                                    coverage_score = 2  # Small area

                                asset_metrics = {
                                    "total_assets": total_assets,
                                    "hex_grids": total_grids,
                                    "asset_density": round(asset_density, 1),
                                }

        # Process special designations
        designations = street_info_data.get("designations", [])
        if designations:
            # Count designations by type
            designation_counts = {}

            for designation in designations:
                designation_type = designation.get("designation", "").lower()

                # Check for Winter Maintenance Routes
                if "winter maintenance" in designation_type:
                    designation_counts["Winter Maintenance Routes"] = (
                        designation_counts.get("Winter Maintenance Routes", 0) + 1
                    )
                    designation_scores["winter_maintenance"] = (
                        10  # Award points once if present
                    )

                # Check for Traffic Sensitive Street
                elif "traffic sensitive" in designation_type:
                    designation_counts["Traffic Sensitive Street"] = (
                        designation_counts.get("Traffic Sensitive Street", 0) + 1
                    )
                    designation_scores["traffic_sensitive"] = (
                        15  # Award points once if present
                    )

                # Check for Environmentally Sensitive Areas
                elif "environmentally sensitive" in designation_type:
                    designation_counts["Environmentally Sensitive Areas"] = (
                        designation_counts.get("Environmentally Sensitive Areas", 0) + 1
                    )
                    designation_scores["environmentally_sensitive"] = (
                        10  # Award points once if present
                    )

            # Store the counts for display
            designation_details = designation_counts

        # Process 2025 work summary
        work_summary = stats.get("2025_work_summary", [])
        if work_summary and work_summary != ["NO DATA"]:
            unique_organizations = set()
            unique_sectors = set()
            total_works_count = 0

            work_organizations = []

            for work_item in work_summary:
                if isinstance(work_item, dict):
                    org = work_item.get("promoter_organisation", "")
                    sector = work_item.get("sector", "")
                    works = int(work_item.get("total_works", 0))

                    if org:
                        unique_organizations.add(org)
                        work_organizations.append(
                            {"organization": org, "sector": sector, "works": works}
                        )
                    if sector:
                        unique_sectors.add(sector)
                    total_works_count += works

            # Scoring based on work activity
            org_count = len(unique_organizations)
            sector_count = len(unique_sectors)

            # Organisation count scoring
            if org_count >= 4:
                work_history_scores["organization_count"] = 8  # High
            elif org_count >= 3:
                work_history_scores["organization_count"] = 6  # Good
            elif org_count >= 2:
                work_history_scores["organization_count"] = 4  # Some
            elif org_count >= 1:
                work_history_scores["organization_count"] = 2  # Single org
            else:
                work_history_scores["organization_count"] = 0  # No work

            # Total works scoring (more works = more active area)
            if total_works_count >= 10:
                work_history_scores["total_works"] = 5  # Very active
            elif total_works_count >= 5:
                work_history_scores["total_works"] = 3  # Active
            elif total_works_count >= 2:
                work_history_scores["total_works"] = 2  # Some activity
            elif total_works_count >= 1:
                work_history_scores["total_works"] = 1  # Minimal activity

            # Multi-sector bonus (different types of utilities working together)
            if sector_count >= 3:
                work_history_scores["multi_sector_bonus"] = 5  # High diversity
            elif sector_count >= 2:
                work_history_scores["multi_sector_bonus"] = 3  # Some diversity

            # At the end of the work history processing section, always set work_history_details:
            work_history_details = {
                "organizations": work_organizations
                if "work_organizations" in locals()
                else [],
                "organization_count": org_count if "org_count" in locals() else 0,
                "sector_count": sector_count if "sector_count" in locals() else 0,
                "total_works": total_works_count
                if "total_works_count" in locals()
                else 0,
            }

    # Calculate totals
    total_designation_score = sum(designation_scores.values())
    total_work_history_score = sum(work_history_scores.values())

    # Calculate final enhanced score
    enhanced_score = (
        base_score
        + asset_density_score
        + coverage_score
        + total_designation_score
        + total_work_history_score
    )

    return {
        "total_score": enhanced_score,
        "breakdown": {
            "base_factors": {
                "location": location_score,
                "sector": sector_score,
                "ttro": ttro_score,
                "installation": installation_score,
                "subtotal": base_score,
            },
            "nuar_factors": {
                "asset_density": asset_density_score,
                "coverage": coverage_score,
                "subtotal": asset_density_score + coverage_score,
            },
            "designation_factors": {
                "winter_maintenance": designation_scores["winter_maintenance"],
                "traffic_sensitive": designation_scores["traffic_sensitive"],
                "environmentally_sensitive": designation_scores[
                    "environmentally_sensitive"
                ],
                "subtotal": total_designation_score,
            },
            "work_history_factors": {
                "organization_count": work_history_scores["organization_count"],
                "total_works": work_history_scores["total_works"],
                "multi_sector_bonus": work_history_scores["multi_sector_bonus"],
                "subtotal": total_work_history_score,
            },
            "asset_metrics": asset_metrics,
            "designation_details": designation_details,
            "work_history_details": work_history_details,
        },
    }


def calculate_collaboration_index(
    location_type, sector_type, ttro_required, installation_method
):
    """Calculate basic collaboration index (fallback)"""
    if (
        not location_type
        or not sector_type
        or not ttro_required
        or not installation_method
    ):
        return 0

    location_score = location_type.score
    sector_score = sector_type.score
    ttro_score = ttro_required.score
    installation_score = installation_method.score

    collaboration_index = (
        location_score + sector_score + ttro_score + installation_score
    )

    return collaboration_index


def get_collaboration_recommendation(score):
    """Get collaboration recommendation based on score"""
    if score >= 80:
        return {
            "level": "🟢 HIGH PRIORITY",
            "recommendation": "Strong recommendation for collaborative working due to high underground asset density and complex work requirements.",
            "score_range": "80-100",
            "color": "#28a745",
        }
    elif score >= 60:
        return {
            "level": "🟡 MODERATE PRIORITY",
            "recommendation": "Good opportunity for collaboration with moderate asset density and work complexity.",
            "score_range": "60-79",
            "color": "#ffc107",
        }
    elif score >= 40:
        return {
            "level": "🟠 CONSIDER",
            "recommendation": "Some collaboration potential but may depend on timing and resource availability.",
            "score_range": "40-59",
            "color": "#fd7e14",
        }
    else:
        return {
            "level": "🔴 LOW PRIORITY",
            "recommendation": "Limited collaboration benefits expected based on current metrics.",
            "score_range": "0-39",
            "color": "#dc3545",
        }


# DISPLAY INDEX AND FORM DATAA
def display_enhanced_collaboration_index(
    collaboration_data, location_type, sector_type, ttro_required, installation_method
):
    """Display the enhanced collaboration index with NUAR data, special designations, and work history"""
    if not collaboration_data or not collaboration_data.get("breakdown"):
        # Fallback to basic display
        basic_score = calculate_collaboration_index(
            location_type, sector_type, ttro_required, installation_method
        )
        st.markdown(
            f"""
            <div class="collaboration-index">
                <h2>🤝 Collaboration Index</h2>
                <div class="collaboration-score">{basic_score}</div>
                <div class="collaboration-subtitle">
                    Location ({location_type.score if location_type else 0}) + 
                    Sector ({sector_type.score if sector_type else 0}) +
                    TTRO ({ttro_required.score if ttro_required else 0}) +
                    Installation ({installation_method.score if installation_method else 0})
                </div>
            </div>
        """,
            unsafe_allow_html=True,
        )
        return

    score = collaboration_data["total_score"]
    breakdown = collaboration_data["breakdown"]
    recommendation = get_collaboration_recommendation(score)

    # Check if work_history_factors exists (for backward compatibility)
    has_work_history = "work_history_factors" in breakdown

    st.markdown(
        f"""
        <div class="collaboration-index">
            <h2>🤝 Collaboration Index</h2>
            <div class="collaboration-score">{score}</div>
            <div class="collaboration-subtitle">
                <strong>Base Factors:</strong> Location ({
            breakdown["base_factors"]["location"]
        }) + 
                Sector ({breakdown["base_factors"]["sector"]}) + 
                TTRO ({breakdown["base_factors"]["ttro"]}) + 
                Installation ({breakdown["base_factors"]["installation"]}) = {
            breakdown["base_factors"]["subtotal"]
        }
            </div>
            {
            f'''<div class="collaboration-subtitle">
                <strong>Asset Factors:</strong> Density {breakdown["asset_metrics"]["asset_density"]}/grid ({breakdown["nuar_factors"]["asset_density"]}) + 
                Coverage {breakdown["asset_metrics"]["hex_grids"]} grids ({breakdown["nuar_factors"]["coverage"]}) = {breakdown["nuar_factors"]["subtotal"]}
            </div>'''
            if breakdown.get("asset_metrics")
            else f'''<div class="collaboration-subtitle">
                <strong>Asset Factors:</strong> Density ({breakdown["nuar_factors"]["asset_density"]}) + 
                Coverage ({breakdown["nuar_factors"]["coverage"]}) = {breakdown["nuar_factors"]["subtotal"]}
            </div>'''
        }
            <div class="collaboration-subtitle">
                <strong>Designation Factors:</strong> Winter Maint. ({
            breakdown["designation_factors"]["winter_maintenance"]
        }) + 
                Traffic Sensitive ({
            breakdown["designation_factors"]["traffic_sensitive"]
        }) + 
                Env. Sensitive ({
            breakdown["designation_factors"]["environmentally_sensitive"]
        }) = {breakdown["designation_factors"]["subtotal"]}
            </div>
            {
            f'''<div class="collaboration-subtitle">
                <strong>Work History Factors:</strong> {breakdown["work_history_details"].get("organization_count", 0)} Orgs ({breakdown["work_history_factors"]["organization_count"]}) + 
                {breakdown["work_history_details"].get("total_works", 0)} Works ({breakdown["work_history_factors"]["total_works"]}) + 
                {breakdown["work_history_details"].get("sector_count", 0)} Sectors ({breakdown["work_history_factors"]["multi_sector_bonus"]}) = {breakdown["work_history_factors"]["subtotal"]}
            </div>'''
            if has_work_history
            else ""
        }
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Display recommendation
    st.markdown(
        f"""
        <div style="background: {recommendation["color"]}; color: white; padding: 1rem; border-radius: 10px; margin: 1rem 0; text-align: center;">
            <h3 style="margin: 0 0 0.5rem 0;">{recommendation["level"]}</h3>
            <p style="margin: 0; font-size: 1.1rem;"><strong>Score: {score} ({recommendation["score_range"]})</strong></p>
            <p style="margin: 0.5rem 0 0 0;">{recommendation["recommendation"]}</p>
        </div>
    """,
        unsafe_allow_html=True,
    )


def display_form_data(form_data):
    """Display the submitted form data in a nice format"""
    st.markdown("### Forward Plan Submission")

    # Create two columns for better layout
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Basic Information:**")
        st.write(f"• **Permit Reference:** {form_data['permit_ref']}")
        st.write(f"• **SWA Code:** {form_data['swa_code']}")
        st.write(f"• **USRN:** {form_data['usrn']}")
        st.write(f"• **Promoter Organisation:** {form_data['promoter_org']}")
        st.write(f"• **Location Type:** {form_data['location_type']}")
        st.write(f"• **Sector Type:** {form_data['sector_type']}")

    with col2:
        st.markdown("**Work Details:**")
        st.write(f"• **Activity Type:** {form_data['activity_type']}")
        st.write(f"• **Installation Method:** {form_data['installation_method']}")
        st.write(f"• **Work Start Date:** {form_data['work_start_date']}")
        st.write(f"• **Work End Date:** {form_data['work_end_date']}")
        st.write(f"• **TTRO Required:** {form_data['ttro_required']}")

    st.markdown("**Programme Information:**")
    st.write(f"• **Capital Works Programme:** {form_data['capital_works_programme']}")
    if form_data["programme_of_works"]:
        st.write(f"• **Programme of Works:** {form_data['programme_of_works']}")


def display_work_statistics(work_summary):
    """Display work statistics in a clean format"""
    if not work_summary or work_summary == ["NO DATA"]:
        st.write("• No work summary data available for 2025")
        return

    # Convert to DataFrame for better display
    work_data = []
    for work_item in work_summary:
        if isinstance(work_item, dict):
            work_data.append(
                {
                    "Organisation": work_item.get("promoter_organisation", "Unknown"),
                    "Sector": work_item.get("sector", "Unknown"),
                    "Total Works": work_item.get("total_works", "0"),
                }
            )

    if work_data:
        # Create DataFrame
        df = pd.DataFrame(work_data)

        # Display as a nice table
        st.dataframe(df, hide_index=True, use_container_width=True)

        # Also display with emojis for better visual appeal
        st.markdown("**Previous Work Activity:**")
        for work in work_data:
            sector_emoji = {
                "Electricity": "⚡",
                "Gas": "🔥",
                "Water": "💧",
                "Highway Authority": "🛣️",
                "Telecommunications": "📡",
            }.get(work["Sector"], "🔧")

            st.markdown(
                f"{sector_emoji} **{work['Organisation']}** ({work['Sector']}): {work['Total Works']} works"
            )
    else:
        # Fallback to original format
        for work_item in work_summary:
            st.write(f"• {work_item}")


def display_street_info(street_info_data):
    """Display the street info data in a nice format"""
    if not street_info_data:
        return

    st.markdown("### 🗺️ Street Information")

    # Parse the street data
    street = street_info_data.get("street", {})
    designations = street_info_data.get("designations", [])
    stats = street_info_data.get("stats", {})
    metadata = street_info_data.get("metadata", {})

    # Display basic street information
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Street Details:**")
        st.write(f"• **USRN:** {street.get('usrn', 'Unknown')}")
        st.write(f"• **Street Name:** {street.get('street_name', 'Unknown')}")
        st.write(f"• **Town:** {street.get('town', 'Unknown')}")
        st.write(
            f"• **Operational State:** {street.get('operational_state', 'Unknown')}"
        )
        if street.get("operational_state_date"):
            st.write(f"• **Operational Date:** {street.get('operational_state_date')}")

    with col2:
        st.markdown("**Authority & Geometry:**")
        authority = street.get("authority", {})
        geometry = street.get("geometry", {})

        st.write(f"• **Authority:** {authority.get('name', 'Unknown')}")
        st.write(f"• **Area:** {authority.get('area', 'Unknown')}")
        if geometry.get("length"):
            st.write(f"• **Length:** {geometry.get('length'):.1f}m")

    # Display designations in an organized way
    if designations:
        st.markdown("---")
        st.markdown(f"**Special Designations ({len(designations)} total):**")

        # Group designations by type
        designation_groups = {}
        for designation in designations:
            designation_type = designation.get("designation", "Unknown")
            if designation_type not in designation_groups:
                designation_groups[designation_type] = []
            designation_groups[designation_type].append(designation)

        # Display each group in tabs or expanders
        designation_types = list(designation_groups.keys())

        for designation_type in designation_types:
            items = designation_groups[designation_type]

            with st.expander(
                f"🚧 {designation_type} ({len(items)} items)", expanded=False
            ):
                for i, item in enumerate(items, 1):
                    st.markdown(f"**Item {i}:**")

                    # Show timeframe
                    if item.get("timeframe"):
                        st.write(f"⏰ **Timeframe:** {item['timeframe']}")

                    # Show location if available
                    if item.get("location"):
                        st.write(f"📍 **Location:** {item['location']}")

                    # Show details
                    if item.get("details"):
                        st.write(f"ℹ️ **Details:** {item['details']}")

                    # Show effective date
                    if item.get("effective_date"):
                        st.write(f"📅 **Effective Date:** {item['effective_date']}")

                    if i < len(items):  # Add separator between items
                        st.markdown("---")

    # Display work summary statistics with enhanced formatting
    if stats:
        st.markdown("---")
        st.markdown("**📊 Work Statistics:**")
        work_summary = stats.get("2025_work_summary", [])
        display_work_statistics(work_summary)

    # Display metadata
    if metadata:
        with st.expander("🔍 Metadata", expanded=False):
            st.write(f"**Query Timestamp:** {metadata.get('timestamp', 'Unknown')}")
            st.write(
                f"**Designations Returned:** {metadata.get('number_returned', 'Unknown')}"
            )

    # Show raw data in collapsible section
    with st.expander("📋 Raw API Response", expanded=False):
        st.json(street_info_data)


# MAP
@st.cache_resource
def connect_to_motherduck() -> duckdb.DuckDBPyConnection:
    """
    Create a database connection object to MotherDuck
    """
    # Define secrets
    database = st.secrets["MD_DB"]
    token = st.secrets["MD_TOKEN"]

    # Check if token exists
    if token is None:
        raise ValueError("Env variable not present")

    # Connection string
    connection_string = f"md:{database}?motherduck_token={token}"

    # Attempt connection
    try:
        con = duckdb.connect(connection_string)
        return con
    except Exception as e:
        logger.warning(f"An error occured: {e}")
        raise


def remove_z(
    geom: Union[LineString, MultiLineString, Point, MultiPoint],
) -> Union[LineString, MultiLineString, Point, MultiPoint]:
    """Remove Z coordinates from geometry objects"""
    if isinstance(geom, LineString):
        return LineString([(x, y) for x, y, *_ in geom.coords])
    elif isinstance(geom, MultiLineString):
        lines = [remove_z(line) for line in geom.geoms]
        return MultiLineString(cast(List[LineString], lines))
    elif isinstance(geom, Point):
        x, y, *_ = geom.coords[0]
        return Point(x, y)
    elif isinstance(geom, MultiPoint):
        points = [remove_z(point) for point in geom.geoms]
        return MultiPoint(cast(List[Point], points))
    return geom


def convert_to_geodf_from_wkt(
    df: pd.DataFrame, geometry_col: str = "geometry"
) -> gpd.GeoDataFrame:
    """
    Takes in a pandas dataframe with WKT geometry and returns a geodataframe
    Ensure that the crs is set to EPSG:4326 and removes Z coordinates if present
    """
    # Check that DataFrame is not empty
    if df is None or df.empty:
        raise ValueError("Input DataFrame is None or empty")

    # Convert WKT to geometry and remove the Z coordinates if present
    df["geometry"] = gpd.GeoSeries.from_wkt(df[geometry_col]).apply(remove_z)

    # Create GeoDataFrame and ensure correct crs
    # Assuming source data is in British National Grid (EPSG:27700)
    geodf = gpd.GeoDataFrame(df, geometry="geometry", crs="EPSG:27700")  # type: ignore

    # Convert to EPSG:4326 (WGS84)
    geodf = geodf.to_crs(epsg=4326)

    # Assert that data is a GeoDataFrame and that CRS is correct
    assert isinstance(geodf, gpd.GeoDataFrame)
    assert geodf.crs is not None and geodf.crs.to_epsg() == 4326
    return geodf


def fetch_usrn_geometry(usrn: str) -> Optional[gpd.GeoDataFrame]:
    """
    Fetch geometry for a given USRN from MotherDuck
    """
    try:
        con = connect_to_motherduck()

        # Get schema and table from secrets
        schema = st.secrets["USRN_SCHEMA"]
        table_name = st.secrets["USRN_TABLE"]

        logger.debug(f"Schema: {schema}, Table: {table_name}")

        if not all([schema, table_name]):
            raise ValueError("Missing schema or table name environment variables")

        query = f"""
            SELECT 
                usrn,
                geometry
            FROM {schema}.{table_name}
            WHERE usrn = ?
        """

        # Execute query
        df = con.execute(query, [usrn]).df()

        if df.empty:
            logger.warning(f"No geometry found for USRN: {usrn}")
            return None

        # Convert to GeoDataFrame
        geodf = convert_to_geodf_from_wkt(df)

        return geodf

    except Exception as e:
        logger.error(f"Error fetching USRN geometry: {e}")
        st.error(f"Error fetching geometry for USRN {usrn}: {e}")
        return None


def filter_hex_grids_by_usrn_intersection(hex_gdf, usrn_gdf):
    """Filter hex grids to only those that intersect with the USRN geometry (no buffer)"""
    if hex_gdf is None or hex_gdf.empty or usrn_gdf is None or usrn_gdf.empty:
        return None

    # Ensure both GeoDataFrames are in the same CRS
    if hex_gdf.crs != usrn_gdf.crs:
        hex_gdf = hex_gdf.to_crs(usrn_gdf.crs)

    # Get the USRN geometry - use union_all() instead of unary_union
    usrn_geometry = usrn_gdf.geometry.union_all()

    # Filter hex grids that intersect with USRN
    intersecting_mask = hex_gdf.geometry.intersects(usrn_geometry)
    filtered_hex_gdf = hex_gdf[intersecting_mask].copy()

    logger.info(
        f"Filtered hex grids by intersection: {len(hex_gdf)} -> {len(filtered_hex_gdf)}"
    )

    return filtered_hex_gdf if not filtered_hex_gdf.empty else None


def create_bgs_corrosivity_geodataframe(bgs_data):
    """Create a GeoDataFrame from BGS corrosivity GeoJSON data"""
    if not bgs_data or "features" not in bgs_data:
        return None

    features = bgs_data["features"]
    if not features:
        return None

    # Extract data for GeoDataFrame
    corrosivity_data = []

    for feature in features:
        properties = feature.get("properties", {})
        geometry_data = feature.get("geometry", {})
        feature_id = feature.get("id")

        if geometry_data and geometry_data.get("type") == "Polygon":
            try:
                # Create Shapely polygon from coordinates
                coords = geometry_data["coordinates"][0]  # Get outer ring
                polygon = Polygon(coords)

                corrosivity_data.append(
                    {
                        "id": feature_id,
                        "score": properties.get("score", "Unknown"),
                        "legend": properties.get("legend", ""),
                        "class": properties.get("class", ""),
                        "recommendation": properties.get("recommenda", ""),
                        "backfill": properties.get("backfill", ""),
                        "version": properties.get("version", ""),
                        "geometry": polygon,
                    }
                )

            except Exception as e:
                logger.warning(
                    f"Error processing BGS corrosivity feature {feature_id}: {e}"
                )
                continue

    if not corrosivity_data:
        return None

    # Create GeoDataFrame - BGS data is already in WGS84 (EPSG:4326)
    gdf = gpd.GeoDataFrame(corrosivity_data, crs="EPSG:4326")  # type: ignore

    return gdf


def find_intersecting_bgs_corrosivity(usrn_gdf, buffer_meters=100):
    """Find BGS corrosivity data that intersects with USRN geometry using local data"""
    if usrn_gdf is None or usrn_gdf.empty:
        logger.warning("USRN GeoDataFrame is None or empty")
        return None, []

    try:
        usrn_projected = usrn_gdf.to_crs(epsg=3857)  
        
        # Create buffer around USRN
        buffered_usrn = usrn_projected.geometry.buffer(buffer_meters)
        
        # Convert back to WGS84 for comparison with BGS data
        buffered_gdf = gpd.GeoDataFrame(geometry=buffered_usrn, crs="EPSG:3857").to_crs(epsg=4326) # type: ignore
        buffer_bounds = buffered_gdf.total_bounds
        
        logger.info(f"USRN buffer bounds: {buffer_bounds}")
        
        # Load BGS corrosivity data from local file
        logger.info("Loading BGS corrosivity data from local file...")
        bgs_data = fetch_bgs_corrosivity()
        
        if not bgs_data:
            logger.warning("No BGS corrosivity data available from local file")
            return None, []
        
        # Check if we have features
        if "features" not in bgs_data or not bgs_data["features"]:
            logger.warning("BGS data contains no features")
            return None, []
        
        logger.info(f"Loaded {len(bgs_data['features'])} BGS features from local file")
        
        # Convert to GeoDataFrame
        bgs_gdf = create_bgs_corrosivity_geodataframe(bgs_data)
        
        if bgs_gdf is None or bgs_gdf.empty:
            logger.warning("No valid BGS corrosivity geometries found after processing")
            return None, []
        
        logger.info(f"Created BGS GeoDataFrame with {len(bgs_gdf)} valid geometries")
        
        # Find intersections with the buffered USRN
        buffer_geometry = buffered_gdf.geometry.union_all()
        intersecting_mask = bgs_gdf.geometry.intersects(buffer_geometry)
        intersecting_bgs = bgs_gdf[intersecting_mask].copy()
        
        if intersecting_bgs.empty:
            logger.info(f"No BGS corrosivity areas intersect with USRN buffer (buffer: {buffer_meters}m)")
            larger_buffer = usrn_projected.geometry.buffer(500)  # 500m buffer
            larger_buffered_gdf = gpd.GeoDataFrame(geometry=larger_buffer, crs="EPSG:3857").to_crs(epsg=4326) # type: ignore
            larger_buffer_geometry = larger_buffered_gdf.geometry.union_all()
            larger_intersecting_mask = bgs_gdf.geometry.intersects(larger_buffer_geometry)
            larger_intersecting_count = larger_intersecting_mask.sum()
            logger.info(f"For reference: {larger_intersecting_count} BGS areas within 500m of USRN")
            
            # Show this info to user
            if larger_intersecting_count > 0:
                st.info(f"No BGS corrosivity areas found within {buffer_meters}m of the street, but {larger_intersecting_count} areas found within 500m")
            else:
                st.info("No BGS corrosivity areas found near this street")
            
            return None, []
        
        logger.info(f"Found {len(intersecting_bgs)} intersecting BGS corrosivity areas")
        
        # Log some details about the intersecting areas
        for _, row in intersecting_bgs.iterrows():
            score = row.get("score", "Unknown")
            feature_id = row.get("id", "Unknown")
            logger.info(f"Intersecting BGS area ID {feature_id}: score={score}")
        
        # Get the IDs for detailed data fetching
        intersecting_ids = intersecting_bgs["id"].tolist()
        
        return intersecting_bgs, intersecting_ids
        
    except Exception as e:
        logger.error(f"Error finding intersecting BGS corrosivity data: {e}")
        st.error(f"Error processing BGS corrosivity data: {e}")
        return None, []


def get_corrosivity_color(score_str):
    """Get color based on corrosivity score"""
    try:
        # Extract numeric part from score string (e.g., ">11" -> 11)
        if ">" in score_str:
            score = float(score_str.replace(">", ""))
        elif "<" in score_str:
            score = float(score_str.replace("<", ""))
        else:
            score = float(score_str)

        # Color scheme based on corrosivity risk
        if score >= 11:
            return "#8B0000", "#FF4444"  # Dark red, light red fill - High risk
        elif score >= 8:
            return "#FF8C00", "#FFA500"  # Dark orange, orange fill - Medium-high risk
        elif score >= 5:
            return "#FFD700", "#FFFF99"  # Gold, light yellow fill - Medium risk
        else:
            return "#32CD32", "#98FB98"  # Lime green, light green fill - Low risk

    except (ValueError, TypeError):
        return "#808080", "#D3D3D3"  # Gray for unknown scores


def plot_usrn_map_with_hex_grids_and_corrosivity(
    geodf: gpd.GeoDataFrame, usrn: str, street_info_data=None, bgs_corrosivity_gdf=None
):
    """Plot USRN geometry on a map with filtered hex grids and BGS corrosivity data"""
    try:
        # Get the bounds of the USRN geometry
        total_bounds = geodf.total_bounds

        # Create hex grids if NUAR data is available
        hex_gdf = None
        if street_info_data:
            stats = street_info_data.get("stats", {})
            nuar_summary = stats.get("nuar_summary", {})
            hex_ids = nuar_summary.get("hex_ids", [])

            if hex_ids:
                all_hex_gdf = create_hex_grids_geodataframe(hex_ids)
                if all_hex_gdf is not None and not all_hex_gdf.empty:
                    # Filter to only hex grids that intersect the USRN
                    hex_gdf = filter_hex_grids_by_usrn_intersection(all_hex_gdf, geodf)

                    if hex_gdf is not None and not hex_gdf.empty:
                        # Expand bounds to include filtered hex grids
                        hex_bounds = hex_gdf.total_bounds
                        total_bounds = [
                            min(total_bounds[0], hex_bounds[0]),  # min x
                            min(total_bounds[1], hex_bounds[1]),  # min y
                            max(total_bounds[2], hex_bounds[2]),  # max x
                            max(total_bounds[3], hex_bounds[3]),  # max y
                        ]

        # Expand bounds to include BGS corrosivity data if available
        if bgs_corrosivity_gdf is not None and not bgs_corrosivity_gdf.empty:
            bgs_bounds = bgs_corrosivity_gdf.total_bounds
            total_bounds = [
                min(total_bounds[0], bgs_bounds[0]),  # min x
                min(total_bounds[1], bgs_bounds[1]),  # min y
                max(total_bounds[2], bgs_bounds[2]),  # max x
                max(total_bounds[3], bgs_bounds[3]),  # max y
            ]

        # Create the map and set bounds to the data area
        m = folium.Map(tiles="cartodbpositron")
        m.fit_bounds(
            [[total_bounds[1], total_bounds[0]], [total_bounds[3], total_bounds[2]]]
        )

        # Add BGS corrosivity areas first (bottom layer)
        if bgs_corrosivity_gdf is not None and not bgs_corrosivity_gdf.empty:
            for _, row in bgs_corrosivity_gdf.iterrows():
                if row.geometry is not None and not row.geometry.is_empty:
                    score = row.get("score", "Unknown")
                    border_color, fill_color = get_corrosivity_color(score)

                    folium.GeoJson(
                        row.geometry.__geo_interface__,
                        style_function=lambda x, border_color=border_color, fill_color=fill_color: {
                            "color": border_color,
                            "weight": 3,
                            "opacity": 0.8,
                            "fillColor": fill_color,
                            "fillOpacity": 0.3,
                        },
                        tooltip=folium.Tooltip(
                            f"<strong>BGS Corrosivity</strong><br>"
                            f"Score: {row.get('score', 'Unknown')}<br>"
                            f"Class: {row.get('class', 'Unknown')}<br>"
                            f"Risk: {row.get('legend', 'Unknown')}"
                        ),
                    ).add_to(m)

        # Add hex grids (middle layer)
        if hex_gdf is not None and not hex_gdf.empty:
            # Get min and max asset counts from the ORIGINAL full dataset for consistent color scaling
            if street_info_data:
                stats = street_info_data.get("stats", {})
                nuar_summary = stats.get("nuar_summary", {})
                hex_ids = nuar_summary.get("hex_ids", [])

                # Calculate min/max from original data, not filtered data
                all_asset_counts = [item.get("asset_count", 0) for item in hex_ids]
                min_assets = min(all_asset_counts) if all_asset_counts else 0
                max_assets = max(all_asset_counts) if all_asset_counts else 0
                asset_range = max_assets - min_assets
            else:
                min_assets = hex_gdf["asset_count"].min()
                max_assets = hex_gdf["asset_count"].max()
                asset_range = max_assets - min_assets

            for _, row in hex_gdf.iterrows():
                if row.geometry is not None and not row.geometry.is_empty:
                    asset_count = row.get("asset_count", 0)

                    # Use the original full dataset range for color scaling
                    if asset_range <= 5:  # Low variance threshold
                        if max_assets > min_assets:
                            intensity = (
                                (asset_count - min_assets) / asset_range * 0.5
                            )  # Scale to 0-0.5
                        else:
                            intensity = 0.25  # Middle of the narrow range

                        if intensity <= 0.1:
                            color = "#e3f2fd"  # Very light blue
                            fill_color = "#e3f2fd"
                        elif intensity <= 0.25:
                            color = "#bbdefb"  # Light blue
                            fill_color = "#bbdefb"
                        else:
                            color = "#90caf9"  # Medium light blue
                            fill_color = "#90caf9"
                    else:
                        # Normal scaling for high variance
                        intensity = (asset_count - min_assets) / asset_range

                        if intensity <= 0.2:
                            color = "#e3f2fd"  # Very light blue
                            fill_color = "#e3f2fd"
                        elif intensity <= 0.4:
                            color = "#90caf9"  # Light blue
                            fill_color = "#90caf9"
                        elif intensity <= 0.6:
                            color = "#42a5f5"  # Medium blue
                            fill_color = "#42a5f5"
                        elif intensity <= 0.8:
                            color = "#1e88e5"  # Dark blue
                            fill_color = "#1e88e5"
                        else:
                            color = "#0d47a1"  # Very dark blue
                            fill_color = "#0d47a1"

                    folium.GeoJson(
                        row.geometry.__geo_interface__,
                        style_function=lambda x, color=color, fill_color=fill_color: {
                            "color": color,
                            "weight": 2,
                            "opacity": 0.7,
                            "fillColor": fill_color,
                            "fillOpacity": 0.4,
                        },
                        tooltip=folium.Tooltip(
                            f"Hex Grid: {row.get('grid_id', 'Unknown')}<br>"
                            f"Asset Count: {row.get('asset_count', 0)}<br>"
                            f"Zoom Level: {row.get('zoom_level', 'Unknown')}"
                        ),
                    ).add_to(m)

        # Add USRN features to map - style for USRN roads (top layer)
        for _, row in geodf.iterrows():
            if row.geometry is not None and not row.geometry.is_empty:
                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x: {
                        "color": "#ff6b6b",
                        "weight": 6,
                        "opacity": 0.9,
                    },
                    tooltip=folium.Tooltip(
                        f"USRN: {row.get('usrn', usrn)}<br>Street Reference"
                    ),
                ).add_to(m)

        # Add legends
        legend_html_parts = []

        # Hex grids legend
        if hex_gdf is not None and not hex_gdf.empty:
            min_assets = hex_gdf["asset_count"].min()
            max_assets = hex_gdf["asset_count"].max()
            asset_range = max_assets - min_assets

            if asset_range <= 5:  # Low variance
                hex_legend = f"""
<div style="margin-bottom: 10px;">
<h4>NUAR Asset Density</h4>
<p><em>Low variance ({min_assets}-{max_assets})</em></p>
<p><span style="color:#e3f2fd; background:#e3f2fd;">⬣</span> {min_assets} assets</p>
<p><span style="color:#90caf9; background:#90caf9;">⬣</span> {max_assets} assets</p>
</div>
"""
            else:  # Normal variance
                hex_legend = f"""
<div style="margin-bottom: 10px;">
<h4>NUAR Asset Density</h4>
<p><span style="color:#e3f2fd; background:#e3f2fd;">⬣</span> Very Low ({min_assets})</p>
<p><span style="color:#90caf9; background:#90caf9;">⬣</span> Low</p>
<p><span style="color:#42a5f5; background:#42a5f5;">⬣</span> Medium</p>
<p><span style="color:#1e88e5; background:#1e88e5;">⬣</span> High</p>
<p><span style="color:#0d47a1; background:#0d47a1;">⬣</span> Very High ({max_assets})</p>
</div>
"""
            legend_html_parts.append(hex_legend)

        # BGS corrosivity legend
        if bgs_corrosivity_gdf is not None and not bgs_corrosivity_gdf.empty:
            corr_legend = """
<div style="margin-bottom: 10px;">
<h4>BGS Corrosivity Risk</h4>
<p><span style="color:#32CD32; background:#98FB98;">▬</span> Low Risk (&lt;5)</p>
<p><span style="color:#FFD700; background:#FFFF99;">▬</span> Medium Risk (5-7)</p>
<p><span style="color:#FF8C00; background:#FFA500;">▬</span> High Risk (8-10)</p>
<p><span style="color:#8B0000; background:#FF4444;">▬</span> Very High Risk (&gt;11)</p>
</div>
"""
            legend_html_parts.append(corr_legend)

        # Combine legends if we have any
        if legend_html_parts:
            legend_height = max(150, len(legend_html_parts) * 120)
            legend_html = f"""
<div style="position: fixed; 
            bottom: 50px; right: 50px; width: 240px; height: {legend_height}px; 
            background-color: white; border:2px solid grey; z-index:9999; 
            font-size:14px; padding: 10px; overflow-y: auto;
            ">
{"".join(legend_html_parts)}
</div>
"""
            m.get_root().add_child(folium.Element(legend_html))

        # Display map using folium_static - responsive width
        folium_static(m, width=None, height=500)

        return m

    except Exception as e:
        logger.error(f"Error occurred while plotting map: {e}")
        raise


def display_usrn_map_enhanced_with_corrosivity(usrn: str, street_info_data=None):
    """Display USRN geometry on a map with NUAR hex grids and BGS corrosivity data"""
    try:
        with st.spinner(f"Loading geometry and corrosivity data for USRN {usrn}..."):
            geodf = fetch_usrn_geometry(usrn)

        if geodf is not None and not geodf.empty:
            # Fetch BGS corrosivity data that intersects with USRN
            bgs_corrosivity_gdf, bgs_ids = find_intersecting_bgs_corrosivity(geodf)

            # Check if we have NUAR data
            has_nuar_data = False
            if street_info_data:
                stats = street_info_data.get("stats", {})
                nuar_summary = stats.get("nuar_summary", {})
                hex_ids = nuar_summary.get("hex_ids", [])
                has_nuar_data = len(hex_ids) > 0

            # Display info about available data
            info_messages = []
            if has_nuar_data:
                info_messages.append(
                    "🔵 Underground asset data (NUAR) overlayed as hex grids"
                )
            if bgs_corrosivity_gdf is not None and not bgs_corrosivity_gdf.empty:
                info_messages.append("🟡 BGS corrosivity risk areas shown")

            if info_messages:
                st.info(" | ".join(info_messages))

            # Plot the enhanced map with corrosivity data
            plot_usrn_map_with_hex_grids_and_corrosivity(
                geodf, usrn, street_info_data, bgs_corrosivity_gdf
            )

            # Custom CSS for the info cards (keep existing CSS)
            st.markdown(
                """
            <style>
            .info-card {
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 1.5rem;
                border-radius: 12px;
                margin: 0.5rem 0;
                border-left: 4px solid #007bff;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .info-card h4 {
                margin: 0 0 1rem 0;
                color: #495057;
                font-size: 1.1rem;
                font-weight: 600;
            }
            .metric-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem 0;
                border-bottom: 1px solid #dee2e6;
            }
            .metric-item:last-child {
                border-bottom: none;
            }
            .metric-label {
                font-weight: 500;
                color: #6c757d;
            }
            .metric-value {
                font-weight: 700;
                color: #495057;
                font-size: 1.1rem;
            }
            .asset-card {
                background: linear-gradient(135deg, #e8f5e8 0%, #d4edda 100%);
                border-left: 4px solid #28a745;
            }
            .corrosivity-card {
                background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
                border-left: 4px solid #ffc107;
            }
            </style>
            """,
                unsafe_allow_html=True,
            )

            # Create three columns for information display
            if bgs_corrosivity_gdf is not None and not bgs_corrosivity_gdf.empty:
                col1, col2, col3 = st.columns(3)
            else:
                col1, col2 = st.columns(2)
                col3 = None

            with col1:
                # Calculate length if it's a LineString
                if hasattr(geodf.geometry.iloc[0], "length"):
                    length_meters = geodf.to_crs(epsg=3857).geometry.length.iloc[0]
                    length_display = f"{length_meters:.1f}m"
                else:
                    length_display = "N/A"

                st.markdown(
                    f"""
                <div class="info-card">
                    <h4>🗺️ Street Geometry</h4>
                    <div class="metric-item">
                        <span class="metric-label">USRN</span>
                        <span class="metric-value">{usrn}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Street Length</span>
                        <span class="metric-value">{length_display}</span>
                    </div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col2:
                if has_nuar_data:
                    # Calculate metrics from FILTERED hex grids
                    if street_info_data:
                        stats = street_info_data.get("stats", {})
                        nuar_summary = stats.get("nuar_summary", {})
                        hex_ids = nuar_summary.get("hex_ids", [])

                        if hex_ids:
                            all_hex_gdf = create_hex_grids_geodataframe(hex_ids)
                            if all_hex_gdf is not None and not all_hex_gdf.empty:
                                filtered_hex_gdf = (
                                    filter_hex_grids_by_usrn_intersection(
                                        all_hex_gdf, geodf
                                    )
                                )

                                if (
                                    filtered_hex_gdf is not None
                                    and not filtered_hex_gdf.empty
                                ):
                                    filtered_total_assets = filtered_hex_gdf[
                                        "asset_count"
                                    ].sum()
                                    filtered_total_grids = len(filtered_hex_gdf)
                                    filtered_density = (
                                        filtered_total_assets / filtered_total_grids
                                        if filtered_total_grids > 0
                                        else 0
                                    )

                                    st.markdown(
                                        f"""
                                    <div class="info-card asset-card">
                                        <h4>🔵 Underground Assets</h4>
                                        <div class="metric-item">
                                            <span class="metric-label">Total Assets</span>
                                            <span class="metric-value">{filtered_total_assets}</span>
                                        </div>
                                        <div class="metric-item">
                                            <span class="metric-label">Hex Grids</span>
                                            <span class="metric-value">{filtered_total_grids}</span>
                                        </div>
                                        <div class="metric-item">
                                            <span class="metric-label">Asset Density</span>
                                            <span class="metric-value">{filtered_density:.1f}/grid</span>
                                        </div>
                                    </div>
                                    """,
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    st.markdown(
                                        """
                                    <div class="info-card asset-card">
                                        <h4>🔵 Underground Assets</h4>
                                        <p style="margin: 0; color: #6c757d; font-style: italic;">No hex grids intersect with this USRN</p>
                                    </div>
                                    """,
                                        unsafe_allow_html=True,
                                    )
                else:
                    st.markdown(
                        """
                    <div class="info-card">
                        <h4>📊 Additional Info</h4>
                        <div class="metric-item">
                            <span class="metric-label">Coordinate System</span>
                            <span class="metric-value">EPSG:4326</span>
                        </div>
                        <p style="margin: 0.5rem 0 0 0; color: #6c757d; font-style: italic;">No underground asset data available</p>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

            # BGS Corrosivity information in third column
            if (
                col3
                and bgs_corrosivity_gdf is not None
                and not bgs_corrosivity_gdf.empty
            ):
                with col3:
                    # Get the highest risk area
                    highest_risk_area = None
                    highest_score = 0

                    for _, row in bgs_corrosivity_gdf.iterrows():
                        score_str = row.get("score", "0")
                        try:
                            if ">" in score_str:
                                score = float(score_str.replace(">", ""))
                            elif "<" in score_str:
                                score = float(score_str.replace("<", ""))
                            else:
                                score = float(score_str)

                            if score > highest_score:
                                highest_score = score
                                highest_risk_area = row
                        except (ValueError, TypeError):
                            continue

                    if highest_risk_area is not None:
                        risk_level = (
                            "Very High"
                            if highest_score >= 11
                            else "High"
                            if highest_score >= 8
                            else "Medium"
                            if highest_score >= 5
                            else "Low"
                        )

                        st.markdown(
                            f"""
                        <div class="info-card corrosivity-card">
                            <h4>⚠️ Corrosivity Risk</h4>
                            <div class="metric-item">
                                <span class="metric-label">Risk Level</span>
                                <span class="metric-value">{risk_level}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Max Score</span>
                                <span class="metric-value">{highest_risk_area.get("score", "Unknown")}</span>
                            </div>
                            <div class="metric-item">
                                <span class="metric-label">Areas Found</span>
                                <span class="metric-value">{len(bgs_corrosivity_gdf)}</span>
                            </div>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"""
                        <div class="info-card corrosivity-card">
                            <h4>⚠️ Corrosivity Risk</h4>
                            <div class="metric-item">
                                <span class="metric-label">Areas Found</span>
                                <span class="metric-value">{len(bgs_corrosivity_gdf)}</span>
                            </div>
                            <p style="margin: 0.5rem 0 0 0; color: #6c757d; font-style: italic;">Score data unavailable</p>
                        </div>
                        """,
                            unsafe_allow_html=True,
                        )

            # Display detailed corrosivity information if available
            if bgs_corrosivity_gdf is not None and not bgs_corrosivity_gdf.empty:
                with st.expander("⚠️ View BGS Corrosivity Details", expanded=False):
                    for i, (_, row) in enumerate(bgs_corrosivity_gdf.iterrows(), 1):
                        st.markdown(f"**Corrosivity Area {i}:**")
                        st.write(f"• **Score:** {row.get('score', 'Unknown')}")
                        st.write(f"• **Class:** {row.get('class', 'Unknown')}")
                        st.write(f"• **Risk:** {row.get('legend', 'Unknown')}")
                        if row.get("recommendation"):
                            st.write(
                                f"• **Recommendation:** {row.get('recommendation', '')}"
                            )
                        if row.get("backfill"):
                            st.write(
                                f"• **Backfill Guidance:** {row.get('backfill', '')}"
                            )
                        if i < len(bgs_corrosivity_gdf):
                            st.markdown("---")

        else:
            st.warning(f"No geometry found for USRN: {usrn}")

    except Exception as e:
        st.error(f"Error loading geometry and corrosivity data: {e}")
        logger.error(f"Error in display_usrn_map_enhanced_with_corrosivity: {e}")


# MAIN
def main():
    # Page configuration
    st.set_page_config(
        page_title="Forward Plan Submission",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Custom CSS
    st.markdown(
        """
        <style>
        .main-header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(90deg, #4a90e2 0%, #357abd 100%);
            color: white;
            margin: -1rem -1rem 2rem -1rem;
            border-radius: 0 0 10px 10px;
        }
        .collaboration-index {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            padding: 2rem;
            border-radius: 15px;
            text-align: center;
            margin: 1rem 0 2rem 0;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);
            border: 3px solid #ffffff20;
        }
        .collaboration-index h2 {
            margin: 0 0 1rem 0;
            font-size: 1.5rem;
            font-weight: 600;
        }
        .collaboration-score {
            font-size: 4rem;
            font-weight: 800;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .collaboration-subtitle {
            font-size: 1.1rem;
            margin: 0.5rem 0 0 0;
            opacity: 0.9;
        }
        .stTextInput > div > div > input, .stTextArea > div > div > textarea {
            background-color: #f8f9fa;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 0.5rem;
        }
        .stSelectbox > div > div > div {
            background-color: #f8f9fa;
            border: 2px solid #e9ecef;
            border-radius: 8px;
        }
        .stButton > button {
            background-color: #28a745 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
            width: 100% !important;
        }
        .stButton > button:hover {
            background-color: #218838 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 8px rgba(40, 167, 69, 0.3) !important;
        }
        .stButton > button:active {
            background-color: #1e7e34 !important;
            transform: translateY(0px) !important;
        }
        .stButton > button:disabled {
            background-color: #6c757d !important;
            color: #ffffff !important;
            opacity: 0.6 !important;
        }
        /* Custom styling for the New Submission button */
        .new-submission-button {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 1rem;
        }
        .new-submission-button .stButton > button,
        .new-submission-button div[data-testid="baseButton-secondary"] button,
        .new-submission-button button[kind="secondary"] {
            background-color: #007bff !important;
            color: white !important;
            border: none !important;
            border-radius: 6px !important;
            padding: 0.375rem 0.75rem !important;
            font-size: 0.875rem !important;
            font-weight: 500 !important;
            width: auto !important;
            min-width: 120px !important;
            max-width: 200px !important;
        }
        .new-submission-button .stButton > button:hover,
        .new-submission-button div[data-testid="baseButton-secondary"] button:hover,
        .new-submission-button button[kind="secondary"]:hover {
            background-color: #0056b3 !important;
            transform: none !important;
            box-shadow: 0 2px 4px rgba(0, 123, 255, 0.25) !important;
        }
        .new-submission-button .stButton > button:active,
        .new-submission-button div[data-testid="baseButton-secondary"] button:active,
        .new-submission-button button[kind="secondary"]:active {
            background-color: #004085 !important;
        }
        .section-divider {
            border-top: 2px solid #e9ecef;
            margin: 2rem 0 1.5rem 0;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Check if we have submitted data
    has_submitted_data = (
        hasattr(st.session_state, "form_data") and st.session_state.form_data
    )

    # Header - update title based on state
    header_title = (
        "Collaboration Index Results"
        if has_submitted_data
        else "Forward Plan Submission"
    )
    st.markdown(
        f"""
        <div class="main-header">
            <h1>{header_title}</h1>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Display results at the top if we have submitted data
    if has_submitted_data:
        # Display enhanced collaboration index (always visible)
        if "enhanced_collaboration_data" in st.session_state.form_data:
            display_enhanced_collaboration_index(
                st.session_state.form_data["enhanced_collaboration_data"],
                st.session_state.form_data.get("location_type_enum"),
                st.session_state.form_data.get("sector_type_enum"),
                st.session_state.form_data.get("ttro_required_enum"),
                st.session_state.form_data.get("installation_method_enum"),
            )

        # ENHANCED MAP WITH HEX GRIDS - AFTER THE COLLABORATION INDEX
        # Display USRN geometry map with NUAR hex grids
        usrn = st.session_state.form_data.get("usrn")
        street_info = st.session_state.form_data.get("street_info")
        if usrn:
            display_usrn_map_enhanced_with_corrosivity(usrn, street_info)

        # Hide detailed information under collapsible sections
        with st.expander("📋 View Submission Details", expanded=False):
            display_form_data(st.session_state.form_data)

        # Add this to display the street info under another collapsible section
        if st.session_state.form_data.get("street_info"):
            with st.expander("🗺️ View Street Information & Analysis", expanded=False):
                display_street_info(st.session_state.form_data["street_info"])

    # Only show the form if we don't have submitted data
    if not has_submitted_data:
        # Main form
        with st.form("street_works_form"):
            # Basic Information Section
            st.markdown("#### 📋 Basic Information")

            col1, col2 = st.columns(2)

            with col1:
                permit_ref = st.text_input(
                    "Permit Reference *",
                    placeholder="e.g., PER-2024-001234",
                    help="Enter the unique permit reference number",
                )

                swa_code: Optional[SWACode] = st.selectbox(
                    "SWA Code *",
                    options=get_enum_options(SWACode),
                    placeholder="Select SWA Code",
                    format_func=lambda x: x.label,
                    help="Select the Street Works Authority code",
                )

                location_type: Optional[LocationType] = st.selectbox(
                    "Location Type *",
                    options=get_enum_options(LocationType),
                    format_func=lambda x: x.label,  # Show the score in the dropdown
                    help="Select where the works will take place",
                )

            with col2:
                promoter_org: Optional[PromoterOrganisation] = st.selectbox(
                    "Promoter Organisation *",
                    options=get_enum_options(PromoterOrganisation),
                    format_func=lambda x: x.value,
                    help="Select the organisation promoting the works",
                )

                usrn = st.text_input(
                    "USRN *",
                    placeholder="e.g., 12345678",
                    help="Enter the Unique Street Reference Number",
                )

                sector_type: Optional[SectorType] = st.selectbox(
                    "Sector Type *",
                    options=get_enum_options(SectorType),
                    format_func=lambda x: x.label,
                    help="Select the utility sector and see dig depth",
                )

            # Work Details Section
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            st.markdown("#### 🔨 Work Details")

            col1, col2 = st.columns(2)

            with col1:
                work_start_date = st.date_input(
                    "Work Start Date *",
                    value=date.today(),
                    help="Select the planned start date for the works",
                )

                activity_type: Optional[ActivityType] = st.selectbox(
                    "Activity Type *",
                    options=get_enum_options(ActivityType),
                    format_func=lambda x: x.display_name,
                    help="Select the type of activity being performed",
                )

                installation_method: Optional[InstallationMethod] = st.selectbox(
                    "Installation Method *",
                    options=get_enum_options(InstallationMethod),
                    format_func=lambda x: x.label,
                    help="Select the installation method for the works",
                )

            with col2:
                work_end_date = st.date_input(
                    "Work End Date *",
                    value=date.today(),
                    help="Select the planned end date for the works",
                )

                ttro_required: Optional[TTRORequired] = st.selectbox(
                    "TTRO Required *",
                    options=get_enum_options(TTRORequired),
                    format_func=lambda x: x.label,  # Now shows score
                    help="Is a Temporary Traffic Regulation Order required?",
                )

            # Programme Information Section
            st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)
            st.markdown("#### 📊 Programme Information")

            capital_works_programme: Optional[ProgrammeType] = st.selectbox(
                "Capital Works Programme *",
                options=get_enum_options(ProgrammeType),
                format_func=lambda x: x.display_name,
                help="Select the type of capital works programme",
            )

            programme_of_works = st.text_area(
                "Programme of Works",
                placeholder="Enter additional details about the programme of works (optional)",
                help="Optional: Provide additional context or details about the works programme",
                height=100,
            )

            # Submit button
            st.markdown("---")
            submitted = st.form_submit_button(
                "📝 Submit Forward Plan", type="primary"
            )

            # Form validation and submission
            if submitted:
                # Check required fields with proper null checks
                required_field_checks = [
                    ("Permit Reference", permit_ref),
                    ("SWA Code", swa_code),
                    ("Promoter Organisation", promoter_org),
                    ("USRN", usrn),
                    ("Location Type", location_type),
                    ("Sector Type", sector_type),
                    ("Activity Type", activity_type),
                    ("Installation Method", installation_method),
                    ("TTRO Required", ttro_required),
                    ("Capital Works Programme", capital_works_programme),
                ]

                missing_fields = [
                    field
                    for field, value in required_field_checks
                    if not value or value is None
                ]

                if missing_fields:
                    st.error(
                        f"Please fill in the following required fields: {', '.join(missing_fields)}"
                    )
                elif work_end_date < work_start_date:
                    st.error("Work end date cannot be before work start date.")
                else:
                    # Fetch street info using the USRN
                    street_info = (
                        fetch_street_info(usrn.strip()) if usrn.strip() else None
                    )

                    # Calculate enhanced collaboration index with NUAR data and USRN
                    enhanced_collaboration_index = calculate_enhanced_collaboration_index(
                        location_type,
                        sector_type,
                        ttro_required,
                        installation_method,
                        street_info,  # Make sure this is the complete street_info object
                        usrn.strip(),  # Pass USRN for geometry fetching
                    )

                    # Store data and display success - with null checks
                    form_data = {
                        "permit_ref": permit_ref,
                        "swa_code": swa_code.label if swa_code else "Unknown",
                        "promoter_org": promoter_org.value
                        if promoter_org
                        else "Unknown",
                        "usrn": usrn,
                        "location_type": location_type.label
                        if location_type
                        else "Unknown",
                        "sector_type": sector_type.label if sector_type else "Unknown",
                        "work_start_date": work_start_date.strftime("%Y-%m-%d"),
                        "work_end_date": work_end_date.strftime("%Y-%m-%d"),
                        "activity_type": activity_type.display_name
                        if activity_type
                        else "Unknown",
                        "installation_method": installation_method.label
                        if installation_method
                        else "Unknown",
                        "ttro_required": ttro_required.label
                        if ttro_required
                        else "Unknown",
                        "capital_works_programme": capital_works_programme.display_name
                        if capital_works_programme
                        else "Unknown",
                        "programme_of_works": programme_of_works or "Not specified",
                        "collaboration_index": enhanced_collaboration_index[
                            "total_score"
                        ],
                        "enhanced_collaboration_data": enhanced_collaboration_index,
                        "location_type_enum": location_type,
                        "sector_type_enum": sector_type,
                        "ttro_required_enum": ttro_required,
                        "installation_method_enum": installation_method,
                        "street_info": street_info,
                    }

                    st.success("✅ Street works data submitted successfully!")
                    st.session_state.form_data = form_data
                    st.rerun()  # Refresh to show results

    # Sidebar with information
    with st.sidebar:
        st.markdown("### 📖 About")
        st.info("""
        This form captures essential information for street works planning 
        and coordination.
        """)

        st.markdown("### 📝 Required Fields")
        st.markdown("""
        - Permit Reference
        - SWA Code
        - Promoter Organisation
        - USRN
        - Location Type
        - Sector Type
        - Work Date Range
        - Activity Type
        - Installation Method
        - TTRO Required
        - Capital Works Programme
        """)

        st.markdown("### 🤝 Enhanced Collaboration Index")
        st.markdown("""
        **Base Factors:**
        - Location Type Score (1-10)
        - Sector Score (2-10)
        - TTRO Required (2-6)
        - Installation Method (1-8)
        
        **Asset Factors (NUAR Data):**
        - Asset Density Score (1-5)
        - Area Coverage Score (1-3)
        
        Higher scores indicate more complex works that may benefit from collaboration.
        """)

        st.markdown("### 💡 Tips")
        st.markdown("""
        - All required fields are marked with *
        - Sector Type shows dig depth information
        - Use clear, descriptive permit references
        - Ensure dates are realistic and in correct order
        - Programme of Works is optional but recommended
        """)


def display_bgs_data_info():
    """Display information about the loaded BGS data for debugging"""
    summary = get_bgs_data_summary()

    if summary:
        with st.expander("🔍 BGS Data Information", expanded=False):
            st.write(f"**Total Features:** {summary['total_features']}")

            st.write("**Score Distribution:**")
            for score, count in summary["score_distribution"].items():
                st.write(f"• Score {score}: {count} features")

            if summary["bounding_box"]:
                bbox = summary["bounding_box"]
                st.write("**Geographic Coverage:**")
                st.write(f"• Longitude: {bbox['min_lon']:.4f} to {bbox['max_lon']:.4f}")
                st.write(f"• Latitude: {bbox['min_lat']:.4f} to {bbox['max_lat']:.4f}")


if __name__ == "__main__":
    main()
