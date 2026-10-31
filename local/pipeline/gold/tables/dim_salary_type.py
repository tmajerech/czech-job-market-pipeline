import duckdb

from pipeline.base_table import BaseTable


class DimSalaryTypeTable(BaseTable):
    """Dimension table describing vacancy salary types."""

    name = "dim_salary_type"
    grain_columns = ("snapshot_date", "salary_type_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    salary_type_id,
    salary_type_code,
    salary_type_name
FROM stage_salary_types;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
