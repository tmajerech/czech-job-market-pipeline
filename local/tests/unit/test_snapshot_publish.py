from datetime import date

import pytest

from pipeline.snapshot_publish import (
    publish_staged_snapshot,
    require_readable_snapshot,
)


SNAPSHOT_DATE = date(2026, 11, 21)


def parquet_path(root, table_name):
    return (
        root
        / table_name
        / f"snapshot_date={SNAPSHOT_DATE.isoformat()}"
        / "part-00000.parquet"
    )


def test_publish_staged_snapshot_replaces_files_and_marks_success(tmp_path) -> None:
    staged_root = tmp_path / "staged"
    output_root = tmp_path / "published"
    staged_path = parquet_path(staged_root, "vacancies")
    final_path = parquet_path(output_root, "vacancies")
    staged_path.parent.mkdir(parents=True)
    final_path.parent.mkdir(parents=True)
    staged_path.write_bytes(b"new snapshot")
    final_path.write_bytes(b"old snapshot")
    stale_path = final_path.with_name("part-00001.parquet")
    stale_path.write_bytes(b"stale part")

    publish_staged_snapshot(
        staged_root=staged_root,
        output_root=output_root,
        snapshot_date=SNAPSHOT_DATE,
        table_names=("vacancies",),
    )

    status_directory = (
        output_root
        / "_snapshots"
        / f"snapshot_date={SNAPSHOT_DATE.isoformat()}"
    )
    assert final_path.read_bytes() == b"new snapshot"
    assert not stale_path.exists()
    assert (status_directory / "_SUCCESS").is_file()
    assert not (status_directory / "_INCOMPLETE").exists()


def test_failed_publication_leaves_snapshot_incomplete(tmp_path) -> None:
    staged_root = tmp_path / "staged"
    output_root = tmp_path / "published"
    staged_path = parquet_path(staged_root, "vacancies")
    staged_path.parent.mkdir(parents=True)
    staged_path.write_bytes(b"new snapshot")
    output_root.mkdir()
    (output_root / "vacancies").write_text("blocks directory creation", encoding="utf-8")

    with pytest.raises(OSError):
        publish_staged_snapshot(
            staged_root=staged_root,
            output_root=output_root,
            snapshot_date=SNAPSHOT_DATE,
            table_names=("vacancies",),
        )

    with pytest.raises(RuntimeError, match="incomplete publication marker"):
        require_readable_snapshot(output_root, SNAPSHOT_DATE, "Silver")
