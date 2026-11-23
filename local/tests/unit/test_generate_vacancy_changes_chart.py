from datetime import date

import duckdb

from analytics.generate_vacancy_changes_chart import (
    OccupationChange,
    latest_readable_event_snapshot,
    load_occupation_changes,
    render_svg,
)


def write_parquet(connection, root, table_name, snapshot_date, query):
    output_path = (
        root
        / table_name
        / f"snapshot_date={snapshot_date.isoformat()}"
        / "part-00000.parquet"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    connection.execute(f"COPY ({query}) TO ? (FORMAT PARQUET)", [str(output_path)])


def test_load_occupation_changes_uses_event_specific_fact_and_current_label(tmp_path):
    gold_root = tmp_path / "gold"
    previous_date = date(2026, 1, 1)
    snapshot_date = date(2026, 1, 2)

    with duckdb.connect(":memory:") as connection:
        write_parquet(
            connection,
            gold_root,
            "fact_vacancy_event",
            snapshot_date,
            """
            SELECT * FROM (VALUES
                (DATE '2026-01-02', 10, DATE '2026-01-01', 'NEW'),
                (DATE '2026-01-02', 20, DATE '2026-01-01', 'REMOVED')
            ) AS events(snapshot_date, portal_id, previous_snapshot_date, event_type)
            """,
        )
        write_parquet(
            connection,
            gold_root,
            "fact_vacancy_snapshot",
            previous_date,
            """
            SELECT DATE '2026-01-01' AS snapshot_date, 20 AS portal_id,
                'CzIsco/1' AS occupation_id
            """,
        )
        write_parquet(
            connection,
            gold_root,
            "fact_vacancy_snapshot",
            snapshot_date,
            """
            SELECT DATE '2026-01-02' AS snapshot_date, 10 AS portal_id,
                'CzIsco/1' AS occupation_id
            """,
        )
        write_parquet(
            connection,
            gold_root,
            "dim_occupation",
            previous_date,
            """
            SELECT DATE '2026-01-01' AS snapshot_date, 'CzIsco/1' AS occupation_id,
                '1' AS occupation_code, 'Old label' AS occupation_name
            """,
        )
        write_parquet(
            connection,
            gold_root,
            "dim_occupation",
            snapshot_date,
            """
            SELECT DATE '2026-01-02' AS snapshot_date, 'CzIsco/1' AS occupation_id,
                '1' AS occupation_code, 'Current label' AS occupation_name
            """,
        )

    loaded_snapshot, loaded_previous, changes = load_occupation_changes(gold_root)

    assert (loaded_snapshot, loaded_previous) == (snapshot_date, previous_date)
    assert changes == [OccupationChange("1", "Current label", 1, 1)]


def test_latest_readable_event_snapshot_skips_incomplete_partition(tmp_path):
    gold_root = tmp_path / "gold"
    readable_date = date(2026, 1, 2)
    incomplete_date = date(2026, 1, 3)

    for snapshot_date in (readable_date, incomplete_date):
        event_path = (
            gold_root
            / "fact_vacancy_event"
            / f"snapshot_date={snapshot_date.isoformat()}"
            / "part-00000.parquet"
        )
        event_path.parent.mkdir(parents=True, exist_ok=True)
        event_path.touch()

    marker = (
        gold_root
        / "_snapshots"
        / f"snapshot_date={incomplete_date.isoformat()}"
        / "_INCOMPLETE"
    )
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()

    assert latest_readable_event_snapshot(gold_root) == readable_date


def test_render_svg_escapes_labels_and_includes_counts():
    svg = render_svg(
        date(2026, 1, 2),
        date(2026, 1, 1),
        [OccupationChange("A&1", "Cook <senior>", 12, 7)],
    )

    assert "Cook &lt;senior&gt;" in svg
    assert "CZ-ISCO A&amp;1" in svg
    assert ">12</text>" in svg
    assert ">7</text>" in svg
