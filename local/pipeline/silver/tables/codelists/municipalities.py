import duckdb

from pipeline.base_table import BaseTable
from pipeline.silver.sql_expressions import extract_cs_text_sql


class MunicipalitiesTable(BaseTable):
    name = "municipalities"
    grain_columns = ("snapshot_date", "municipality_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS municipality_id,
    CAST(kod AS VARCHAR) AS municipality_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS municipality_name,
    CAST(okres AS VARCHAR) AS district_id
FROM staged_municipalities;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        unresolved_districts = connection.execute("""
            SELECT
                municipality.municipality_id,
                municipality.district_id
            FROM municipalities AS municipality
            LEFT JOIN districts AS district
                ON municipality.snapshot_date = district.snapshot_date
                AND municipality.district_id = district.district_id
            WHERE municipality.district_id IS NULL
                OR district.district_id IS NULL
            LIMIT 10
        """).fetchall()

        if unresolved_districts:
            raise ValueError(f"Municipalities reference unknown districts: {unresolved_districts}")
