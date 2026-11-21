"""Snapshot-level staging and publication helpers for local pipeline layers."""

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4


STATUS_DIRECTORY = "_snapshots"
INCOMPLETE_MARKER = "_INCOMPLETE"
SUCCESS_MARKER = "_SUCCESS"


def _snapshot_status_directory(output_root: Path, snapshot_date: date) -> Path:
    return output_root / STATUS_DIRECTORY / f"snapshot_date={snapshot_date.isoformat()}"


def snapshot_is_incomplete(output_root: Path, snapshot_date: date) -> bool:
    return (_snapshot_status_directory(output_root, snapshot_date) / INCOMPLETE_MARKER).is_file()


def require_readable_snapshot(
    output_root: Path,
    snapshot_date: date,
    layer_name: str,
) -> None:
    if snapshot_is_incomplete(output_root, snapshot_date):
        raise RuntimeError(
            f"{layer_name} snapshot {snapshot_date} has an incomplete publication marker"
        )


def mark_snapshot_incomplete(
    output_root: Path,
    snapshot_date: date,
    reason: str,
) -> None:
    status_directory = _snapshot_status_directory(output_root, snapshot_date)
    status_directory.mkdir(parents=True, exist_ok=True)
    _write_marker(
        status_directory / INCOMPLETE_MARKER,
        {
            "snapshot_date": snapshot_date.isoformat(),
            "marked_at_utc": datetime.now(UTC).isoformat(),
            "reason": reason,
        },
    )


@contextmanager
def temporary_output_root(output_root: Path, snapshot_date: date) -> Iterator[Path]:
    """Create a staging root on the same filesystem as the final layer root."""
    output_root.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
        prefix=f".{output_root.name}-{snapshot_date.isoformat()}-",
        dir=output_root.parent,
    ) as temporary_directory:
        yield Path(temporary_directory)


def _write_marker(path: Path, payload: dict[str, object]) -> None:
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary_path.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def publish_staged_snapshot(
    staged_root: Path,
    output_root: Path,
    snapshot_date: date,
    table_names: Iterable[str],
    delete_table_names: Iterable[str] = (),
) -> None:
    """Publish staged Parquet files and expose success only after every replacement.

    Existing legacy snapshots without markers remain readable. A failed or interrupted
    publication leaves ``_INCOMPLETE`` behind so in-repository consumers refuse to
    combine files from different attempts.
    """
    published_tables = tuple(table_names)
    deleted_tables = tuple(delete_table_names)

    staged_paths = {
        table_name: (
            staged_root
            / table_name
            / f"snapshot_date={snapshot_date.isoformat()}"
            / "part-00000.parquet"
        )
        for table_name in published_tables
    }
    missing_staged_paths = [
        str(path) for path in staged_paths.values() if not path.is_file()
    ]
    if missing_staged_paths:
        raise FileNotFoundError(
            f"Missing staged snapshot files: {missing_staged_paths}"
        )

    status_directory = _snapshot_status_directory(output_root, snapshot_date)
    status_directory.mkdir(parents=True, exist_ok=True)
    incomplete_marker = status_directory / INCOMPLETE_MARKER
    success_marker = status_directory / SUCCESS_MARKER
    marker_payload = {
        "snapshot_date": snapshot_date.isoformat(),
        "published_at_utc": datetime.now(UTC).isoformat(),
        "published_tables": published_tables,
        "deleted_tables": deleted_tables,
    }
    _write_marker(incomplete_marker, marker_payload)

    try:
        for table_name, staged_path in staged_paths.items():
            final_directory = (
                output_root
                / table_name
                / f"snapshot_date={snapshot_date.isoformat()}"
            )
            final_directory.mkdir(parents=True, exist_ok=True)
            final_path = final_directory / "part-00000.parquet"
            staged_path.replace(final_path)

            for stale_path in final_directory.glob("part-*.parquet"):
                if stale_path != final_path:
                    stale_path.unlink()

        for table_name in deleted_tables:
            final_directory = (
                output_root
                / table_name
                / f"snapshot_date={snapshot_date.isoformat()}"
            )
            if final_directory.is_dir():
                for stale_path in final_directory.glob("part-*.parquet"):
                    stale_path.unlink()

        _write_marker(success_marker, marker_payload)
        incomplete_marker.unlink()
    except BaseException:
        # The marker deliberately remains so readers reject a partially replaced snapshot.
        raise
