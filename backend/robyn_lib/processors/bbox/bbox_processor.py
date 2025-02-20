import os
import duckdb
from shapely.wkt import loads
from loguru import logger
import asyncio

async def connect_to_motherduck() -> duckdb.DuckDBPyConnection:
    """Create a database connection object to MotherDuck"""
    try:
        database = os.getenv('MD_DB')
        token = os.getenv('MD_TOKEN')
        
        # More detailed environment variable checking if needed
        # logger.debug(f"Database name present: {bool(database)}")
        # logger.debug(f"Token present: {bool(token)}")
        
        if token is None or database is None:
            logger.error("MotherDuck environment variables are missing")
            raise ValueError("MotherDuck environment variables are not present")
        
        connection_string = f'md:{database}?motherduck_token={token}&access_mode=read_only'
        logger.debug("Attempting MotherDuck connection...")
        
        con = await asyncio.to_thread(duckdb.connect, connection_string)
        logger.success("MotherDuck connection successful")
        return con
        
    except duckdb.Error as e:
        logger.error(f"MotherDuck connection error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MotherDuck connection: {str(e)}")
        raise

async def get_bbox_from_usrn(usrn: str, buffer_distance: float = 50) -> tuple:
    """Get bounding box coordinates for a given USRN"""
    con = None
    try:
        con = await connect_to_motherduck()
        schema = os.getenv('USRN_SCHEMA')
        table_name = os.getenv('USRN_TABLE')
        
        logger.debug(f"Schema: {schema}, Table: {table_name}")
        
        if not all([schema, table_name]):
            raise ValueError("Missing schema or table name environment variables")
        
        query = f"""
            SELECT geometry
            FROM {schema}.{table_name}
            WHERE usrn = ?
        """
        
        logger.debug(f"Executing query for USRN: {usrn}")
        result = await asyncio.to_thread(con.execute, query, [usrn])
        df = result.fetchdf()
        
        logger.debug(f"Query result shape: {df.shape}")
        logger.success(f"USRN Geom Retrieval Successful: {df}")
        
        if df.empty:
            logger.warning(f"No geometry found for USRN: {usrn}")
            raise ValueError(f"No geometry found for USRN: {usrn}")
        
        geom = loads(df['geometry'].iloc[0])
        buffered = geom.buffer(buffer_distance, cap_style="square", single_sided=False)
        logger.success(f"Buffered geometry: {buffered}")
        
        return tuple(round(coord) for coord in buffered.bounds)
        
    except Exception as e:
        logger.error(f"Error in get_bbox_from_usrn: {str(e)}")
        raise
        
    finally:
        if con:
            try:
                await asyncio.to_thread(con.close)
                logger.success("MotherDuck connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")