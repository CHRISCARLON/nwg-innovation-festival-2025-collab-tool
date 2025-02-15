import os
import duckdb
from shapely.wkt import loads
from loguru import logger
import asyncio

from os_lib.os_ngd_features import OSNGDCollections

async def connect_to_motherduck() -> duckdb.DuckDBPyConnection:
    """Create a database connection object to MotherDuck"""
    database = os.getenv('MD_DB')
    token = os.getenv('MD_TOKEN')

    if token is None or database is None:
        raise ValueError("MotherDuck environment variables are not present")

    connection_string = f'md:{database}?motherduck_token={token}&access_mode=read_only'
    try:
        # Create a thread-safe cursor for the connection
        con = await asyncio.to_thread(duckdb.connect, connection_string)
        cursor = con.cursor()
        logger.success("MotherDuck connection successful")
        return cursor
    except duckdb.Error as e:
        logger.warning(f"MotherDuck connection error: {e}")
        raise

async def get_bbox_from_usrn(usrn: str, buffer_distance: float = 50) -> tuple:
    """Get bounding box coordinates for a given USRN
    Args:
        usrn: Street reference number
        buffer_distance: Buffer distance in meters - the default is 50m

    Returns:
        tuple: (minx, miny, maxx, maxy) coordinates
    """
    try:
        con = await connect_to_motherduck()
        schema = os.getenv('SCHEMA')
        table_name = os.getenv('TABLE')

        query = f"""
        SELECT geometry
        FROM {schema}.{table_name}
        WHERE usrn = ?
        """

        result = await asyncio.to_thread(con.execute, query, [usrn])
        df = result.fetchdf()
        con.close()
        
        logger.success(f"USRN Geom Retrieval Successful: {df}")

        if df.empty:
            logger.warning(f"No geometry found for USRN: {usrn}")
            raise ValueError(f"No geometry found for USRN: {usrn}")

        # Load in data and create buffer around the geometry of the USRN
        geom = loads(df['geometry'].iloc[0])
        buffered = geom.buffer(buffer_distance, cap_style="square", single_sided=False)
        return tuple(round(coord) for coord in buffered.bounds)

    except duckdb.Error as e:
        logger.error(f"Error getting bbox from USRN: {e}")
        raise

def filter_feature_properties(feature: dict, collection_id: str) -> dict:
    """Extract key information from a feature based on collection type"""

    # Base properties that exist in both schemas
    essential_props = {
        'id': feature['id'],
        'properties': {
            'description': feature['properties'].get('description'),
        }
    }

    # For RAMI Special Designation collections
    if collection_id in OSNGDCollections.RAMI.value:
        essential_props['properties'].update({
            'usrn': feature['properties'].get('usrn'),
            'designation': feature['properties'].get('designation'),
            'designationdescription': feature['properties'].get('designationdescription'),
            'effectivestartdate': feature['properties'].get('effectivestartdate'),
            'effectiveenddate': feature['properties'].get('effectiveenddate'),
            'timeinterval': feature['properties'].get('timeinterval'),
            'geometry_length': feature['properties'].get('geometry_length'),
            'authorityid': feature['properties'].get('authorityid'),
            'contactauthority_authorityname': feature['properties'].get('contactauthority_authorityname')
        })

    # For LUS collections
    elif collection_id in OSNGDCollections.LUS.value:
        essential_props['properties'].update({
            'name1_text': feature['properties'].get('name1_text'),
            'name2_text': feature['properties'].get('name2_text'),
            'oslandusetiera': feature['properties'].get('oslandusetiera'),
            'oslandusetierb': feature['properties'].get('oslandusetierb', []),
            'primaryuprn': feature['properties'].get('primaryuprn'),
            'geometry_area': feature['properties'].get('geometry_area')
        })

    return essential_props
