from typing import Dict, Any, Callable, Coroutine
from loguru import logger
import asyncio
from .config import create_street_manager_queries
from ...db.database_pool import MotherDuckPool


def stringify_list(data_list):
    """Stringify a list of data"""
    if isinstance(data_list, list):
        return [
            {k: str(v) if v is not None else "" for k, v in item.items()}
            if isinstance(item, dict)
            else str(item)
            for item in data_list
        ]
    return ["NO DATA"]


def street_manager_processor() -> Callable[[str], Coroutine[Any, Any, Dict[str, Any]]]:
    """Creates a street manager processor that executes all available queries"""
    queries = create_street_manager_queries()
    pool = MotherDuckPool()

    async def process_street_manager_stats(usrn: str) -> Dict[str, Any]:
        try:
            async with pool.get_connection() as con:
                # Execute work summary query
                work_summary = await asyncio.to_thread(
                    con.execute,
                    queries.work_summary,
                    [usrn, usrn, usrn, usrn, usrn, usrn],
                )
                work_summary_table = work_summary.fetch_arrow_table()

                # Check if all tables are empty
                if all(
                    table.num_rows == 0
                    for table in [
                        # impact_levels_table,
                        work_summary_table
                    ]
                ):
                    logger.warning(f"No data found for USRN: {usrn}")
                    return {
                        "work_summary": ["NO DATA"],
                    }

                logger.success(f"Data is not empty for USRN: {usrn}")
                logger.info(f"Work summary table: {work_summary_table}")

                return {
                    "2025_work_summary": stringify_list(
                        work_summary_table.to_pylist()
                        if work_summary_table.num_rows > 0
                        else ["NO DATA"]
                    )
                }
        except Exception as e:
            logger.error(f"Error processing street manager stats: {e}")
            raise

    return process_street_manager_stats
