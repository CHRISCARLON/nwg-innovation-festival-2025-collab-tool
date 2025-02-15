import os
import duckdb
from shapely.wkt import loads
from loguru import logger
import asyncio

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
        logger.success(f"Buffered geometry: {buffered}")
        return tuple(round(coord) for coord in buffered.bounds)

    except duckdb.Error as e:
        logger.error(f"Error getting bbox from USRN: {e}")
        raise
