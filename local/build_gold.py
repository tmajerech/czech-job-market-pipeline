import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import duckdb

from config import Config
from pipeline.gold.tables import (
    BridgeVacancyRegionTable,
    DimContactOfficeTable,
    DimEmployerTable,
    DimMunicipalityTable,
    DimOccupationTable,
    DimPublishTypeTable,
    DimRegionTable,
    DimSalaryTypeTable,
    DimShiftPatternTable,
    DimWorkLocationTypeTable,
    FactVacancyEventTable,
    FactVacancySnapshotTable,
)
from pipeline.gold.tables.stage_tables import (
    create_stage_tables,
    stage_previous_fact_vacancy_snapshot,
)

LOCAL_DIR = Path(__file__).parent
SILVER_ROOT = LOCAL_DIR / Config.SILVER_PATH
GOLD_ROOT = LOCAL_DIR / Config.GOLD_PATH
DATABASE_PATH = LOCAL_DIR / "gold.duckdb"
GOLD_TABLES = (
    DimOccupationTable,
    DimRegionTable,
    DimMunicipalityTable,
    DimSalaryTypeTable,
    DimShiftPatternTable,
    DimPublishTypeTable,
    DimWorkLocationTypeTable,
    DimContactOfficeTable,
    DimEmployerTable,
    BridgeVacancyRegionTable,
    FactVacancySnapshotTable,
)


def build_gold_snapshot(
    snapshot_date: date,
    silver_root: Path = SILVER_ROOT,
    gold_root: Path = GOLD_ROOT,
    database_path: Path = DATABASE_PATH,
) -> None:
    snapshot_directory = (
        silver_root / "vacancies" / f"snapshot_date={snapshot_date.isoformat()}"
    )
    if not snapshot_directory.is_dir():
        raise FileNotFoundError(f"Missing Silver vacancies snapshot: {snapshot_directory}")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_path))
    try:
        create_stage_tables(
            connection=connection,
            silver_root=silver_root,
            snapshot_date=snapshot_date,
        )

        for table in GOLD_TABLES:
            table.create(connection)
            table.validate(connection)
            table.export(connection, gold_root, snapshot_date)

        previous_snapshot_date = stage_previous_fact_vacancy_snapshot(
            connection=connection,
            gold_root=gold_root,
            current_snapshot_date=snapshot_date,
        )

        if previous_snapshot_date is not None:
            FactVacancyEventTable.create(connection)
            FactVacancyEventTable.validate(connection)
            FactVacancyEventTable.export(connection, gold_root, snapshot_date)
    finally:
        connection.close()


def main(argv: Sequence[str] | None = None) -> None:
    argument_parser = argparse.ArgumentParser(
        description="Build Gold tables from a local Silver snapshot"
    )
    argument_parser.add_argument(
        "--snapshot-date",
        type=date.fromisoformat,
        help="Snapshot date to process; defaults to the latest Silver snapshot",
    )
    arguments = argument_parser.parse_args(argv)

    if arguments.snapshot_date is None:
        snapshot_directory = max(
            (SILVER_ROOT / "vacancies").glob("snapshot_date=*"),
            key=lambda path: path.name,
        )
        snapshot_date = date.fromisoformat(
            snapshot_directory.name.removeprefix("snapshot_date=")
        )
    else:
        snapshot_date = arguments.snapshot_date

    build_gold_snapshot(snapshot_date)


if __name__ == "__main__":
    main()
