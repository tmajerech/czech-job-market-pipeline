import duckdb

from pipeline.base_table import BaseTable


class DimPublishTypeTable(BaseTable):
    """Dimension table describing vacancy publication modes."""

    name = "dim_publish_type"
    grain_columns = ("snapshot_date", "publish_type_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    publish_type_id,
    publish_type_code,
    publish_type_name
FROM stage_publish_types;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
