"""Load one Silver snapshot into temporary Gold input tables."""

from datetime import date
from pathlib import Path

import duckdb

from pipeline.snapshot_publish import require_readable_snapshot, snapshot_is_incomplete

SILVER_TABLES = (
    "vacancies",
    "vacancy_workplaces",
    "vacancy_benefits",
    "vacancy_required_skills",
    "vacancy_required_language",
    "occupations",
    "salary_types",
    "shift_patterns",
    "publish_types",
    "work_location_types",
    "contact_offices",
    "regions",
    "districts",
    "municipalities",
)


def create_stage_tables(
    connection: duckdb.DuckDBPyConnection,
    silver_root: Path,
    snapshot_date: date,
) -> None:
    require_readable_snapshot(silver_root, snapshot_date, "Silver")

    for table_name in SILVER_TABLES:
        source_path = silver_root / table_name / f"snapshot_date={snapshot_date.isoformat()}" / "part-*.parquet"

        connection.execute(
            f"""
            CREATE OR REPLACE TEMP TABLE stage_{table_name} AS
            SELECT *
            FROM read_parquet(
                ?,
                hive_partitioning = true,
                union_by_name = true
            );
            """,
            [str(source_path)],
        )


def fact_snapshot_dates(gold_root: Path) -> list[date]:
    fact_root = gold_root / "fact_vacancy_snapshot"
    snapshot_dates = []
    for directory in fact_root.glob("snapshot_date=*"):
        partition_date = directory.name.removeprefix("snapshot_date=")
        if not partition_date:
            continue

        parsed_date = date.fromisoformat(partition_date)
        has_parquet_files = any(directory.glob("part-*.parquet"))
        if has_parquet_files and not snapshot_is_incomplete(gold_root, parsed_date):
            snapshot_dates.append(parsed_date)

    return sorted(snapshot_dates)


def stage_fact_vacancy_snapshot(
    connection: duckdb.DuckDBPyConnection,
    gold_root: Path,
    snapshot_date: date,
    allow_incomplete: bool = False,
) -> None:
    if not allow_incomplete:
        require_readable_snapshot(gold_root, snapshot_date, "Gold")
    source_path = (
        gold_root
        / "fact_vacancy_snapshot"
        / f"snapshot_date={snapshot_date.isoformat()}"
        / "part-*.parquet"
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE fact_vacancy_snapshot AS
        SELECT
            snapshot_date,
            portal_id
        FROM read_parquet(
            ?,
            hive_partitioning = true,
            union_by_name = true
        );
        """,
        [str(source_path)],
    )


def create_event_snapshot_context(
    connection: duckdb.DuckDBPyConnection,
    snapshot_date: date,
    previous_snapshot_date: date,
) -> None:
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE event_snapshot_context AS
        SELECT
            CAST(? AS DATE) AS snapshot_date,
            CAST(? AS DATE) AS previous_snapshot_date;
        """,
        [snapshot_date, previous_snapshot_date],
    )


def stage_previous_fact_vacancy_snapshot(
    connection: duckdb.DuckDBPyConnection,
    gold_root: Path,
    current_snapshot_date: date,
) -> date | None:
    fact_root = gold_root / "fact_vacancy_snapshot"
    previous_dates = [
        snapshot_date
        for snapshot_date in fact_snapshot_dates(gold_root)
        if snapshot_date < current_snapshot_date
    ]

    if not previous_dates:
        return None

    previous_snapshot_date = max(previous_dates)
    source_path = (
        fact_root
        / f"snapshot_date={previous_snapshot_date.isoformat()}"
        / "part-*.parquet"
    )

    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE
            stage_previous_fact_vacancy_snapshot AS
        SELECT
            snapshot_date,
            portal_id
        FROM read_parquet(
            ?,
            hive_partitioning = true,
            union_by_name = true
        );
        """,
        [str(source_path)],
    )

    return previous_snapshot_date
