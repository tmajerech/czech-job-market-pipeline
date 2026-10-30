import duckdb

from pipeline.base_table import BaseTable
from pipeline.silver.sql_expressions import extract_cs_text_sql


class DistrictsTable(BaseTable):
    name = "districts"
    grain_columns = ("snapshot_date", "district_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS district_id,
    CAST(kod AS VARCHAR) AS district_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS district_name,
    CAST(kodLau AS VARCHAR) AS lau_code,
    CAST(kraj AS VARCHAR) AS region_id
FROM staged_districts;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        unresolved_regions = connection.execute("""
            SELECT
                district.district_id,
                district.region_id
            FROM districts AS district
            LEFT JOIN regions AS region
                ON district.snapshot_date = region.snapshot_date
                AND district.region_id = region.region_id
            WHERE district.region_id IS NULL
                OR region.region_id IS NULL
            LIMIT 10
        """).fetchall()

        if unresolved_regions:
            raise ValueError(f"Districts reference unknown regions: {unresolved_regions}")
