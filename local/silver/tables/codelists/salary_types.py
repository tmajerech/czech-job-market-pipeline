import duckdb

from silver.tables.base import BaseTable
from sql_expressions import extract_cs_text_sql


class SalaryTypesTable(BaseTable):
    name = "salary_types"
    grain_columns = ("snapshot_date", "salary_type_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS salary_type_id,
    CAST(kod AS VARCHAR) AS salary_type_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS salary_type_name
FROM staged_salary_types;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
