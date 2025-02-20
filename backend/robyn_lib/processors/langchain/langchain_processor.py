import json
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence 
from loguru import logger
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any, List
from ...routes.route_handler import RouteType

class StreetAnalysis(BaseModel):
    """Structured output for street analysis"""
    location: List[str] = Field(description="Name of street and the location of the street")
    key_characteristics: List[str] = Field(description="Key characteristics of the road network including who manages the road network")
    special_designations: List[str] = Field(description="Special designations or restrictions present for this USRN")
    past_work_history: List[str] = Field(description="Work history of the specific USRN. This will include last month's work info, last 12 monthsworth of work info (please always include this historical data in your response). Please tell us if any collaborative street working has been done here last month and over the last 12 months and make this clear in your response.")
    potential_challenges: List[str] = Field(description="Potential challenges or hazards present for this USRN")
    summary: str = Field(description="Overall summary of the analysis and information your have found.")

class LandUseAnalysis(BaseModel):
    """Structured output for land use analysis"""
    location: List[str] = Field(description="Name and location details of the area, including any major landmarks nearby")
    property_numbers: List[str] = Field(description="A high-level idea of the number of properties in the area")
    institutional_properties: List[str] = Field(description="Names of all educational, religious, and public institutions including universities, schools, churches, cathedrals")
    residential_properties: List[str] = Field(description="Names of all types of residential buildings including private homes, student accommodation, communal living")
    commercial_properties: List[str] = Field(description="Names of all commercial and business properties in the area")
    recent_changes: List[str] = Field(description="Recent modifications, updates, and changes to properties in the area")
    summary: str = Field(description="Overall summary of the analysis and information your have found.")

class CollaborativeStreetWorksAnalysis(BaseModel):
    """Structured output for collaborative street works analysis"""
    location: List[str] = Field(description="Name of street and the location of the street")
    key_characteristics: List[str] = Field(description="Key characteristics of the road network including who manages the road network")
    special_designations: List[str] = Field(description="Special designations or restrictions present for this USRN")
    past_work_history: List[str] = Field(description="Work history of the specific USRN. This will include last month's work info, a year worth of work info, and last month's impact scores (please always include these historical impact scores and data in your response). Please tell us if any collaborative street working has been done here last month and over the last 12 months and make this clear in your response.")
    potential_challenges: List[str] = Field(description="Potential challenges or hazards present for this USRN")
    property_numbers: List[str] = Field(description="A high-level idea of the number of properties in the area")
    institutional_properties: List[str] = Field(description="Names of all educational, religious, and public institutions including universities, schools, churches, cathedrals")
    residential_properties: List[str] = Field(description="Names of all types of residential buildings including private homes, student accommodation, communal living")
    commercial_properties: List[str] = Field(description="Names of all commercial and business properties in the area")
    recent_changes: List[str] = Field(description="Recent modifications, updates, and changes to properties in the area")
    summary: str = Field(description="Overall summary of the analysis and please make a recommendation for collaborative street works - based on all the context you now have would you advise this on a scale of 1 (being no) to 10 (being yes absolutely).")

async def process_with_langchain(data: Dict[str, Any], route_type: str) -> Dict[str, Any]:
    """
    Process data using Langchain with structured output.

    This uses the OpenAI API to process the data.
    
    Args:
        data (Dict[str, Any]): The data to process
        route_type (str): The type of route to process
        
    Returns:
        Dict[str, Any]: The processed data
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None:
        raise ValueError("OPENAI_API_KEY is not set")

    # Convert api_key to SecretStr using pydantic
    secret_api_key = SecretStr(api_key)

    # Set model type
    # TODO add other models?
    model = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        api_key=secret_api_key 
    )

    # Select appropriate parser and template based on the route type
    if route_type == RouteType.STREET_INFO.value:
        logger.info("Processing street info with Langchain")
        prompt_template = """You are a street works expert.
        Analyze the following data:
        {context}
        Always focus on a summary of all the information you have found.
        Make sure to include information about the street manager stats including past works and in the data.
        """
        structured_output = model.with_structured_output(StreetAnalysis)
        logger.info("Street analysis structured output: {structured_output}")
    elif route_type == RouteType.COLLABORATIVE_STREET_WORKS.value:
        logger.info("Processing collaborative street works with Langchain")
        prompt_template = """You are a street works collaboration expert.
        Analyze the following data:
        {context}
        Always focus on practical implications for street works planning and make a judgement on the potential for collaborative street works.
        """
        structured_output = model.with_structured_output(CollaborativeStreetWorksAnalysis)
        logger.info("Collaborative street works analysis structured output: {structured_output}")
    else: 
        # Else RouteType.LAND_USE.value
        logger.info("Processing land use with Langchain")
        prompt_template = """You are an expert urban planning analyst.
        Analyze the following land use data:
        {context}
        Always focus on a summary of all the information you have found.
        """
        structured_output = model.with_structured_output(LandUseAnalysis)
        logger.info("Land use analysis structured output: {structured_output}")
    
    # Create prompt template and chain to run
    prompt = PromptTemplate(template=prompt_template, input_variables=["context"])
    chain = RunnableSequence(prompt | structured_output)

    try:
        # Get response and ensure we get string content
        response = await chain.ainvoke({"context": json.dumps(data, indent=2)})
        
        # Parse the response content to be returned
        logger.success("Langchain Parse Successul")

        return {
            "llm_summary": response.model_dump(),
            "raw_data": data
        }
    except Exception as e:
        return {
            "error": f"Langchain processing failed: {str(e)}",
            "raw_data": data
        }