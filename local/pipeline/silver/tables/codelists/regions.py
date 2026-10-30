import duckdb

from pipeline.base_table import BaseTable
from pipeline.silver.sql_expressions import extract_cs_text_sql


class RegionsTable(BaseTable):
    name = "regions"
    grain_columns = ("snapshot_date", "region_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS region_id,
    CAST(kod AS VARCHAR) AS region_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS region_name,
    CAST(kodNuts3 AS VARCHAR) AS nuts3_code
FROM staged_regions;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
