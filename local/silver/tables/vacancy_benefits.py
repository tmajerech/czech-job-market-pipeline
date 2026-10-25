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
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    benefit.vyhoda.id AS benefit_id,
    benefit.popis AS benefit_description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.vyhodyVolnehoMista
) AS unnested_benefits(benefit);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
