from datetime import date
from pathlib import Path

import duckdb

from config import Config
from pipeline.gold.tables import (
    BridgeVacancyRegionTable,
    DimOccupationTable,
    DimRegionTable,
    FactVacancySnapshotTable,
)
from pipeline.gold.tables.stage_tables import create_stage_tables

LOCAL_DIR = Path(__file__).parent
SILVER_ROOT = LOCAL_DIR / Config.SILVER_PATH
GOLD_ROOT = LOCAL_DIR / Config.GOLD_PATH
DATABASE_PATH = LOCAL_DIR / "gold.duckdb"
GOLD_TABLES = (
    DimOccupationTable,
    DimRegionTable,
    BridgeVacancyRegionTable,
    FactVacancySnapshotTable,
)

connection = duckdb.connect(DATABASE_PATH)

snapshot_directory = max(
    (SILVER_ROOT / "vacancies").glob("snapshot_date=*"),
    key=lambda path: path.name,
)
snapshot_date = date.fromisoformat(snapshot_directory.name.removeprefix("snapshot_date="))

# First load the selected Silver snapshot into stage tables.
create_stage_tables(
    connection=connection,
    silver_root=SILVER_ROOT,
    snapshot_date=snapshot_date,
)

for table in GOLD_TABLES:
    table.create(connection)
    table.validate(connection)
    table.export(connection, GOLD_ROOT, snapshot_date)
