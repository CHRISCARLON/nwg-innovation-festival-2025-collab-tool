import streamlit as st
from typing import Optional, List, Dict, Any
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import folium_static
from loguru import logger
import io
import re

from streamlit_app import (
    fetch_street_info,
    calculate_enhanced_collaboration_index,
    get_collaboration_recommendation,
    create_hex_grids_geodataframe,
    filter_hex_grids_by_usrn_intersection,
    find_intersecting_bgs_corrosivity,
    get_corrosivity_color,
    connect_to_motherduck,
    convert_to_geodf_from_wkt,
)
from config import (
    LocationType,
    SectorType,
    TTRORequired,
    InstallationMethod,
    get_enum_options,
)


def fetch_multiple_usrns_geometry(usrns: List[str]) -> Dict[str, gpd.GeoDataFrame]:
    """Fetch geometry for multiple USRNs efficiently using a single query"""
    if not usrns:
        return {}
    
    try:
        con = connect_to_motherduck()
        schema = st.secrets["USRN_SCHEMA"]
        table_name = st.secrets["USRN_TABLE"]
        
        if not all([schema, table_name]):
            raise ValueError("Missing schema or table name environment variables")
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['?' for _ in usrns])
        query = f"""
            SELECT 
                usrn,
                geometry
            FROM {schema}.{table_name}
            WHERE usrn IN ({placeholders})
        """
        
        # Execute query with all USRNs at once
        df = con.execute(query, usrns).df()
        
        if df.empty:
            logger.warning(f"No geometry found for any of the {len(usrns)} USRNs")
            return {}
        
        # Group by USRN and convert each to GeoDataFrame
        result = {}
        for usrn in df['usrn'].unique():
            usrn_df = df[df['usrn'] == usrn].copy()
            try:
                geodf = convert_to_geodf_from_wkt(usrn_df)
                result[str(usrn)] = geodf
            except Exception as e:
                logger.error(f"Error converting geometry for USRN {usrn}: {e}")
                continue
        
        logger.info(f"Successfully fetched geometry for {len(result)} out of {len(usrns)} USRNs")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching multiple USRN geometries: {e}")
        st.error(f"Error fetching geometries: {e}")
        return {}


def calculate_multi_usrn_collaboration_index(
    usrns: List[str], 
    location_type, 
    sector_type, 
    ttro_required, 
    installation_method
) -> Dict[str, Any]:
    """Calculate collaboration index for multiple USRNs with progress tracking"""
    
    results = {
        "individual_results": {},
        "summary": {
            "total_usrns": len(usrns),
            "processed_usrns": 0,
            "failed_usrns": 0,
            "average_score": 0,
            "max_score": 0,
            "min_score": float('inf'),
            "high_priority_count": 0,
            "moderate_priority_count": 0,
            "low_priority_count": 0,
        }
    }
    
    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_scores = []
    
    for i, usrn in enumerate(usrns):
        usrn = usrn.strip()
        if not usrn:
            continue
            
        # Update progress
        progress = (i + 1) / len(usrns)
        progress_bar.progress(progress)
        status_text.text(f"Processing USRN {i+1}/{len(usrns)}: {usrn}")
        
        try:
            street_info = fetch_street_info(usrn)
            
            if street_info:
                collaboration_data = calculate_enhanced_collaboration_index(
                    location_type, sector_type, ttro_required, installation_method,
                    street_info, usrn
                )
                
                score = collaboration_data["total_score"]
                recommendation = get_collaboration_recommendation(score)
                
                results["individual_results"][usrn] = {
                    "street_info": street_info,
                    "collaboration_data": collaboration_data,
                    "score": score,
                    "recommendation": recommendation,
                    "street_name": street_info.get("street", {}).get("street_name", "Unknown"),
                    "town": street_info.get("street", {}).get("town", "Unknown"),
                }
                
                all_scores.append(score)
                results["summary"]["processed_usrns"] += 1
                
                # Count by priority level
                if score >= 80:
                    results["summary"]["high_priority_count"] += 1
                elif score >= 60:
                    results["summary"]["moderate_priority_count"] += 1
                else:
                    results["summary"]["low_priority_count"] += 1
                    
            else:
                results["summary"]["failed_usrns"] += 1
                logger.warning(f"Failed to fetch street info for USRN: {usrn}")
                
        except Exception as e:
            results["summary"]["failed_usrns"] += 1
            logger.error(f"Error processing USRN {usrn}: {e}")
    
    # Calculate final summary statistics
    if all_scores:
        results["summary"]["average_score"] = sum(all_scores) / len(all_scores)
        results["summary"]["max_score"] = max(all_scores)
        results["summary"]["min_score"] = min(all_scores)
    
    progress_bar.empty()
    status_text.empty()
    
    return results


def create_multi_usrn_map(usrns: List[str], results: Dict[str, Any]) -> Optional[folium.Map]:
    """Create a comprehensive map showing all USRNs with hex grids, BGS corrosivity, and collaboration scores"""
    
    # Fetch all geometries
    geometries = fetch_multiple_usrns_geometry(usrns)
    
    if not geometries:
        st.warning("No geometry data found for any USRNs")
        return None
    
    # Create map
    m = folium.Map(tiles="cartodbpositron")
    
    # Track bounds for fitting map
    all_bounds = []
    
    # Collect all hex grids and BGS data
    all_hex_grids = []
    all_bgs_data = []
    
    # Color mapping for collaboration scores
    def get_score_color(score):
        if score >= 80:
            return "#dc3545"  # Red - High priority
        elif score >= 60:
            return "#ffc107"  # Yellow - Moderate priority
        elif score >= 40:
            return "#fd7e14"  # Orange - Consider
        else:
            return "#28a745"  # Green - Low priority
    
    # Process each USRN to collect all data
    with st.spinner("Preparing comprehensive map data..."):
        for usrn, geodf in geometries.items():
            if geodf is not None and not geodf.empty:
                # Add to bounds
                bounds = geodf.total_bounds
                all_bounds.append(bounds)
                
                # Get street info and hex grids if available
                if usrn in results["individual_results"]:
                    street_info = results["individual_results"][usrn]["street_info"]
                    
                    # Process NUAR hex grids
                    if street_info:
                        stats = street_info.get("stats", {})
                        nuar_summary = stats.get("nuar_summary", {})
                        hex_ids = nuar_summary.get("hex_ids", [])
                        
                        if hex_ids:
                            try:
                                # Create hex grids for this USRN
                                all_hex_gdf = create_hex_grids_geodataframe(hex_ids)
                                if all_hex_gdf is not None and not all_hex_gdf.empty:
                                    # Filter to only hex grids that intersect this USRN
                                    filtered_hex_gdf = filter_hex_grids_by_usrn_intersection(all_hex_gdf, geodf)
                                    
                                    if filtered_hex_gdf is not None and not filtered_hex_gdf.empty:
                                        # Add USRN identifier to hex grids
                                        filtered_hex_gdf['source_usrn'] = usrn
                                        all_hex_grids.append(filtered_hex_gdf)
                                        
                                        # Update bounds to include hex grids
                                        hex_bounds = filtered_hex_gdf.total_bounds
                                        all_bounds.append(hex_bounds)
                                        
                            except Exception as e:
                                logger.warning(f"Error processing hex grids for USRN {usrn}: {e}")
                    
                    # Process BGS corrosivity data
                    try:
                        bgs_corrosivity_gdf, bgs_ids = find_intersecting_bgs_corrosivity(geodf, buffer_meters=100)
                        if bgs_corrosivity_gdf is not None and not bgs_corrosivity_gdf.empty:
                            # Add USRN identifier to BGS data
                            bgs_corrosivity_gdf['source_usrn'] = usrn
                            all_bgs_data.append(bgs_corrosivity_gdf)
                            
                            # Update bounds to include BGS data
                            bgs_bounds = bgs_corrosivity_gdf.total_bounds
                            all_bounds.append(bgs_bounds)
                            
                    except Exception as e:
                        logger.warning(f"Error processing BGS data for USRN {usrn}: {e}")
    
    # Combine all hex grids
    combined_hex_gdf = None
    if all_hex_grids:
        try:
            combined_hex_gdf = pd.concat(all_hex_grids, ignore_index=True)
            logger.info(f"Combined {len(combined_hex_gdf)} hex grids from {len(all_hex_grids)} USRNs")
        except Exception as e:
            logger.error(f"Error combining hex grids: {e}")
    
    # Combine all BGS data
    combined_bgs_gdf = None
    if all_bgs_data:
        try:
            combined_bgs_gdf = pd.concat(all_bgs_data, ignore_index=True)
            # Remove duplicates based on BGS feature ID
            if 'id' in combined_bgs_gdf.columns:
                combined_bgs_gdf = combined_bgs_gdf.drop_duplicates(subset=['id'])
            logger.info(f"Combined {len(combined_bgs_gdf)} unique BGS areas from {len(all_bgs_data)} USRNs")
        except Exception as e:
            logger.error(f"Error combining BGS data: {e}")
    
    # Fit map to show all data
    if all_bounds:
        min_lons = [b[0] for b in all_bounds]
        min_lats = [b[1] for b in all_bounds] 
        max_lons = [b[2] for b in all_bounds]
        max_lats = [b[3] for b in all_bounds]
        
        total_bounds = [
            min(min_lons), min(min_lats),
            max(max_lons), max(max_lats)
        ]
        
        m.fit_bounds([
            [total_bounds[1], total_bounds[0]], 
            [total_bounds[3], total_bounds[2]]
        ])
    
    # Add BGS corrosivity areas first (bottom layer)
    if combined_bgs_gdf is not None and not combined_bgs_gdf.empty:
        for _, row in combined_bgs_gdf.iterrows():
            if row.geometry is not None and not row.geometry.is_empty:
                score = row.get("score", "Unknown")
                border_color, fill_color = get_corrosivity_color(score)
                
                # Get source USRN for tooltip
                source_usrn = row.get("source_usrn", "Unknown")

                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x, border_color=border_color, fill_color=fill_color: {
                        "color": border_color,
                        "weight": 2,
                        "opacity": 0.7,
                        "fillColor": fill_color,
                        "fillOpacity": 0.2,
                    },
                    tooltip=folium.Tooltip(
                        f"<strong>BGS Corrosivity</strong><br>"
                        f"Score: {row.get('score', 'Unknown')}<br>"
                        f"Class: {row.get('class', 'Unknown')}<br>"
                        f"Risk: {row.get('legend', 'Unknown')}<br>"
                        f"Near USRN: {source_usrn}"
                    ),
                ).add_to(m)
    
    # Add hex grids (middle layer)
    if combined_hex_gdf is not None and not combined_hex_gdf.empty:
        # Calculate color scaling across ALL hex grids
        min_assets = combined_hex_gdf["asset_count"].min()
        max_assets = combined_hex_gdf["asset_count"].max()
        asset_range = max_assets - min_assets
        
        for _, row in combined_hex_gdf.iterrows():
            if row.geometry is not None and not row.geometry.is_empty:
                asset_count = row.get("asset_count", 0)
                source_usrn = row.get("source_usrn", "Unknown")
                
                # Color scaling logic (same as single USRN version)
                if asset_range <= 5:  # Low variance threshold
                    if max_assets > min_assets:
                        intensity = (asset_count - min_assets) / asset_range * 0.5
                    else:
                        intensity = 0.25
                    
                    if intensity <= 0.1:
                        color = "#e3f2fd"
                        fill_color = "#e3f2fd"
                    elif intensity <= 0.25:
                        color = "#bbdefb"
                        fill_color = "#bbdefb"
                    else:
                        color = "#90caf9"
                        fill_color = "#90caf9"
                else:
                    # Normal scaling for high variance
                    intensity = (asset_count - min_assets) / asset_range
                    
                    if intensity <= 0.2:
                        color = "#e3f2fd"
                        fill_color = "#e3f2fd"
                    elif intensity <= 0.4:
                        color = "#90caf9"
                        fill_color = "#90caf9"
                    elif intensity <= 0.6:
                        color = "#42a5f5"
                        fill_color = "#42a5f5"
                    elif intensity <= 0.8:
                        color = "#1e88e5"
                        fill_color = "#1e88e5"
                    else:
                        color = "#0d47a1"
                        fill_color = "#0d47a1"

                folium.GeoJson(
                    row.geometry.__geo_interface__,
                    style_function=lambda x, color=color, fill_color=fill_color: {
                        "color": color,
                        "weight": 1,
                        "opacity": 0.6,
                        "fillColor": fill_color,
                        "fillOpacity": 0.3,
                    },
                    tooltip=folium.Tooltip(
                        f"<strong>Hex Grid</strong><br>"
                        f"Asset Count: {row.get('asset_count', 0)}<br>"
                        f"Grid ID: {row.get('grid_id', 'Unknown')}<br>"
                        f"Zoom Level: {row.get('zoom_level', 'Unknown')}<br>"
                        f"USRN: {source_usrn}"
                    ),
                ).add_to(m)
    
    # Add USRNs (top layer) with collaboration score colors
    for usrn, geodf in geometries.items():
        if geodf is not None and not geodf.empty:
            # Get collaboration score and details
            score = 0
            street_name = "Unknown"
            recommendation_level = "Unknown"
            
            if usrn in results["individual_results"]:
                score = results["individual_results"][usrn]["score"]
                street_name = results["individual_results"][usrn]["street_name"]
                recommendation_level = results["individual_results"][usrn]["recommendation"]["level"]
            
            # Get color based on score
            usrn_color = get_score_color(score)
            
            # Add USRN to map
            for _, row in geodf.iterrows():
                if row.geometry is not None and not row.geometry.is_empty:
                    folium.GeoJson(
                        row.geometry.__geo_interface__,
                        style_function=lambda x, color=usrn_color: {
                            "color": color,
                            "weight": 5,
                            "opacity": 0.9,
                        },
                        tooltip=folium.Tooltip(
                            f"<strong>USRN:</strong> {usrn}<br>"
                            f"<strong>Street:</strong> {street_name}<br>"
                            f"<strong>Collaboration Score:</strong> {score}<br>"
                            f"<strong>Priority:</strong> {recommendation_level}"
                        ),
                    ).add_to(m)
    
    # Create comprehensive legend
    legend_parts = []
    
    # USRN collaboration priority legend
    usrn_legend = """
    <div style="margin-bottom: 15px;">
    <h4>🚧 Collaboration Priority</h4>
    <p><span style="color:#dc3545; font-weight: bold;">▬▬</span> High Priority (80+)</p>
    <p><span style="color:#ffc107; font-weight: bold;">▬▬</span> Moderate Priority (60-79)</p>
    <p><span style="color:#fd7e14; font-weight: bold;">▬▬</span> Consider (40-59)</p>
    <p><span style="color:#28a745; font-weight: bold;">▬▬</span> Low Priority (<40)</p>
    </div>
    """
    legend_parts.append(usrn_legend)
    
    # Hex grids legend (if present)
    if combined_hex_gdf is not None and not combined_hex_gdf.empty:
        min_assets = combined_hex_gdf["asset_count"].min()
        max_assets = combined_hex_gdf["asset_count"].max()
        asset_range = max_assets - min_assets
        
        if asset_range <= 5:  # Low variance
            hex_legend = f"""
            <div style="margin-bottom: 15px;">
            <h4>🔵 NUAR Asset Density</h4>
            <p><em>Low variance ({min_assets}-{max_assets})</em></p>
            <p><span style="color:#e3f2fd; background:#e3f2fd;">⬣</span> {min_assets} assets</p>
            <p><span style="color:#90caf9; background:#90caf9;">⬣</span> {max_assets} assets</p>
            </div>
            """
        else:  # Normal variance
            hex_legend = f"""
            <div style="margin-bottom: 15px;">
            <h4>🔵 NUAR Asset Density</h4>
            <p><span style="color:#e3f2fd; background:#e3f2fd;">⬣</span> Very Low ({min_assets})</p>
            <p><span style="color:#90caf9; background:#90caf9;">⬣</span> Low</p>
            <p><span style="color:#42a5f5; background:#42a5f5;">⬣</span> Medium</p>
            <p><span style="color:#1e88e5; background:#1e88e5;">⬣</span> High</p>
            <p><span style="color:#0d47a1; background:#0d47a1;">⬣</span> Very High ({max_assets})</p>
            </div>
            """
        legend_parts.append(hex_legend)
    
    # BGS corrosivity legend (if present)
    if combined_bgs_gdf is not None and not combined_bgs_gdf.empty:
        bgs_legend = """
        <div style="margin-bottom: 15px;">
        <h4>⚠️ BGS Corrosivity Risk</h4>
        <p><span style="color:#32CD32; background:#98FB98;">▬</span> Low Risk (&lt;5)</p>
        <p><span style="color:#FFD700; background:#FFFF99;">▬</span> Medium Risk (5-7)</p>
        <p><span style="color:#FF8C00; background:#FFA500;">▬</span> High Risk (8-10)</p>
        <p><span style="color:#8B0000; background:#FF4444;">▬</span> Very High Risk (&gt;11)</p>
        </div>
        """
        legend_parts.append(bgs_legend)
    
    # Combine legends
    if legend_parts:
        legend_height = max(200, len(legend_parts) * 140)
        legend_html = f"""
        <div style="position: fixed; 
                    bottom: 50px; right: 50px; width: 260px; height: {legend_height}px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:13px; padding: 12px; overflow-y: auto;
                    border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                    ">
        {"".join(legend_parts)}
        </div>
        """
        m.get_root().add_child(folium.Element(legend_html))
    
    # Add summary info to map
    processed_count = len([usrn for usrn in usrns if usrn in results["individual_results"]])
    summary_info = f"""
    <div style="position: fixed; 
                top: 80px; left: 50px; width: 250px; 
                background-color: white; border:2px solid grey; z-index:9999; 
                font-size:14px; padding: 12px; border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                ">
    <h4 style="margin: 0 0 10px 0;">📊 Analysis Summary</h4>
    <p style="margin: 5px 0;"><strong>Total USRNs:</strong> {len(usrns)}</p>
    <p style="margin: 5px 0;"><strong>Processed:</strong> {processed_count}</p>
    <p style="margin: 5px 0;"><strong>Avg Score:</strong> {results['summary']['average_score']:.1f}</p>
    <p style="margin: 5px 0;"><strong>High Priority:</strong> {results['summary']['high_priority_count']}</p>
    </div>
    """
    m.get_root().add_child(folium.Element(summary_info))
    
    return m


def display_multi_usrn_summary(results: Dict[str, Any]):
    """Display summary statistics for multiple USRNs"""
    summary = results["summary"]
    
    # Summary metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total USRNs", 
            summary["total_usrns"],
            help="Total number of USRNs submitted"
        )
    
    with col2:
        st.metric(
            "Successfully Processed", 
            summary["processed_usrns"],
            help="USRNs with complete data and collaboration scores"
        )
    
    with col3:
        st.metric(
            "Failed to Process", 
            summary["failed_usrns"],
            help="USRNs that couldn't be processed due to missing data or errors"
        )
    
    with col4:
        avg_score = summary["average_score"]
        st.metric(
            "Average Score", 
            f"{avg_score:.1f}" if avg_score > 0 else "N/A",
            help="Average collaboration index score across all processed USRNs"
        )
    
    # Priority distribution
    if summary["processed_usrns"] > 0:
        st.markdown("### 📊 Priority Distribution")
        
        priority_col1, priority_col2, priority_col3 = st.columns(3)
        
        with priority_col1:
            st.markdown(
                f"""
                <div style="background: #dc3545; color: white; padding: 1rem; border-radius: 8px; text-align: center;">
                    <h3 style="margin: 0;">🔴 HIGH PRIORITY</h3>
                    <h2 style="margin: 0.5rem 0 0 0;">{summary["high_priority_count"]}</h2>
                    <p style="margin: 0;">USRNs (Score 80+)</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        with priority_col2:
            st.markdown(
                f"""
                <div style="background: #ffc107; color: black; padding: 1rem; border-radius: 8px; text-align: center;">
                    <h3 style="margin: 0;">🟡 MODERATE PRIORITY</h3>
                    <h2 style="margin: 0.5rem 0 0 0;">{summary["moderate_priority_count"]}</h2>
                    <p style="margin: 0;">USRNs (Score 60-79)</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        with priority_col3:
            st.markdown(
                f"""
                <div style="background: #28a745; color: white; padding: 1rem; border-radius: 8px; text-align: center;">
                    <h3 style="margin: 0;">🟢 LOW PRIORITY</h3>
                    <h2 style="margin: 0.5rem 0 0 0;">{summary["low_priority_count"]}</h2>
                    <p style="margin: 0;">USRNs (Score <60)</p>
                </div>
                """,
                unsafe_allow_html=True,
            )


def display_detailed_results_table(results: Dict[str, Any]):
    """Display detailed results in a sortable table"""
    if not results["individual_results"]:
        st.warning("No detailed results to display")
        return
    
    # Prepare data for table
    table_data = []
    for usrn, data in results["individual_results"].items():
        table_data.append({
            "USRN": usrn,
            "Street Name": data["street_name"],
            "Town": data["town"],
            "Collaboration Score": data["score"],
            "Priority Level": data["recommendation"]["level"],
            "Base Score": data["collaboration_data"]["breakdown"]["base_factors"]["subtotal"],
            "Asset Score": data["collaboration_data"]["breakdown"]["nuar_factors"]["subtotal"],
            "Designation Score": data["collaboration_data"]["breakdown"]["designation_factors"]["subtotal"],
            "Work History Score": data["collaboration_data"]["breakdown"].get("work_history_factors", {}).get("subtotal", 0),
        })
    
    # Create DataFrame
    df = pd.DataFrame(table_data)
    
    # Sort by collaboration score descending
    df = df.sort_values("Collaboration Score", ascending=False)
    
    # Display with styling
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "USRN": st.column_config.TextColumn("USRN", width="medium"),
            "Street Name": st.column_config.TextColumn("Street Name", width="large"),
            "Town": st.column_config.TextColumn("Town", width="medium"),
            "Collaboration Score": st.column_config.NumberColumn(
                "Score", 
                format="%.1f",
                width="small"
            ),
            "Priority Level": st.column_config.TextColumn("Priority", width="medium"),
            "Base Score": st.column_config.NumberColumn("Base", format="%.0f", width="small"),
            "Asset Score": st.column_config.NumberColumn("Assets", format="%.0f", width="small"),
            "Designation Score": st.column_config.NumberColumn("Designation", format="%.0f", width="small"),
            "Work History Score": st.column_config.NumberColumn("Work History", format="%.0f", width="small"),
        }
    )


def create_results_download(results: Dict[str, Any]) -> bytes:
    """Create downloadable CSV of results"""
    if not results["individual_results"]:
        return b""
    
    csv_data = []
    for usrn, data in results["individual_results"].items():
        breakdown = data["collaboration_data"]["breakdown"]
        csv_data.append({
            "USRN": usrn,
            "Street_Name": data["street_name"],
            "Town": data["town"],
            "Collaboration_Score": data["score"],
            "Priority_Level": data["recommendation"]["level"],
            "Recommendation": data["recommendation"]["recommendation"],
            "Base_Score": breakdown["base_factors"]["subtotal"],
            "Location_Score": breakdown["base_factors"]["location"],
            "Sector_Score": breakdown["base_factors"]["sector"],
            "TTRO_Score": breakdown["base_factors"]["ttro"],
            "Installation_Score": breakdown["base_factors"]["installation"],
            "Asset_Score": breakdown["nuar_factors"]["subtotal"],
            "Asset_Density_Score": breakdown["nuar_factors"]["asset_density"],
            "Coverage_Score": breakdown["nuar_factors"]["coverage"],
            "Total_Assets": breakdown.get("asset_metrics", {}).get("total_assets", 0),
            "Hex_Grids": breakdown.get("asset_metrics", {}).get("hex_grids", 0),
            "Asset_Density": breakdown.get("asset_metrics", {}).get("asset_density", 0),
            "Designation_Score": breakdown["designation_factors"]["subtotal"],
            "Winter_Maintenance": breakdown["designation_factors"]["winter_maintenance"],
            "Traffic_Sensitive": breakdown["designation_factors"]["traffic_sensitive"],
            "Environmental_Sensitive": breakdown["designation_factors"]["environmentally_sensitive"],
            "Work_History_Score": breakdown.get("work_history_factors", {}).get("subtotal", 0),
            "Organization_Count": breakdown.get("work_history_details", {}).get("organization_count", 0),
            "Total_Works": breakdown.get("work_history_details", {}).get("total_works", 0),
            "Sector_Count": breakdown.get("work_history_details", {}).get("sector_count", 0),
        })
    
    df = pd.DataFrame(csv_data)
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode('utf-8')


def parse_usrns_from_text(text_input: str) -> List[str]:
    """
    Parse USRNs from text input, handling various formats:
    - Newline separated
    - Comma separated  
    - Space separated
    - Mixed formats
    """
    if not text_input:
        return []
    
    cleaned = re.sub(r'[,;\t]+', '\n', text_input)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.replace(' ', '\n')
    
    raw_usrns = cleaned.split('\n')
    
    usrns = []
    for usrn in raw_usrns:
        cleaned_usrn = usrn.strip()
        
        if not cleaned_usrn:
            continue
            
        if cleaned_usrn.isdigit() and 6 <= len(cleaned_usrn) <= 12:
            usrns.append(cleaned_usrn)
        else:
            logger.warning(f"Skipping invalid USRN format: '{cleaned_usrn}'")
    
    return usrns


def validate_usrns(usrns: List[str]) -> tuple[List[str], List[str]]:
    """
    Validate USRNs and return valid ones and invalid ones separately
    """
    valid_usrns = []
    invalid_usrns = []
    
    for usrn in usrns:
        # Basic validation - should be numeric and reasonable length
        if usrn.isdigit() and 6 <= len(usrn) <= 12:
            valid_usrns.append(usrn)
        else:
            invalid_usrns.append(usrn)
    
    return valid_usrns, invalid_usrns


def main():
    # Page configuration
    st.set_page_config(
        page_title="Multi-USRN Collaboration Analysis",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    
    # Custom CSS (reuse from main app)
    st.markdown(
        """
        <style>
        .main-header {
            text-align: center;
            padding: 2rem 0;
            background: linear-gradient(90deg, #6f42c1 0%, #5a2d91 100%);
            color: white;
            margin: -1rem -1rem 2rem -1rem;
            border-radius: 0 0 10px 10px;
        }
        .stButton > button {
            background-color: #6f42c1 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            width: 100% !important;
        }
        .stButton > button:hover {
            background-color: #5a2d91 !important;
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 8px rgba(111, 66, 193, 0.3) !important;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )
    
    # Header
    st.markdown(
        """
        <div class="main-header">
            <h1>🚧 Multi-USRN Collaboration Analysis</h1>
            <p style="margin: 0; opacity: 0.9;">Batch processing for multiple street works assessments</p>
        </div>
    """,
        unsafe_allow_html=True,
    )
    
    has_results = hasattr(st.session_state, "multi_usrn_results") and st.session_state.multi_usrn_results
    
    if has_results:
        results = st.session_state.multi_usrn_results
        
        # Summary
        st.markdown("## 📊 Analysis Summary")
        display_multi_usrn_summary(results)
        
        # Map
        st.markdown("## 🗺️ Collaboration Priority Map")
        usrns = list(results["individual_results"].keys())
        if usrns:
            map_obj = create_multi_usrn_map(usrns, results)
            if map_obj:
                folium_static(map_obj, width=None, height=600)
        
        # Detailed results
        with st.expander("📋 Detailed Results Table", expanded=True):
            display_detailed_results_table(results)
        
        # Download results
        st.markdown("## 💾 Download Results")
        csv_data = create_results_download(results)
        if csv_data:
            st.download_button(
                label="📥 Download Detailed Results (CSV)",
                data=csv_data,
                file_name=f"multi_usrn_collaboration_analysis_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # New analysis button
        if st.button("🔄 Start New Analysis", use_container_width=True):
            del st.session_state.multi_usrn_results
            st.rerun()
    
    else:
        # Input form
        with st.form("multi_usrn_form"):
            # Input method selection
            st.markdown("### 📝 Input Method")
            input_method = st.radio(
                "How would you like to provide USRNs?",
                ["Text Input (Multiple USRNs)", "Upload CSV File"],
                horizontal=True,
                help="Choose your preferred method for providing multiple USRNs"
            )
            
            usrns = []
            
            if input_method == "Text Input (Multiple USRNs)":
                usrn_input = st.text_area(
                    "USRNs *",
                    placeholder="Enter USRNs separated by:\n• New lines\n• Commas\n• Spaces\n• Mixed formats\n\nExample:\n12345678, 87654321\n11223344 99887766\n55443322",
                    height=120,
                    help="Enter multiple USRNs using any common separator (newlines, commas, spaces, etc.)"
                )
                
                if usrn_input:
                    parsed_usrns = parse_usrns_from_text(usrn_input)
                    
                    valid_usrns, invalid_usrns = validate_usrns(parsed_usrns)
                    
                    if valid_usrns:
                        usrns = valid_usrns
                        
                        # Show success message with count
                        if invalid_usrns:
                            st.warning(f"✅ Found {len(valid_usrns)} valid USRNs. ⚠️ Skipped {len(invalid_usrns)} invalid entries: {', '.join(invalid_usrns[:5])}{'...' if len(invalid_usrns) > 5 else ''}")
                        else:
                            st.success(f"✅ Found {len(valid_usrns)} valid USRNs")
                        
                        # Show preview of valid USRNs
                        with st.expander("👀 Preview Valid USRNs"):
                            preview_df = pd.DataFrame({
                                "USRN": valid_usrns[:20],  # Show first 20
                                "Status": ["✅ Valid"] * min(20, len(valid_usrns))
                            })
                            st.dataframe(preview_df, hide_index=True, use_container_width=True)
                            if len(valid_usrns) > 20:
                                st.write(f"... and {len(valid_usrns) - 20} more valid USRNs")
                            
                            # Also show invalid ones if any
                            if invalid_usrns:
                                st.markdown("**Invalid entries that will be skipped:**")
                                invalid_df = pd.DataFrame({
                                    "Entry": invalid_usrns[:10],  # Show first 10 invalid
                                    "Issue": ["❌ Invalid format"] * min(10, len(invalid_usrns))
                                })
                                st.dataframe(invalid_df, hide_index=True, use_container_width=True)
                                if len(invalid_usrns) > 10:
                                    st.write(f"... and {len(invalid_usrns) - 10} more invalid entries")
                    
                    elif invalid_usrns:
                        st.error(f"❌ No valid USRNs found. All {len(invalid_usrns)} entries have invalid format.")
                        st.info("💡 USRNs should be 6-12 digit numbers. Check your input format.")
                        
                        # Show what was parsed
                        with st.expander("🔍 Show what was detected"):
                            for i, invalid in enumerate(invalid_usrns[:10], 1):
                                st.write(f"{i}. '{invalid}' - Invalid format")
                            if len(invalid_usrns) > 10:
                                st.write(f"... and {len(invalid_usrns) - 10} more")
            
            elif input_method == "Upload CSV File":
                uploaded_file = st.file_uploader(
                    "Choose CSV file *",
                    type=['csv'],
                    help="Upload a CSV file with a 'usrn' column containing the USRNs to process"
                )
                
                if uploaded_file:
                    try:
                        df = pd.read_csv(uploaded_file)
                        
                        if 'usrn' in df.columns:
                            raw_usrns = df['usrn'].astype(str).str.strip().tolist()
                            
                            raw_usrns = [usrn for usrn in raw_usrns if usrn and usrn.lower() != 'nan']
                            
                            valid_usrns, invalid_usrns = validate_usrns(raw_usrns)
                            
                            if valid_usrns:
                                usrns = valid_usrns
                                
                                if invalid_usrns:
                                    st.warning(f"✅ Loaded {len(valid_usrns)} valid USRNs from file. ⚠️ Skipped {len(invalid_usrns)} invalid entries.")
                                else:
                                    st.success(f"✅ Loaded {len(valid_usrns)} valid USRNs from file")
                                
                                # Show preview
                                with st.expander("👀 Preview Loaded USRNs"):
                                    preview_df = pd.DataFrame({
                                        "USRN": valid_usrns[:20],
                                        "Status": ["✅ Valid"] * min(20, len(valid_usrns))
                                    })
                                    st.dataframe(preview_df, hide_index=True, use_container_width=True)
                                    if len(valid_usrns) > 20:
                                        st.write(f"... and {len(valid_usrns) - 20} more valid USRNs")
                                        
                                    if invalid_usrns:
                                        st.markdown("**Invalid entries skipped:**")
                                        invalid_preview = invalid_usrns[:5]
                                        for invalid in invalid_preview:
                                            st.write(f"❌ '{invalid}' - Invalid format")
                                        if len(invalid_usrns) > 5:
                                            st.write(f"... and {len(invalid_usrns) - 5} more invalid entries")
                                
                            else:
                                st.error(f"❌ No valid USRNs found in the uploaded file. All {len(raw_usrns)} entries have invalid format.")
                                
                        else:
                            st.error("❌ CSV file must contain a 'usrn' column")
                            st.info("📁 Expected format: CSV file with at least one column named 'usrn'")
                            
                            # Show available columns
                            available_cols = df.columns.tolist()
                            st.write(f"Available columns in your file: {', '.join(available_cols)}")
                    
                    except Exception as e:
                        st.error(f"❌ Error reading CSV file: {e}")
            
            # Work parameters (same as single USRN form)
            st.markdown("### 🔨 Work Parameters")
            st.info("These parameters will be applied to all USRNs in the analysis")
            
            col1, col2 = st.columns(2)
            
            with col1:
                location_type: Optional[LocationType] = st.selectbox(
                    "Location Type *",
                    options=get_enum_options(LocationType),
                    format_func=lambda x: x.label,
                    help="Select where the works will take place"
                )
                
                sector_type: Optional[SectorType] = st.selectbox(
                    "Sector Type *",
                    options=get_enum_options(SectorType),
                    format_func=lambda x: x.label,
                    help="Select the utility sector"
                )
            
            with col2:
                ttro_required: Optional[TTRORequired] = st.selectbox(
                    "TTRO Required *",
                    options=get_enum_options(TTRORequired),
                    format_func=lambda x: x.label,
                    help="Is a Temporary Traffic Regulation Order required?"
                )
                
                installation_method: Optional[InstallationMethod] = st.selectbox(
                    "Installation Method *",
                    options=get_enum_options(InstallationMethod),
                    format_func=lambda x: x.label,
                    help="Select the installation method for the works"
                )
            
            # Submit button
            st.markdown("---")
            submitted = st.form_submit_button(
                "🚀 Analyze Multiple USRNs", 
                type="primary",
                use_container_width=True
            )
            
            # Form validation and processing
            if submitted:
                # Validation
                if not usrns:
                    st.error("❌ Please provide at least one USRN")
                elif len(usrns) > 100:  # Limit for performance
                    st.error("❌ Please limit to 100 USRNs maximum per analysis")
                elif not all([location_type, sector_type, ttro_required, installation_method]):
                    st.error("❌ Please fill in all work parameters")
                else:
                    # Process USRNs
                    with st.spinner(f"Processing {len(usrns)} USRNs..."):
                        results = calculate_multi_usrn_collaboration_index(
                            usrns, location_type, sector_type, ttro_required, installation_method
                        )
                        
                        # Store results in session state
                        st.session_state.multi_usrn_results = results
                        
                        st.success(f"✅ Analysis complete! Processed {results['summary']['processed_usrns']} out of {len(usrns)} USRNs")
                        st.rerun()
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 📖 About Multi-USRN Analysis")
        st.info(
            """
            This tool allows you to analyze collaboration potential for multiple 
            street works locations simultaneously.
            """
        )
        
        st.markdown("### 📊 What You Get")
        st.markdown(
            """
            - **Batch Processing**: Analyze up to 100 USRNs at once
            - **Visual Map**: See all locations color-coded by priority
            - **Summary Statistics**: Overview of collaboration potential
            - **Detailed Table**: Sortable results with all metrics
            - **CSV Export**: Download results for further analysis
            """
        )
        
        st.markdown("### 💡 Input Options")
        st.markdown(
            """
            **Text Input:**
            - Paste USRNs one per line
            - Or use comma-separated format
            - Mix of formats is supported
            
            **CSV Upload:**
            - Must have 'usrn' column
            - Other columns are ignored
            - Supports standard CSV format
            """
        )
        
        st.markdown("### 🎯 Priority Levels")
        st.markdown(
            """
            - **🔴 High (80+)**: Strong collaboration potential
            - **🟡 Moderate (60-79)**: Good opportunities  
            - **🟠 Consider (40-59)**: Some potential
            - **🟢 Low (<40)**: Limited benefits
            """
        )

        st.markdown("### 📝 Input Format Examples")
        st.markdown(
            """
            **Text Input Examples:**
            ```
            12345678
            87654321
            11223344
            ```
            
            ```
            12345678, 87654321, 11223344
            ```
            
            ```
            12345678 87654321 11223344
            ```
            
            **Mixed formats work too:**
            ```
            12345678, 87654321
            11223344 99887766
            55443322
            ```
            """
        )


if __name__ == "__main__":
    main() 