from taipy.gui import Gui
import taipy.gui.builder as tgb
import requests
import json

#TODO: Split this out into modules!
# Initial state variables
collection_id = ""
usrn = ""
response_data = "No data fetched yet"
formatted_data = "No data fetched yet"
api_base_url = "http://localhost:8080"

def initialize_state(state):
    state.usrn = usrn
    state.response_data = response_data
    state.formatted_data = formatted_data

def clear_response(state):
    """Helper function to clear response data"""
    state.response_data = "Loading..."
    state.formatted_data = "Loading..."

def fetch_street_llm(state):
    try:
        # Clear existing response first
        clear_response(state)
        
        params = {
            "usrn": state.usrn
        }

        print(f"Fetching Street Info with params: {params}")
        response = requests.get(f"{api_base_url}/street-info-llm", params=params)
        response.raise_for_status()
        
        state.response_data = json.dumps(response.json(), indent=2)
        state.formatted_data = state.response_data 
        print(f"Response received: {state.response_data}")
    except Exception as e:
        state.response_data = f"Error: {str(e)}"
        state.formatted_data = state.response_data
        print(f"Error occurred: {str(e)}")

def fetch_land_use_llm(state):
    try:
        # Clear existing response first
        clear_response(state)
        
        
        params = {
            "usrn": state.usrn
        }

        print(f"Fetching Land Use Info with params: {params}")
        response = requests.get(f"{api_base_url}/land-use-info-llm", params=params)
        response.raise_for_status()

        state.response_data = json.dumps(response.json(), indent=2)
        print(f"Response received: {state.formatted_data}")
    except Exception as e:
        state.response_data = f"Error: {str(e)}"
        state.formatted_data = state.response_data
        print(f"Error occurred: {str(e)}")

# Build the page
with tgb.Page() as page:
    # Main container with padding and background
    with tgb.layout("grid", class_name="h-screen bg-gray-50 p-4"):
        # Header section
        with tgb.part(class_name="col-span-2 mb-6"):
            tgb.text("# ⚠️ Rapid Street Assessment Tool", mode="md", class_name="text-3xl font-bold text-gray-800")
        
        # Two-column layout with gap
        with tgb.layout("1 1", gap="4"):
            # Left column - Controls
            with tgb.part(class_name="bg-white rounded-lg shadow-md p-6"):
                # Input section
                tgb.text("### Input Parameters", mode="md", class_name="text-xl font-semibold text-gray-700 mb-4")
                
                # USRN input
                tgb.text("USRN", class_name="text-sm font-medium text-gray-600 mb-2")
                tgb.input("{usrn}", class_name="w-full p-2 border rounded-md mb-6")
                
                # Actions section
                tgb.text("### Actions", mode="md", class_name="text-xl font-semibold text-gray-700 mb-4")
                
                # Buttons
                with tgb.part(class_name="space-y-3"):
                    tgb.button("📊 Fetch Street Data", 
                            on_action=fetch_street_llm, 
                            class_name="w-full p-2 bg-blue-600 text-white rounded-md hover:bg-blue-700")
                    tgb.button("🏢 Fetch Land Use Data", 
                            on_action=fetch_land_use_llm, 
                            class_name="w-full p-2 bg-green-600 text-white rounded-md hover:bg-green-700")

            # Right column - Response
            with tgb.part(class_name="bg-white rounded-lg shadow-md"):
                # Response header
                with tgb.part(class_name="border-b p-4"):
                    tgb.text("### Response", mode="md", class_name="text-xl font-semibold text-gray-700")
                
                # Response content
                with tgb.part(class_name="p-4"):
                    tgb.text("{formatted_data}", 
                            mode="md", 
                            class_name="font-mono text-sm whitespace-pre-wrap bg-gray-50 p-4 rounded-md overflow-auto max-h-[70vh]")

if __name__ == "__main__":
    Gui(page=page).run(
        title="Rapid Street Assessments Tool",
    )