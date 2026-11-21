import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import duckdb

from config import Config
from pipeline.base_table import BaseTable
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
    create_event_snapshot_context,
    create_stage_tables,
    fact_snapshot_dates,
    stage_fact_vacancy_snapshot,
    stage_previous_fact_vacancy_snapshot,
)
from pipeline.snapshot_publish import (
    mark_snapshot_incomplete,
    publish_staged_snapshot,
    temporary_output_root,
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


def publish_tables(
    connection: duckdb.DuckDBPyConnection,
    tables: tuple[type[BaseTable], ...],
    gold_root: Path,
    snapshot_date: date,
    delete_table_names: tuple[str, ...] = (),
) -> None:
    with temporary_output_root(gold_root, snapshot_date) as staged_root:
        for table in tables:
            table.export(connection, staged_root, snapshot_date)

        publish_staged_snapshot(
            staged_root=staged_root,
            output_root=gold_root,
            snapshot_date=snapshot_date,
            table_names=(table.name for table in tables),
            delete_table_names=delete_table_names,
        )


def rebuild_event_snapshot(
    connection: duckdb.DuckDBPyConnection,
    gold_root: Path,
    snapshot_date: date,
) -> None:
    mark_snapshot_incomplete(
        gold_root,
        snapshot_date,
        reason="Rebuilding vacancy events after an earlier fact snapshot changed",
    )
    stage_fact_vacancy_snapshot(
        connection,
        gold_root,
        snapshot_date,
        allow_incomplete=True,
    )
    previous_snapshot_date = stage_previous_fact_vacancy_snapshot(
        connection=connection,
        gold_root=gold_root,
        current_snapshot_date=snapshot_date,
    )

    if previous_snapshot_date is None:
        publish_staged_snapshot(
            staged_root=gold_root,
            output_root=gold_root,
            snapshot_date=snapshot_date,
            table_names=(),
            delete_table_names=(FactVacancyEventTable.name,),
        )
        return

    create_event_snapshot_context(
        connection,
        snapshot_date=snapshot_date,
        previous_snapshot_date=previous_snapshot_date,
    )
    FactVacancyEventTable.create(connection)
    FactVacancyEventTable.validate(connection)
    publish_tables(
        connection=connection,
        tables=(FactVacancyEventTable,),
        gold_root=gold_root,
        snapshot_date=snapshot_date,
    )


def rebuild_next_dependent_event_snapshot(
    connection: duckdb.DuckDBPyConnection,
    gold_root: Path,
    rebuilt_snapshot_date: date,
) -> None:
    later_snapshot_dates = [
        snapshot_date
        for snapshot_date in fact_snapshot_dates(gold_root)
        if snapshot_date > rebuilt_snapshot_date
    ]
    if not later_snapshot_dates:
        return

    rebuild_event_snapshot(
        connection=connection,
        gold_root=gold_root,
        snapshot_date=min(later_snapshot_dates),
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

        previous_snapshot_date = stage_previous_fact_vacancy_snapshot(
            connection=connection,
            gold_root=gold_root,
            current_snapshot_date=snapshot_date,
        )

        tables_to_publish = GOLD_TABLES
        delete_table_names: tuple[str, ...] = ()
        if previous_snapshot_date is not None:
            create_event_snapshot_context(
                connection,
                snapshot_date=snapshot_date,
                previous_snapshot_date=previous_snapshot_date,
            )
            FactVacancyEventTable.create(connection)
            FactVacancyEventTable.validate(connection)
            tables_to_publish = (*tables_to_publish, FactVacancyEventTable)
        else:
            delete_table_names = (FactVacancyEventTable.name,)

        publish_tables(
            connection=connection,
            tables=tables_to_publish,
            gold_root=gold_root,
            snapshot_date=snapshot_date,
            delete_table_names=delete_table_names,
        )

        rebuild_next_dependent_event_snapshot(
            connection=connection,
            gold_root=gold_root,
            rebuilt_snapshot_date=snapshot_date,
        )
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
