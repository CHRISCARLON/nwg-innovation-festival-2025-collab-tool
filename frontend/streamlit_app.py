import streamlit as st
from datetime import date
from typing import Optional
import requests  # Add this import
import pandas as pd
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


def fetch_street_info(usrn: str):
    """Fetch street info from the backend API"""
    try:
        response = requests.get(f"http://localhost:8080/street-info?usrn={usrn}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching street info: {e}")
        return None


def calculate_enhanced_collaboration_index(
    location_type,
    sector_type,
    ttro_required,
    installation_method,
    street_info_data=None,
):
    """Calculate enhanced collaboration index including NUAR asset data and special designations"""
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

    if street_info_data:
        # Process NUAR data
        stats = street_info_data.get("stats", {})
        nuar_summary = stats.get("nuar_summary", {})

        # Check if NUAR data exists and is valid
        if nuar_summary and nuar_summary.get("total_asset_count") is not None:
            total_assets = nuar_summary.get("total_asset_count", 0)
            total_grids = nuar_summary.get("total_hex_grids", 0)

            if total_assets > 0 and total_grids > 0:
                # Calculate asset density
                asset_density = total_assets / total_grids

                # Asset density scoring (higher density = more underground assets = higher collaboration potential)
                if asset_density >= 20:
                    asset_density_score = 5  # High density
                elif asset_density >= 15:
                    asset_density_score = 3  # Medium density
                elif asset_density >= 10:
                    asset_density_score = 2  # Low-medium density
                else:
                    asset_density_score = 1  # Low density

                # Grid coverage scoring (more grids = larger area = more coordination needed)
                if total_grids >= 15:
                    coverage_score = 3  # Large area
                elif total_grids >= 10:
                    coverage_score = 2  # Medium area
                else:
                    coverage_score = 1  # Small area

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

    # Calculate total designation bonus
    total_designation_score = sum(designation_scores.values())

    # Calculate final enhanced score
    enhanced_score = (
        base_score + asset_density_score + coverage_score + total_designation_score
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
            "asset_metrics": asset_metrics,
            "designation_details": designation_details,
        },
    }


def get_collaboration_recommendation(score):
    """Get collaboration recommendation based on score"""
    if score >= 35:
        return {
            "level": "🟢 HIGH PRIORITY",
            "recommendation": "Strong recommendation for collaborative working due to high underground asset density and complex work requirements.",
            "score_range": "35+",
            "color": "#28a745",
        }
    elif score >= 30:
        return {
            "level": "🟡 MODERATE PRIORITY",
            "recommendation": "Good opportunity for collaboration with moderate asset density and work complexity.",
            "score_range": "30-34",
            "color": "#ffc107",
        }
    elif score >= 25:
        return {
            "level": "🟠 CONSIDER",
            "recommendation": "Some collaboration potential but may depend on timing and resource availability.",
            "score_range": "25-29",
            "color": "#fd7e14",
        }
    else:
        return {
            "level": "🔴 LOW PRIORITY",
            "recommendation": "Limited collaboration benefits expected based on current metrics.",
            "score_range": "< 25",
            "color": "#dc3545",
        }


def display_enhanced_collaboration_index(
    collaboration_data, location_type, sector_type, ttro_required, installation_method
):
    """Display the enhanced collaboration index with NUAR data and special designations"""
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

    st.markdown(
        f"""
        <div class="collaboration-index">
            <h2>🤝 Enhanced Collaboration Index</h2>
            <div class="collaboration-score">{score}</div>
            <div class="collaboration-subtitle">
                <strong>Base Factors:</strong> Location ({breakdown["base_factors"]["location"]}) + 
                Sector ({breakdown["base_factors"]["sector"]}) + 
                TTRO ({breakdown["base_factors"]["ttro"]}) + 
                Installation ({breakdown["base_factors"]["installation"]}) = {breakdown["base_factors"]["subtotal"]}
            </div>
            <div class="collaboration-subtitle">
                <strong>Asset Factors:</strong> Density ({breakdown["nuar_factors"]["asset_density"]}) + 
                Coverage ({breakdown["nuar_factors"]["coverage"]}) = {breakdown["nuar_factors"]["subtotal"]}
            </div>
            <div class="collaboration-subtitle">
                <strong>Designation Factors:</strong> Winter Maint. ({breakdown["designation_factors"]["winter_maintenance"]}) + 
                Traffic Sensitive ({breakdown["designation_factors"]["traffic_sensitive"]}) + 
                Env. Sensitive ({breakdown["designation_factors"]["environmentally_sensitive"]}) = {breakdown["designation_factors"]["subtotal"]}
            </div>
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

        # Display NUAR summary if available
        if "nuar_summary" in stats:
            st.markdown("---")
            st.markdown("**🏗️ Underground Asset Summary:**")
            nuar_summary = stats["nuar_summary"]

            if nuar_summary.get("error"):
                st.warning(f"NUAR Data Error: {nuar_summary['error']}")
            else:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Assets", nuar_summary.get("total_asset_count", 0))
                with col2:
                    st.metric("Hex Grids", nuar_summary.get("total_hex_grids", 0))
                with col3:
                    density = (
                        nuar_summary.get("total_asset_count", 0)
                        / nuar_summary.get("total_hex_grids", 1)
                        if nuar_summary.get("total_hex_grids", 0) > 0
                        else 0
                    )
                    st.metric("Asset Density", f"{density:.1f}/grid")

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
        # Display enhanced collaboration index
        if "enhanced_collaboration_data" in st.session_state.form_data:
            display_enhanced_collaboration_index(
                st.session_state.form_data["enhanced_collaboration_data"],
                st.session_state.form_data.get("location_type_enum"),
                st.session_state.form_data.get("sector_type_enum"),
                st.session_state.form_data.get("ttro_required_enum"),
                st.session_state.form_data.get("installation_method_enum"),
            )

        # Then display the form data
        display_form_data(st.session_state.form_data)

        # Add this to display the street info
        if st.session_state.form_data.get("street_info"):
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
                "📝 Submit Street Works Data", type="primary"
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

                    # Calculate enhanced collaboration index with NUAR data
                    enhanced_collaboration_index = calculate_enhanced_collaboration_index(
                        location_type,
                        sector_type,
                        ttro_required,
                        installation_method,
                        street_info,  # Make sure this is the complete street_info object
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
                        "street_info": street_info,  # Add the fetched street info
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


if __name__ == "__main__":
    main()
