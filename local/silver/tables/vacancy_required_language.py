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
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    language.urovenZnalosti.id AS skill_level_id,
    language.jazyk.id AS language_id,
    language.popis AS description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.pozadovanaJazykovaZnalost
) AS languages(language);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
