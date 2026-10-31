import duckdb

from pipeline.base_table import BaseTable


class DimMunicipalityTable(BaseTable):
    """Dimension table describing municipalities and their location hierarchy."""

    name = "dim_municipality"
    grain_columns = ("snapshot_date", "municipality_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    municipality.snapshot_date,
    municipality.municipality_id,
    municipality.municipality_code,
    municipality.municipality_name,

    district.district_id,
    district.district_code,
    district.district_name,
    district.lau_code AS district_lau_code,

    region.region_id,
    region.region_code,
    region.region_name,
    region.nuts3_code AS region_nuts3_code
FROM stage_municipalities AS municipality
INNER JOIN stage_districts AS district
    ON district.snapshot_date = municipality.snapshot_date
    AND district.district_id = municipality.district_id
INNER JOIN dim_region AS region
    ON region.snapshot_date = district.snapshot_date
    AND region.region_id = district.region_id;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        result = connection.execute(f"""
            SELECT
                (SELECT COUNT(*) FROM {cls.name}),
                (SELECT COUNT(*) FROM stage_municipalities)
        """).fetchone()
        if result is None:
            raise RuntimeError(
                f"Could not read row counts from {cls.name} and stage_municipalities"
            )
        actual_row_count, expected_row_count = result

        if actual_row_count != expected_row_count:
            raise RuntimeError(
                f"{cls.name} row count mismatch: "
                f"expected {expected_row_count}, got {actual_row_count}"
            )
