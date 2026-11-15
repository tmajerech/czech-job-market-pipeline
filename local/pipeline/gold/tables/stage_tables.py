"""Load one Silver snapshot into temporary Gold input tables."""

from datetime import date
from pathlib import Path

import duckdb

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


def stage_previous_fact_vacancy_snapshot(
    connection: duckdb.DuckDBPyConnection,
    gold_root: Path,
    current_snapshot_date: date,
) -> date | None:
    fact_root = gold_root / "fact_vacancy_snapshot"

    previous_dates = []
    for directory in fact_root.glob("snapshot_date=*"):
        partition_date = directory.name.removeprefix("snapshot_date=")
        if not partition_date:
            continue

        parsed_date = date.fromisoformat(partition_date)
        has_parquet_files = any(directory.glob("part-*.parquet"))
        if parsed_date < current_snapshot_date and has_parquet_files:
            previous_dates.append(parsed_date)

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
