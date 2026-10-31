import duckdb

from pipeline.base_table import BaseTable


class DimOccupationTable(BaseTable):
    """Dimension table describing CZ-ISCO occupations."""

    name = "dim_occupation"
    grain_columns = ("snapshot_date", "occupation_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    occupation_id,
    occupation_code,
    occupation_name,
    occupation_level,
    parent_occupation_id
FROM stage_occupations;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
