from typing import AsyncGenerator
import duckdb
from dataclasses import dataclass
import asyncio
from loguru import logger
import os
from contextlib import asynccontextmanager

# TODO: Add a query for the number of works completed in the last 12 months as well


@asynccontextmanager
async def connect_to_motherduck() -> AsyncGenerator[duckdb.DuckDBPyConnection, None]:
    """Create a database connection object to MotherDuck that can be used with async context managers"""
    database = os.getenv("MD_DB")
    token = os.getenv("MD_TOKEN")

    if token is None or database is None:
        raise ValueError("MotherDuck environment variables are not present")

    connection_string = f"md:{database}?motherduck_token={token}&access_mode=read_only"

    con = None
    try:
        con = await asyncio.to_thread(duckdb.connect, connection_string)
        logger.success("MotherDuck connection successful")
        yield con
    except duckdb.Error as e:
        logger.warning(f"MotherDuck connection error: {e}")
        raise
    finally:
        if con is not None:
            await asyncio.to_thread(con.close)
            logger.success("MotherDuck connection closed")


@dataclass
class StreetManagerQueries:
    work_summary: str


def create_street_manager_queries() -> StreetManagerQueries:
    """
    Creates query for street manager data

    Each query is for a different aggregation of the street manager data
    """
    schema = os.getenv("WORK_SUMMARY_SCHEMA")

    return StreetManagerQueries(
        work_summary=f"""
            WITH base_data AS (
                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code
                FROM {schema}."01_2025"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ? 
                
                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code
                FROM {schema}."02_2025"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code
                FROM {schema}."03_2025"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code
                FROM {schema}."04_2025"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code
                FROM {schema}."05_2025"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code
                FROM {schema}."06_2025"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?
            ),
            distinct_permits AS (
                SELECT DISTINCT 
                    permit_reference_number, 
                    promoter_organisation, 
                    promoter_swa_code
                FROM base_data
            ),
            sector_classification AS (
                SELECT 
                    dp.promoter_organisation,
                    dp.promoter_swa_code,
                    CASE 
                        WHEN geoplace.ofwat_licence IS NOT NULL AND geoplace.ofcom_licence IS NOT NULL THEN 'Water'
                        WHEN geoplace.ofwat_licence IS NOT NULL THEN 'Water'
                        WHEN geoplace.ofgem_electricity_licence IS NOT NULL THEN 'Electricity'
                        WHEN geoplace.ofgem_gas_licence IS NOT NULL THEN 'Gas'
                        WHEN geoplace.ofcom_licence IS NOT NULL THEN 'Telecommunications'
                        WHEN geoplace.swa_code IS NOT NULL THEN 'Highway Authority'
                        ELSE 'Other'
                    END as sector
                FROM (SELECT DISTINCT promoter_organisation, promoter_swa_code FROM distinct_permits) dp
                LEFT JOIN geoplace_swa_codes.LATEST_ACTIVE geoplace 
                    ON CAST(dp.promoter_swa_code AS INT) = CAST(geoplace.swa_code AS INT)
            )
            SELECT 
                dp.promoter_organisation,
                sc.sector,
                COUNT(DISTINCT dp.permit_reference_number) as total_works
            FROM distinct_permits dp
            LEFT JOIN sector_classification sc 
                ON dp.promoter_organisation = sc.promoter_organisation
                AND dp.promoter_swa_code = sc.promoter_swa_code
            GROUP BY 
                dp.promoter_organisation,
                sc.sector
            ORDER BY 
                total_works DESC,
                dp.promoter_organisation
        """
    )
