from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field, SecretStr
from typing import Dict, Any, List
import json
import os

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
    location: List[str] = Field(description="Name of street and the location of the street")
    land_use_types: List[str] = Field(description="Main types of land and building use in the area")
    work_implications: List[str] = Field(description="Implications for street works")
    property_impacts: List[str] = Field(description="Impacts on different property types")
    access_considerations: List[str] = Field(description="Access and logistics considerations")
    summary: str = Field(description="Overall summary of the analysis")

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

    # Select appropriate parser and template based on route type
    #TODO add match statements instead of if statements
    if route_type == "street_info":
        parser = PydanticOutputParser(pydantic_object=StreetAnalysis)
        template = """You are a street works and highways expert.
        Analyze the following street network and special designation data:
        {context}
        Provide a structured analysis following this format:
        {format_instructions}
        Be sure to identify and include the responsible highway authority.
        Focus on practical implications for street works planning.
        """
    else:  # land_use
        parser = PydanticOutputParser(pydantic_object=LandUseAnalysis)
        template = """You are an urban planning expert.
        Analyze the following land use data:
        {context}
        Provide a structured analysis following this format:
        {format_instructions}
        Be sure to identify and include the responsible highway authority.
        Focus on implications for street works and construction activities.
        """

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

        return {
            "analysis": parsed_response.model_dump(),
        }
    except Exception as e:
        return {
            "error": f"Langchain processing failed: {str(e)}",
            "raw_data": data
        }