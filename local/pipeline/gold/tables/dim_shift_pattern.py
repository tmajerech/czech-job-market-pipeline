import duckdb

from pipeline.base_table import BaseTable


class DimShiftPatternTable(BaseTable):
    """Dimension table describing vacancy shift patterns."""

    name = "dim_shift_pattern"
    grain_columns = ("snapshot_date", "shift_pattern_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    shift_pattern_id,
    shift_pattern_code,
    shift_pattern_name
FROM stage_shift_patterns;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
