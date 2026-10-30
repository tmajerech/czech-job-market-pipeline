import duckdb

from pipeline.base_table import BaseTable
from pipeline.silver.sql_expressions import extract_cs_text_sql


class OccupationsTable(BaseTable):
    name = "occupations"
    grain_columns = ("snapshot_date", "occupation_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS occupation_id,
    CAST(kod AS VARCHAR) AS occupation_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS occupation_name,
    CAST(LENGTH(kod) AS INTEGER) AS occupation_level,
    CAST(
        CASE
            WHEN LENGTH(kod) > 1
                THEN 'CzIsco/' || LEFT(kod, LENGTH(kod) - 1)
        END AS VARCHAR
    ) AS parent_occupation_id
FROM staged_occupations;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
