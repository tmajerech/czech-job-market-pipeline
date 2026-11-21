from datetime import date

import pytest

from pipeline.gold.tables.fact_vacancy_event import FactVacancyEventTable
from pipeline.gold.tables.fact_vacancy_snapshot import FactVacancySnapshotTable
from pipeline.gold.tables.stage_tables import create_event_snapshot_context


def test_event_fact_emits_new_and_removed_but_not_unchanged(connection) -> None:
    connection.execute("""
        CREATE TEMP TABLE fact_vacancy_snapshot AS
        SELECT DATE '2026-11-14' AS snapshot_date, portal_id
        FROM (VALUES (10), (11)) AS vacancies(portal_id)
    """)
    connection.execute("""
        CREATE TEMP TABLE stage_previous_fact_vacancy_snapshot AS
        SELECT DATE '2026-11-08' AS snapshot_date, portal_id
        FROM (VALUES (11), (12)) AS vacancies(portal_id)
    """)
    create_event_snapshot_context(
        connection,
        snapshot_date=date(2026, 11, 14),
        previous_snapshot_date=date(2026, 11, 8),
    )

    FactVacancyEventTable.create(connection)
    events = connection.execute("""
        SELECT snapshot_date, portal_id, previous_snapshot_date, event_type
        FROM fact_vacancy_event
        ORDER BY portal_id
    """).fetchall()

    assert events == [
        (date(2026, 11, 14), 10, date(2026, 11, 8), "NEW"),
        (date(2026, 11, 14), 12, date(2026, 11, 8), "REMOVED"),
    ]
    FactVacancyEventTable.validate(connection)


def test_event_fact_rejects_event_inconsistent_with_source_snapshots(connection) -> None:
    connection.execute("""
        CREATE TEMP TABLE fact_vacancy_snapshot AS
        SELECT DATE '2026-11-14' AS snapshot_date, portal_id
        FROM (VALUES (10)) AS vacancies(portal_id)
    """)
    connection.execute("""
        CREATE TEMP TABLE stage_previous_fact_vacancy_snapshot AS
        SELECT DATE '2026-11-08' AS snapshot_date, portal_id
        FROM (VALUES (11)) AS vacancies(portal_id)
    """)
    create_event_snapshot_context(
        connection,
        snapshot_date=date(2026, 11, 14),
        previous_snapshot_date=date(2026, 11, 8),
    )
    FactVacancyEventTable.create(connection)
    connection.execute("""
        UPDATE fact_vacancy_event
        SET event_type = 'REMOVED'
        WHERE portal_id = 10
    """)

    with pytest.raises(ValueError, match="inconsistent with their source snapshots"):
        FactVacancyEventTable.validate_custom(connection)


def test_vacancy_fact_rejects_unknown_occupation_reference(connection) -> None:
    connection.execute("""
        CREATE TEMP TABLE stage_vacancies AS
        SELECT 10 AS portal_id
    """)
    connection.execute("""
        CREATE TEMP TABLE fact_vacancy_snapshot AS
        SELECT DATE '2026-11-14' AS snapshot_date, 'unknown' AS occupation_id
    """)
    connection.execute("""
        CREATE TEMP TABLE dim_occupation (
            snapshot_date DATE,
            occupation_id VARCHAR
        )
    """)

    with pytest.raises(RuntimeError, match="occupation ids.*do not exist"):
        FactVacancySnapshotTable.validate_custom(connection)
