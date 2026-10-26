import duckdb

from silver.tables.base import BaseTable


class VacancyRequiredSkillsTable(BaseTable):
    name = "vacancy_required_skills"
    grain_columns = ("snapshot_date", "portal_id", "skill_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(vacancy.snapshot_date AS DATE) AS snapshot_date,
    CAST(vacancy.portalId AS BIGINT) AS portal_id,

    CAST(skill.dovednost.id AS VARCHAR) AS skill_id,
    CAST(skill.popis AS VARCHAR) AS skill_description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.pozadovanaDovednost
) AS skills(skill);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
