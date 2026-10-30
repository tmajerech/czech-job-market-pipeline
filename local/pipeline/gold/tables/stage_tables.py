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
        source_path = (
            silver_root
            / table_name
            / f"snapshot_date={snapshot_date.isoformat()}"
            / "part-*.parquet"
        )

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
