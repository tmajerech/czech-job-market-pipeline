import duckdb

from silver.tables.base import BaseTable


class VacancyRequiredLanguageTable(BaseTable):
    name = "vacancy_required_language"
    grain_columns = ("snapshot_date", "portal_id", "language_id", "skill_level_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(vacancy.snapshot_date AS DATE) AS snapshot_date,
    CAST(vacancy.portalId AS BIGINT) AS portal_id,

    CAST(language.urovenZnalosti.id AS VARCHAR) AS skill_level_id,
    CAST(language.jazyk.id AS VARCHAR) AS language_id,
    CAST(language.popis AS VARCHAR) AS description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.pozadovanaJazykovaZnalost
) AS languages(language);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
