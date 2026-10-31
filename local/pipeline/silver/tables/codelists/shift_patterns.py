import duckdb

from pipeline.base_table import BaseTable
from pipeline.silver.sql_expressions import extract_cs_text_sql


class ShiftPatternsTable(BaseTable):
    name = "shift_patterns"
    grain_columns = ("snapshot_date", "shift_pattern_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS shift_pattern_id,
    CAST(kod AS VARCHAR) AS shift_pattern_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS shift_pattern_name
FROM staged_shift_patterns;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
