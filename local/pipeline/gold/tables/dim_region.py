import duckdb

from pipeline.base_table import BaseTable


class DimRegionTable(BaseTable):
    """Dimension table describing Czech regions."""

    name = "dim_region"
    grain_columns = ("snapshot_date", "region_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    region_id,
    region_code,
    region_name,
    nuts3_code
FROM stage_regions;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
