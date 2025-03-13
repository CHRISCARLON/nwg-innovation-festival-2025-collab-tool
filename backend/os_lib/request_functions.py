import requests
import os
import aiohttp

def fetch_data(endpoint: str) -> dict:
    """" 
    Synchronous function to fetch data from an endpoint
    
    Args:
        endpoint: str - The endpoint to fetch data from
    Returns:
        dict - The data from the endpoint
    Raises:
        Exception - If the request fails
    """
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        raise e

async def fetch_data_auth(endpoint: str) -> dict:
    """" 
    Asynchronous function to fetch data from an endpoint using OS API key from environment variables 
    
    Args:
        endpoint: str - The endpoint to fetch data from
    Returns:
        dict - The data from the endpoint
    Raises:
        Exception - If the request fails
    """
    try:
        headers = {
            'key': os.environ['OS_KEY'],
            'Content-Type': 'application/json'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(endpoint, headers=headers) as response:
                response.raise_for_status()
                print(response.url)
                result = await response.json()
                return result
    except aiohttp.ClientError as e:
        raise e
    except Exception as e:
        raise e