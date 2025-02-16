import json
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.runnables.base import RunnableSequence 
from loguru import logger
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any, List
from ..routes.route_handler import RouteType

class StreetAnalysis(BaseModel):
    """Structured output for street analysis"""
    location: List[str] = Field(description="Name of street and the location of the street")
    key_characteristics: List[str] = Field(description="Key characteristics of the road network including who managed the road network")
    special_designations: List[str] = Field(description="Special designations or restrictions")
    work_considerations: List[str] = Field(description="Important considerations for street works inlcuding information about the street manager stats including past works and impact scores in the data")
    potential_challenges: List[str] = Field(description="Potential challenges or hazards")
    summary: str = Field(description="Overall summary of the analysis")

class LandUseAnalysis(BaseModel):
    """Structured output for land use analysis"""
    location: List[str] = Field(description="Name and location details of the area, including any major landmarks nearby")
    numbers: List[str] = Field(description="A high-level idea of the number of properties in the area")
    institutional_properties: List[str] = Field(description="Names of all educational, religious, and public institutions including universities, schools, churches, cathedrals")
    residential_properties: List[str] = Field(description="Names of all types of residential buildings including private homes, student accommodation, communal living")
    commercial_properties: List[str] = Field(description="Names of all commercial and business properties in the area")
    recent_changes: List[str] = Field(description="Recent modifications, updates, and changes to properties in the area")
    summary: str = Field(description="Comprehensive overview synthesizing all key findings about the area")

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

    structured_output = model.with_structured_output(
        StreetAnalysis if route_type == RouteType.STREET_INFO.value else LandUseAnalysis
    )

    # Select appropriate parser and template based on the route type
    if route_type == RouteType.STREET_INFO.value:
        logger.info("Processing street info with Langchain")
        prompt_template = """You are a street works and highways expert.
        Analyze the following street network and special designation data:
        {context}
        Always focus on practical implications for street works planning and impacts to the public, environment, and road users.
        Make sure to include information about the street manager stats including past works and impact scores in the data.
        """
    else: 
        logger.info("Processing land use with Langchain")
        prompt_template = """You are an expert urban planning analyst.
        Analyze the following land use data:
        {context}
        Always focus on practical implications for street works planning and impacts to the public, environment, and road users"""

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
        }
    except Exception as e:
        return {
            "error": f"Langchain processing failed: {str(e)}"
        }