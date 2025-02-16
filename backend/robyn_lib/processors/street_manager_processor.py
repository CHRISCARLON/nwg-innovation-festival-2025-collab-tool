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

async def get_street_manager_stats(usrn: str) -> dict:
    """Get street manager stats for a given USRN from multiple tables
    Args:
        usrn: Street reference number
    Returns:
        list: List of Arrow tables containing query results
    """
    con = await connect_to_motherduck()
    schema = os.getenv('STREETMANAGER_SCHEMA')
    table1 = os.getenv('STREETMANAGER_TABLE')
    table2 = os.getenv('STREETMANAGER_TABLE_2')
    table3 = os.getenv('STREETMANAGER_TABLE_3')

    try:
        # Execute separate SELECTs
        street_manager_stats = []
        query1 = f"SELECT weighted_impact_level FROM {schema}.{table1} WHERE usrn = ?"
        query2 = f"""
            SELECT 
                promoter_organisation,
                work_category,
                COUNT(*) as work_count
            FROM {schema}.{table2} 
            WHERE usrn = ?
            GROUP BY promoter_organisation, work_category
            UNION ALL
            SELECT 
                promoter_organisation,
                work_category,
                COUNT(*) as work_count
            FROM {schema}.{table3} 
            WHERE usrn = ?
            GROUP BY promoter_organisation, work_category
        """
        
        street_manager_stats.append((await asyncio.to_thread(con.execute, query1, [usrn])).fetch_arrow_table())
        street_manager_stats.append((await asyncio.to_thread(con.execute, query2, [usrn, usrn])).fetch_arrow_table())

        if all(table.num_rows == 0 for table in street_manager_stats):
            logger.warning(f"No data found for USRN: {usrn}")
            return {
                'impact_levels': ["EMPTY"],
                'work_summary': ["EMPTY"]
            }
        
        logger.success(f"Street manager stats retrieved: {street_manager_stats}")

        formatted_stats = {
            'impact_levels': street_manager_stats[0].to_pylist(),
            'work_summary': street_manager_stats[1].to_pylist()
        }

        return formatted_stats

    finally:
        await asyncio.to_thread(con.close)
        logger.success("MotherDuck connection closed")