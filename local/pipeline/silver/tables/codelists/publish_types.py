import duckdb

from pipeline.base_table import BaseTable
from pipeline.silver.sql_expressions import extract_cs_text_sql


class PublishTypesTable(BaseTable):
    name = "publish_types"
    grain_columns = ("snapshot_date", "publish_type_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(id AS VARCHAR) AS publish_type_id,
    CAST(kod AS VARCHAR) AS publish_type_code,
    CAST({extract_cs_text_sql("nazev")} AS VARCHAR) AS publish_type_name
FROM staged_publish_types;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
