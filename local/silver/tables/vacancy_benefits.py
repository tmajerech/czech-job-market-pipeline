import duckdb

from silver.tables.base import BaseTable


class VacancyBenefitsTable(BaseTable):
    name = "vacancy_benefits"
    grain_columns = ("snapshot_date", "portal_id", "benefit_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(vacancy.snapshot_date AS DATE) AS snapshot_date,
    CAST(vacancy.portalId AS BIGINT) AS portal_id,

    CAST(benefit.vyhoda.id AS VARCHAR) AS benefit_id,
    CAST(benefit.popis AS VARCHAR) AS benefit_description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.vyhodyVolnehoMista
) AS unnested_benefits(benefit);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
