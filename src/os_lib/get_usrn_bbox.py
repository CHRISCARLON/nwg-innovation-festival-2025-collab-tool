import os
import duckdb
from shapely.wkt import loads
from loguru import logger

def connect_to_motherduck() -> duckdb.DuckDBPyConnection:
    """
    Create a database connection object to MotherDuck
    """
    # Define secrets
    database = os.getenv('MD_DB')
    token =os.getenv('MD_TOKEN')

    # Check if token exists
    if token is None:
        raise ValueError("Env variable not present")

    # Connection string
    connection_string = f'md:{database}?motherduck_token={token}'

    # Attempt connection
    try:
        con = duckdb.connect(connection_string)
        return con
    except Exception as e:
        logger.warning(f"An error occured: {e}")
        raise

def fetch(usrn: str, buffer_distance: float = 50) -> tuple | None :
    """
    Fetch road geometry and return bounding box coordinates suitable for API query

    Args:
        usrn (str): Unique Street Reference Number
        buffer_distance (float): Distance in meters to buffer around the road

    Returns:
        tuple: (minx, miny, maxx, maxy) coordinates for the bounding box
    """
    try:
        con = connect_to_motherduck()
        schema = os.getenv('SCHEMA')
        table_name = os.getenv('TABLE')

        query = f"""
        SELECT geometry
        FROM {schema}.{table_name}
        WHERE usrn = ?
        """
        result = con.execute(query, [usrn])
        df = result.fetchdf()

        if df.empty:
            logger.warning(f"No data found for USRN: {usrn}")
            return None

        # Parse the WKT string to geometry and create buffer
        geom = loads(df['geometry'].iloc[0])
        buffered = geom.buffer(buffer_distance)

        # Get bounding box coordinates and round to nearest meter
        minx, miny, maxx, maxy = [round(coord) for coord in buffered.bounds]

        return (minx, miny, maxx, maxy)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise

def create_api_url(bbox_coords: tuple, base_url: str = "http://localhost:8080/features") -> str:
    """
    Create API URL with bounding box coordinates

    Args:
        bbox_coords: (minx, miny, maxx, maxy) tuple
        base_url: Base URL for the API

    Returns:
        str: Complete URL with bbox parameters
    """
    minx, miny, maxx, maxy = bbox_coords
    return (f"{base_url}?"
            f"collection_id=lus-fts-site-1&"
            f"bbox={minx},{miny},{maxx},{maxy}&"
            f"bbox-crs=http://www.opengis.net/def/crs/EPSG/0/27700&"
            f"crs=http://www.opengis.net/def/crs/EPSG/0/27700")

if __name__ == "__main__":
    try:
        # Example USRN - replace with actual USRN
        test_usrn = "11720125"

        # Get bounding box coordinates
        bbox_coords = fetch(test_usrn, buffer_distance=50)
        print(bbox_coords)

        if bbox_coords:
            # Generate API URL
            api_url = create_api_url(bbox_coords)
            print(f"Generated API URL: {api_url}")
        else:
            print(f"No data found for USRN: {test_usrn}")

    except Exception as e:
        logger.error(f"Application error: {e}")
        raise
