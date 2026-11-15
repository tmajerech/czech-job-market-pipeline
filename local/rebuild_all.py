"""Rebuild every available local Silver and Gold snapshot from Bronze."""

import subprocess
import sys
from datetime import date
from pathlib import Path

LOCAL_DIR = Path(__file__).parent
BRONZE_VACANCIES = LOCAL_DIR / "s3_doppelganger/bronze/mpsv/volna-mista"


def partition_dates(root: Path, required_file: str) -> list[date]:
    dates = []
    for directory in root.glob("snapshot_date=*"):
        date_value = directory.name.removeprefix("snapshot_date=")
        if not date_value:
            continue
        if not (directory / required_file).is_file():
            continue
        dates.append(date.fromisoformat(date_value))
    return sorted(dates)


def run_builder(script_name: str, snapshot_date: date) -> None:
    command = [
        sys.executable,
        str(LOCAL_DIR / script_name),
        "--snapshot-date",
        snapshot_date.isoformat(),
    ]
    print(f"Running {script_name} for {snapshot_date}", flush=True)
    subprocess.run(command, check=True, cwd=LOCAL_DIR)


def main() -> None:
    bronze_dates = partition_dates(BRONZE_VACANCIES, "volna-mista.json.gz")
    if not bronze_dates:
        raise FileNotFoundError(
            f"No local Bronze vacancy snapshots found in {BRONZE_VACANCIES}"
        )

    for snapshot_date in bronze_dates:
        run_builder("build_silver.py", snapshot_date)

    for snapshot_date in bronze_dates:
        run_builder("build_gold.py", snapshot_date)


if __name__ == "__main__":
    main()
