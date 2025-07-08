import streamlit as st
import requests

# Configuration
API_BASE_URL = "http://localhost:8080"


def fetch_collaborative_street_works(usrn):
    """
    Fetch collaborative street works recommendations for a given USRN
    """
    try:
        params = {"usrn": usrn}

        with st.spinner("We're preparing your recommendations! Go get a brew ☕️"):
            response = requests.get(
                f"{API_BASE_URL}/collaborative-street-works", params=params, timeout=30
            )
            response.raise_for_status()
            return response.json()

    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return None
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return None


def display_section_as_expander(title, items, icon="📋"):
    """Display a section as an expander with proper bullet formatting"""
    if items and items != ["NO DATA"]:
        with st.expander(f"{icon} {title}", expanded=True):
            for item in items:
                if item and item != "NO DATA":
                    st.write(f"• {item}")


def display_llm_summary(llm_data):
    """Display the LLM summary using expanders for better formatting"""

    # Summary first - highlight this as the main recommendation
    if "summary" in llm_data:
        st.markdown(
            f"""
            <div class="summary-container">
                <h3>🎯 Recommendation & Summary</h3>
                <p class="summary-text">{llm_data["summary"]}</p>
            </div>
        """,
            unsafe_allow_html=True,
        )

    # Define the sections to display in order
    sections = [
        ("📍 Location", "location"),
        ("🔑 Key Characteristics", "key_characteristics"),
        ("🔨 Past Work History", "past_work_history"),
        ("⚠️ Special Designations", "special_designations"),
        ("⚡ Potential Challenges", "potential_challenges"),
        ("🏠 Property Numbers", "property_numbers"),
        ("🏛️ Institutional Properties", "institutional_properties"),
        ("🏘️ Residential Properties", "residential_properties"),
        ("🏢 Commercial Properties", "commercial_properties"),
        ("🔄 Recent Changes", "recent_changes"),
    ]

    # Create two columns for layout
    col1, col2 = st.columns(2)

    # Split sections between columns
    left_sections = sections[: len(sections) // 2]
    right_sections = sections[len(sections) // 2 :]

    with col1:
        for section_title, section_key in left_sections:
            if section_key in llm_data and llm_data[section_key]:
                display_section_as_expander(section_title, llm_data[section_key])

    with col2:
        for section_title, section_key in right_sections:
            if section_key in llm_data and llm_data[section_key]:
                display_section_as_expander(section_title, llm_data[section_key])


def main():
    # Page configuration
    st.set_page_config(
        page_title="Collaborative Street Works Tool",
        page_icon="🤝",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

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
        .stTextInput > div > div > input {
            background-color: #f8f9fa;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            padding: 0.5rem;
        }
        /* Green button styling */
        .stButton > button {
            background-color: #28a745 !important;
            color: white !important;
            border: none !important;
            border-radius: 8px !important;
            padding: 0.5rem 1rem !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
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
        .summary-container {
            background: linear-gradient(135deg, #4a90e2 0%, #2c5aa0 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0 2rem 0;
            box-shadow: 0 4px 15px rgba(74, 144, 226, 0.3);
        }
        .summary-container h3 {
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }
        .summary-text {
            font-size: 1rem;
            line-height: 1.5;
            margin: 0;
        }
        .stExpander {
            margin-bottom: 0.5rem;
        }
        .stExpander > div > div > div > div {
            padding-top: 0.5rem;
        }
        </style>
    """,
        unsafe_allow_html=True,
    )

    # Header
    st.markdown(
        """
        <div class="main-header">
            <h1>🤝 Collaborative Street Works Tool</h1>
            <p>Get AI-powered recommendations for collaborative street works</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    # Main interface
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Enter Street Information")

        # USRN input
        usrn = st.text_input(
            "USRN (Unique Street Reference Number)",
            placeholder="Enter USRN (e.g., 12345678)",
            help="Enter the USRN for the street you want to analyse",
        )

        # Fetch button
        if st.button(
            "🔍 Generate Recommendations",
            type="primary",
            use_container_width=True,
            disabled=not usrn.strip(),
            key="generate_btn",
        ):
            if usrn.strip():
                result = fetch_collaborative_street_works(usrn.strip())

                if result:
                    st.session_state.result = result
                    st.session_state.usrn = usrn.strip()

    # Display results if available
    if hasattr(st.session_state, "result") and st.session_state.result:
        st.markdown("---")
        st.markdown(f"### 📊 Analysis Results for USRN: {st.session_state.usrn}")

        # Extract LLM summary if available
        if (
            isinstance(st.session_state.result, dict)
            and "llm_summary" in st.session_state.result
        ):
            display_llm_summary(st.session_state.result["llm_summary"])
        else:
            # Fallback for other data structures
            if isinstance(st.session_state.result, str):
                st.markdown(st.session_state.result)
            elif isinstance(st.session_state.result, dict):
                for key, value in st.session_state.result.items():
                    st.markdown(f"**{key.title().replace('_', ' ')}:**")
                    if isinstance(value, (dict, list)):
                        st.json(value)
                    else:
                        st.write(value)
            else:
                st.write(st.session_state.result)

    # Sidebar with information
    with st.sidebar:
        st.markdown("### About")
        st.info("""
        This tool analyzes street data and provides AI-powered recommendations 
        for collaborative street works planning.
        """)

        st.markdown("### How to Use")
        st.markdown("""
        1. Enter a valid USRN
        2. Click 'Generate Recommendations'
        3. Review the structured analysis and recommendations
        """)


if __name__ == "__main__":
    main()
