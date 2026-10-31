import duckdb

from pipeline.base_table import BaseTable


class DimContactOfficeTable(BaseTable):
    """Dimension table describing Labour Office contact offices."""

    name = "dim_contact_office"
    grain_columns = ("snapshot_date", "contact_office_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    contact_office_id,
    contact_office_code,
    contact_office_name
FROM stage_contact_offices;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
