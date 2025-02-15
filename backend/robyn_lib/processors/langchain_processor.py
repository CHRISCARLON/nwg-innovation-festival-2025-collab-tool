import json
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from loguru import logger
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any, List
from ..routes.route_handler import RouteType

class StreetAnalysis(BaseModel):
    """Structured output for street analysis"""
    location: List[str] = Field(description="Name of street and the location of the street")
    key_characteristics: List[str] = Field(description="Key characteristics of the road network")
    special_designations: List[str] = Field(description="Special designations or restrictions")
    work_considerations: List[str] = Field(description="Important considerations for street works")
    potential_challenges: List[str] = Field(description="Potential challenges or hazards")
    summary: str = Field(description="Overall summary of the analysis")

class LandUseAnalysis(BaseModel):
    """Structured output for land use analysis"""
    location: List[str] = Field(
        description="Name and location details of the area, including any major landmarks"
    )
    institutional_properties: List[str] = Field(
        description="Educational, religious, and public institutions including universities, schools, churches, cathedrals"
    )
    residential_properties: List[str] = Field(
        description="All types of residential buildings including private homes, student accommodation, communal living"
    )
    commercial_properties: List[str] = Field(
        description="Commercial and business properties in the area"
    )
    recent_changes: List[str] = Field(
        description="Recent modifications, updates, and changes to properties in the area"
    )
    summary: str = Field(
        description="Comprehensive overview synthesizing all key findings about the area"
    )

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

    chat = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        api_key=secret_api_key 
    )

    # Select appropriate parser and template based on the route type
    if route_type == RouteType.STREET_INFO.value:
        logger.info("Processing street info with Langchain")
        parser = PydanticOutputParser(pydantic_object=StreetAnalysis)
        template = """You are a street works and highways expert.
        Analyze the following street network and special designation data:
        {context}
        Provide a structured analysis following this format:
        {format_instructions}
        Be sure to always start with the location of the street and then identify and include the responsible highway authority.
        Always focus on practical implications for street works planning and impacts to the public, environment, and road users.
        """
    else: 
        logger.info("Processing land use with Langchain")
        parser = PydanticOutputParser(pydantic_object=LandUseAnalysis)
        template = """You are an expert urban planning analyst.
        Analyze the following land use data:
        {context}
        Provide a structured analysis following this format:
        {format_instructions}
        Follow these specific guidelines:
        1. Begin with precise location identification and major landmarks
        2. List names of institutional properties including:
        - Universities and colleges
        - Religious buildings
        - Public institutions
        3. Detail names of residential properties including:
        - Private residences
        - Student accommodation
        - Communal living spaces
        4. Document names of commercial properties as well. 
        5. Note recent changes and modifications to properties
        6. Provide a comprehensive summary
        Format your response according to the schema exactly as specified."""

    # Create prompt template
    prompt = ChatPromptTemplate.from_template(template)

    try:
        # Format the prompt with data and parser instructions
        messages = prompt.format_messages(
            context=json.dumps(data, indent=2),
            format_instructions=parser.get_format_instructions()
        )

        # Get response and ensure we get string content
        response = await chat.ainvoke(messages)
        response_content = response.content if isinstance(response.content, str) else str(response.content)
        
        # Parse the response content to be returned
        parsed_response = parser.parse(response_content)
        logger.success("Langchain Parse Successul")

        return {
            "llm_summary": parsed_response.model_dump(),
        }
    except Exception as e:
        return {
            "error": f"Langchain processing failed: {str(e)}",
            "raw_data": data
        }