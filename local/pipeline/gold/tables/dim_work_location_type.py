import duckdb

from pipeline.base_table import BaseTable


class DimWorkLocationTypeTable(BaseTable):
    """Dimension table describing how vacancy work locations are specified."""

    name = "dim_work_location_type"
    grain_columns = ("snapshot_date", "work_location_type_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    work_location_type_id,
    work_location_type_code,
    work_location_type_name
FROM stage_work_location_types;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
