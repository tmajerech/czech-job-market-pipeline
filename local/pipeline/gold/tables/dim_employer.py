import duckdb

from pipeline.base_table import BaseTable


class DimEmployerTable(BaseTable):
    """Describe employers by IČO using the latest observed name.

    Multiple vacancies can use the same IČO with different employer-name
    spellings, so the latest updated vacancy supplies the descriptive name.
    """

    name = "dim_employer"
    grain_columns = ("snapshot_date", "employer_ico")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    employer_ico,
    employer_name
FROM (
    SELECT
        snapshot_date,
        employer_ico,
        employer_name,
        ROW_NUMBER() OVER (
            PARTITION BY
                snapshot_date,
                employer_ico
            ORDER BY
                updated_at DESC NULLS LAST,
                portal_id DESC
        ) AS row_number
    FROM stage_vacancies
    WHERE employer_ico IS NOT NULL
) AS ranked_employers
WHERE row_number = 1;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
