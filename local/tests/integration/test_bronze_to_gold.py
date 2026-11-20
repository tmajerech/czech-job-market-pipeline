from datetime import date

import duckdb

from build_gold import build_gold_snapshot
from build_silver import build_silver_snapshot
from tests.integration.fixtures.tiny_bronze import write_snapshot


def read_parquet_rows(path, query):
    connection = duckdb.connect(":memory:")
    try:
        return connection.execute(query, [str(path)]).fetchall()
    finally:
        connection.close()


def test_two_bronze_snapshots_build_silver_gold_and_events(tmp_path) -> None:
    bronze_root = tmp_path / "bronze"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    database_root = tmp_path / "databases"
    snapshots = (
        (date(2026, 11, 8), (100, 200)),
        (date(2026, 11, 14), (100, 300)),
    )

    for snapshot_date, portal_ids in snapshots:
        write_snapshot(bronze_root, snapshot_date, portal_ids)
        build_silver_snapshot(
            snapshot_date,
            bronze_root=bronze_root,
            silver_root=silver_root,
            database_path=database_root / "silver.duckdb",
        )
        build_gold_snapshot(
            snapshot_date,
            silver_root=silver_root,
            gold_root=gold_root,
            database_path=database_root / "gold.duckdb",
        )

    first_event_partition = (
        gold_root
        / "fact_vacancy_event"
        / "snapshot_date=2026-11-08"
        / "part-00000.parquet"
    )
    assert not first_event_partition.exists()

    event_file = (
        gold_root
        / "fact_vacancy_event"
        / "snapshot_date=2026-11-14"
        / "part-00000.parquet"
    )
    events = read_parquet_rows(
        event_file,
        """
        SELECT portal_id, event_type, previous_snapshot_date
        FROM read_parquet(?)
        ORDER BY portal_id
        """,
    )

    assert events == [
        (200, "REMOVED", date(2026, 11, 8)),
        (300, "NEW", date(2026, 11, 8)),
    ]

    fact_file = (
        gold_root
        / "fact_vacancy_snapshot"
        / "snapshot_date=2026-11-14"
        / "part-00000.parquet"
    )
    fact_rows = read_parquet_rows(
        fact_file,
        """
        SELECT portal_id, location_scope, region_count
        FROM read_parquet(?)
        ORDER BY portal_id
        """,
    )
    assert fact_rows == [
        (100, "single_region", 1),
        (300, "single_region", 1),
    ]
