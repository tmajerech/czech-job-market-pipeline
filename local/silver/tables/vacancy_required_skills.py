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
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    skill.dovednost.id AS skill_id,
    skill.popis AS skill_description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.pozadovanaDovednost
) AS skills(skill);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
