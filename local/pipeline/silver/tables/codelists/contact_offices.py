import duckdb

from pipeline.base_table import BaseTable
from pipeline.silver.sql_expressions import extract_cs_text_sql


class ContactOfficesTable(BaseTable):
    name = "contact_offices"
    grain_columns = ("snapshot_date", "contact_office_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS contact_office_id,
    CAST(kod AS VARCHAR) AS contact_office_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS contact_office_name
FROM staged_contact_offices;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
