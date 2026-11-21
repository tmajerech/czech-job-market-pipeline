import gzip
import json
from datetime import date

import build_gold as build_gold_module
import duckdb
import pytest

from build_gold import build_gold_snapshot
from build_silver import build_silver_snapshot
from pipeline.snapshot_publish import mark_snapshot_incomplete
from pipeline.silver.tables import VacancyBenefitsTable
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

    for layer_root in (silver_root, gold_root):
        for snapshot_date, _ in snapshots:
            success_marker = (
                layer_root
                / "_snapshots"
                / f"snapshot_date={snapshot_date.isoformat()}"
                / "_SUCCESS"
            )
            assert success_marker.is_file()


def test_targeted_gold_rebuild_refreshes_next_snapshot_events(tmp_path) -> None:
    bronze_root = tmp_path / "bronze"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    database_root = tmp_path / "databases"
    first_snapshot_date = date(2026, 11, 8)
    second_snapshot_date = date(2026, 11, 14)

    for snapshot_date, portal_ids in (
        (first_snapshot_date, (100, 200)),
        (second_snapshot_date, (100, 300)),
    ):
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

    write_snapshot(bronze_root, first_snapshot_date, (100, 300))
    build_silver_snapshot(
        first_snapshot_date,
        bronze_root=bronze_root,
        silver_root=silver_root,
        database_path=database_root / "silver.duckdb",
    )
    build_gold_snapshot(
        first_snapshot_date,
        silver_root=silver_root,
        gold_root=gold_root,
        database_path=database_root / "gold.duckdb",
    )

    event_file = (
        gold_root
        / "fact_vacancy_event"
        / f"snapshot_date={second_snapshot_date.isoformat()}"
        / "part-00000.parquet"
    )
    events = read_parquet_rows(
        event_file,
        "SELECT portal_id, event_type FROM read_parquet(?) ORDER BY portal_id",
    )
    assert events == []


def test_failed_historical_gold_rebuild_does_not_invalidate_later_snapshot(
    tmp_path,
    monkeypatch,
) -> None:
    bronze_root = tmp_path / "bronze"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    database_root = tmp_path / "databases"
    first_snapshot_date = date(2026, 11, 8)
    second_snapshot_date = date(2026, 11, 14)

    for snapshot_date, portal_ids in (
        (first_snapshot_date, (100, 200)),
        (second_snapshot_date, (100, 300)),
    ):
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

    def fail_publication(*, output_root, snapshot_date, **kwargs) -> None:
        mark_snapshot_incomplete(
            output_root,
            snapshot_date,
            reason="Injected historical publication failure",
        )
        raise RuntimeError("injected historical publication failure")

    monkeypatch.setattr(
        build_gold_module,
        "publish_staged_snapshot",
        fail_publication,
    )

    with pytest.raises(RuntimeError, match="injected historical publication failure"):
        build_gold_snapshot(
            first_snapshot_date,
            silver_root=silver_root,
            gold_root=gold_root,
            database_path=database_root / "gold.duckdb",
        )

    first_status_directory = (
        gold_root
        / "_snapshots"
        / f"snapshot_date={first_snapshot_date.isoformat()}"
    )
    second_status_directory = (
        gold_root
        / "_snapshots"
        / f"snapshot_date={second_snapshot_date.isoformat()}"
    )
    assert (first_status_directory / "_INCOMPLETE").is_file()
    assert (second_status_directory / "_SUCCESS").is_file()
    assert not (second_status_directory / "_INCOMPLETE").exists()


def test_failed_silver_rebuild_keeps_previous_snapshot_visible(
    tmp_path,
    monkeypatch,
) -> None:
    snapshot_date = date(2026, 11, 20)
    bronze_root = tmp_path / "bronze"
    silver_root = tmp_path / "silver"
    database_path = tmp_path / "databases" / "silver.duckdb"

    write_snapshot(bronze_root, snapshot_date, (100,))
    build_silver_snapshot(
        snapshot_date,
        bronze_root=bronze_root,
        silver_root=silver_root,
        database_path=database_path,
    )

    write_snapshot(bronze_root, snapshot_date, (100, 200))

    def fail_validation(cls, connection) -> None:
        raise RuntimeError("injected late validation failure")

    monkeypatch.setattr(
        VacancyBenefitsTable,
        "validate_custom",
        classmethod(fail_validation),
    )

    with pytest.raises(RuntimeError, match="injected late validation failure"):
        build_silver_snapshot(
            snapshot_date,
            bronze_root=bronze_root,
            silver_root=silver_root,
            database_path=database_path,
        )

    vacancy_file = (
        silver_root
        / "vacancies"
        / f"snapshot_date={snapshot_date.isoformat()}"
        / "part-00000.parquet"
    )
    vacancy_count = read_parquet_rows(
        vacancy_file,
        "SELECT COUNT(*) FROM read_parquet(?)",
    )
    assert vacancy_count == [(1,)]


def test_gold_build_rejects_incomplete_silver_snapshot(tmp_path) -> None:
    snapshot_date = date(2026, 11, 20)
    bronze_root = tmp_path / "bronze"
    silver_root = tmp_path / "silver"
    gold_root = tmp_path / "gold"
    database_root = tmp_path / "databases"

    write_snapshot(bronze_root, snapshot_date, (100,))
    build_silver_snapshot(
        snapshot_date,
        bronze_root=bronze_root,
        silver_root=silver_root,
        database_path=database_root / "silver.duckdb",
    )

    status_directory = (
        silver_root
        / "_snapshots"
        / f"snapshot_date={snapshot_date.isoformat()}"
    )
    (status_directory / "_INCOMPLETE").write_text("interrupted\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="incomplete publication marker"):
        build_gold_snapshot(
            snapshot_date,
            silver_root=silver_root,
            gold_root=gold_root,
            database_path=database_root / "gold.duckdb",
        )

    assert not (gold_root / "fact_vacancy_snapshot").exists()


def test_silver_build_rejects_missing_required_bronze_column(tmp_path) -> None:
    snapshot_date = date(2026, 11, 20)
    bronze_root = tmp_path / "bronze"
    silver_root = tmp_path / "silver"
    write_snapshot(bronze_root, snapshot_date, (100,))

    vacancy_file = (
        bronze_root
        / "volna-mista"
        / f"snapshot_date={snapshot_date.isoformat()}"
        / "volna-mista.json.gz"
    )
    with gzip.open(vacancy_file, "rt", encoding="utf-8") as source_file:
        payload = json.load(source_file)
    del payload["polozky"][0]["zamestnavatel"]
    with gzip.open(vacancy_file, "wt", encoding="utf-8") as source_file:
        json.dump(payload, source_file, ensure_ascii=False)

    with pytest.raises(ValueError, match="Missing required columns:.*zamestnavatel"):
        build_silver_snapshot(
            snapshot_date,
            bronze_root=bronze_root,
            silver_root=silver_root,
            database_path=tmp_path / "databases" / "silver.duckdb",
        )

    assert not (silver_root / "vacancies").exists()
