import requests
import os

def fetch_data(endpoint: str) -> dict:
    """" TBC """
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        result = response.json()
        return result
    except Exception:
        raise

def fetch_data_auth(endpoint: str) -> dict:
    """" Fetches data from endpoint using OS API key from environment variables """
    try:
        headers = {
            'key': os.environ['OS_KEY'],
            'Content-Type': 'application/json'
        }
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        result = response.json()
        return result
    except Exception:
        raise
