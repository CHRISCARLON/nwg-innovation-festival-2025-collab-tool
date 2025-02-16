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
        con = await asyncio.to_thread(duckdb.connect, connection_string)
        logger.success("MotherDuck connection successful")
        return con
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
    con = await connect_to_motherduck()
    schema = os.getenv('USRN_SCHEMA')
    table_name = os.getenv('USRN_TABLE')

    try:
        query = f"""
        SELECT geometry
        FROM {schema}.{table_name}
        WHERE usrn = ?
        """

        result = await asyncio.to_thread(con.execute, query, [usrn])
        df = result.fetchdf()
        
        logger.success(f"USRN Geom Retrieval Successful: {df}")

        if df.empty:
            logger.warning(f"No geometry found for USRN: {usrn}")
            raise ValueError(f"No geometry found for USRN: {usrn}")

        # Load in data and create buffer around the geometry of the USRN
        geom = loads(df['geometry'].iloc[0])
        buffered = geom.buffer(buffer_distance, cap_style="square", single_sided=False)
        logger.success(f"Buffered geometry: {buffered}")
        return tuple(round(coord) for coord in buffered.bounds)

    finally:
        await asyncio.to_thread(con.close)
        logger.success("MotherDuck connection closed")