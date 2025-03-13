from typing import AsyncGenerator
import duckdb
from dataclasses import dataclass
import asyncio
from loguru import logger
import os
from contextlib import asynccontextmanager

@asynccontextmanager
async def connect_to_motherduck() -> AsyncGenerator[duckdb.DuckDBPyConnection, None]:
    """Create a database connection object to MotherDuck that can be used with async context managers"""
    database = os.getenv('MD_DB')
    token = os.getenv('MD_TOKEN')
    
    if token is None or database is None:
        raise ValueError("MotherDuck environment variables are not present")
        
    connection_string = f'md:{database}?motherduck_token={token}&access_mode=read_only'
    
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
    # last_month_impact_level: str
    last_month_work_summary: str
    last_12_months_work_summary: str
    # last_24_months_work_summary: str

def create_street_manager_queries() -> StreetManagerQueries:
    """
    Creates query for street manager data
    
    Each query is for a different aggregation of the street manager data
    """
    # TODO rename these variables to be more descriptive
    schema = os.getenv('STREETMANAGER_SCHEMA')
    schema2 = os.getenv('WORK_SUMMARY_SCHEMA')
    completed_works_table = os.getenv('STREETMANAGER_TABLE_COMPLETED')
    in_progress_works_table = os.getenv('STREETMANAGER_TABLE_IN_PROGRESS')
    
    return StreetManagerQueries(
            last_month_work_summary=f"""
            SELECT
                highway_authority,
                promoter_organisation,
                work_category,
                activity_type,
                collaborative_working,
                COUNT(*) as work_count
            FROM {schema}.{completed_works_table}
            WHERE usrn = ?
            GROUP BY 
                highway_authority,
                promoter_organisation, 
                work_category,
                activity_type,
                collaborative_working

            UNION ALL

            SELECT
                highway_authority,
                promoter_organisation,
                work_category,
                activity_type,
                collaborative_working,
                COUNT(*) as work_count
            FROM {schema}.{in_progress_works_table}
            WHERE usrn = ?
            GROUP BY 
                highway_authority,
                promoter_organisation, 
                work_category,
                activity_type,
                collaborative_working
        """,
        last_12_months_work_summary=f"""
            WITH base_data AS (
                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."01_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ? 
                
                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."02_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."03_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."04_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."05_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."06_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."07_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."08_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."09_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."10_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."11_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?

                UNION ALL

                SELECT 
                    permit_reference_number,
                    promoter_organisation,
                    promoter_swa_code,
                    highway_authority,
                    work_category,
                    collaborative_working,
                    work_status_ref,
                    event_type,
                    usrn
                FROM {schema2}."12_2024"
                WHERE work_status_ref = 'completed' AND event_type = 'WORK_STOP'
                AND usrn = ?
            ),
            distinct_permits AS (
                SELECT DISTINCT 
                    permit_reference_number, 
                    promoter_organisation, 
                    promoter_swa_code, 
                    highway_authority,
                    work_category,
                    collaborative_working
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
            ),
            work_analysis AS (
                SELECT 
                    dp.highway_authority,
                    dp.promoter_organisation,
                    sc.sector,
                    dp.work_category,
                    COUNT(DISTINCT dp.permit_reference_number) as total_works,
                    SUM(CASE WHEN dp.collaborative_working = 'Yes' THEN 1 ELSE 0 END) as collaborative_works
                FROM distinct_permits dp
                LEFT JOIN sector_classification sc 
                    ON dp.promoter_organisation = sc.promoter_organisation
                    AND dp.promoter_swa_code = sc.promoter_swa_code
                GROUP BY 
                    dp.highway_authority,
                    dp.promoter_organisation,
                    sc.sector,
                    dp.work_category
            )
            SELECT 
                highway_authority,
                promoter_organisation,
                sector,
                work_category,
                total_works,
                collaborative_works
            FROM work_analysis
            ORDER BY 
                highway_authority,
                promoter_organisation,
                sector,
                work_category
        """
    )