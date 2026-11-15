import duckdb

from pipeline.base_table import BaseTable


class FactVacancyEventTable(BaseTable):
    """Fact table for changes between vacancy snapshots."""

    name = "fact_vacancy_event"
    grain_columns = ("snapshot_date", "portal_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
WITH current_snapshot_date AS (
    SELECT snapshot_date
    FROM fact_vacancy_snapshot
    GROUP BY snapshot_date
),
previous_snapshot_date AS (
    SELECT snapshot_date
    FROM stage_previous_fact_vacancy_snapshot
    GROUP BY snapshot_date
)
SELECT
    current_snapshot_date.snapshot_date,
    portal_id,
    previous_snapshot_date.snapshot_date
        AS previous_snapshot_date,
    CASE
        WHEN current_vacancy.portal_id IS NOT NULL
            AND previous_vacancy.portal_id IS NULL
            THEN 'NEW'
        WHEN current_vacancy.portal_id IS NULL
            AND previous_vacancy.portal_id IS NOT NULL
            THEN 'REMOVED'
    END AS event_type
FROM fact_vacancy_snapshot AS current_vacancy
FULL OUTER JOIN stage_previous_fact_vacancy_snapshot AS previous_vacancy
    USING (portal_id)
CROSS JOIN current_snapshot_date
CROSS JOIN previous_snapshot_date
WHERE current_vacancy.portal_id IS NULL
    OR previous_vacancy.portal_id IS NULL;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        invalid_rows = connection.execute(f"""
            SELECT
                snapshot_date,
                previous_snapshot_date,
                event_type
            FROM {cls.name}
            WHERE previous_snapshot_date IS NULL
                OR previous_snapshot_date >= snapshot_date
                OR event_type NOT IN ('NEW', 'REMOVED')
            LIMIT 10
        """).fetchall()

        if invalid_rows:
            raise ValueError(
                f"Found invalid snapshot dates or event types in {cls.name}: "
                f"{invalid_rows}"
            )

        inconsistent_rows = connection.execute(f"""
            SELECT event.portal_id, event.event_type
            FROM {cls.name} AS event
            LEFT JOIN fact_vacancy_snapshot AS current_vacancy
                ON current_vacancy.portal_id = event.portal_id
            LEFT JOIN stage_previous_fact_vacancy_snapshot AS previous_vacancy
                ON previous_vacancy.portal_id = event.portal_id
            WHERE (event.event_type = 'NEW'
                    AND (current_vacancy.portal_id IS NULL
                        OR previous_vacancy.portal_id IS NOT NULL))
                OR (event.event_type = 'REMOVED'
                    AND (current_vacancy.portal_id IS NOT NULL
                        OR previous_vacancy.portal_id IS NULL))
            LIMIT 10
        """).fetchall()

        if inconsistent_rows:
            raise ValueError(
                f"Found event rows inconsistent with their source snapshots in "
                f"{cls.name}: {inconsistent_rows}"
            )
