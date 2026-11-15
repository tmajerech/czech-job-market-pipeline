import argparse
from datetime import date
from pathlib import Path

import duckdb

from config import Config
from pipeline.base_table import BaseTable
from pipeline.silver.tables import (
    VacanciesTable,
    VacancyBenefitsTable,
    VacancyContactsTable,
    VacancyRequiredLanguageTable,
    VacancyRequiredSkillsTable,
    VacancyWorkplacesTable,
)
from pipeline.silver.tables.codelists import (
    ContactOfficesTable,
    DistrictsTable,
    MunicipalitiesTable,
    OccupationsTable,
    PublishTypesTable,
    RegionsTable,
    SalaryTypesTable,
    ShiftPatternsTable,
    WorkLocationTypesTable,
)

LOCAL_DIR = Path(__file__).parent
BRONZE_ROOT = LOCAL_DIR / Config.BRONZE_PATH
DATABASE_PATH = LOCAL_DIR / "silver.duckdb"
MAXIMUM_OBJECT_SIZE = 512 * 1024 * 1024
SILVER_ROOT = LOCAL_DIR / Config.SILVER_PATH
SILVER_TABLES = (
    VacanciesTable,
    VacancyWorkplacesTable,
    VacancyBenefitsTable,
    VacancyRequiredSkillsTable,
    VacancyRequiredLanguageTable,
    VacancyContactsTable,
)
CODELISTS: tuple[tuple[type[BaseTable], str], ...] = (
    (OccupationsTable, "cz-isco.json.gz"),
    (RegionsTable, "kraje.json.gz"),
    (DistrictsTable, "okresy.json.gz"),
    (MunicipalitiesTable, "obce.json.gz"),
    (SalaryTypesTable, "typy-mzdy.json.gz"),
    (ShiftPatternsTable, "smennosti.json.gz"),
    (PublishTypesTable, "zverejnovat-vpm.json.gz"),
    (WorkLocationTypesTable, "typy-mista-vykonu-prace.json.gz"),
    (ContactOfficesTable, "kontaktni-pracoviste.json.gz"),
)


def stage_codelist(
    connection: duckdb.DuckDBPyConnection,
    codelists_directory: Path,
    table: type[BaseTable],
    filename: str,
) -> None:
    source_path = codelists_directory / filename
    if not source_path.is_file():
        raise FileNotFoundError(f"Missing {table.name} codelist: {source_path}")

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE staged_{table.name} AS
        SELECT
            CAST(source.snapshot_date AS DATE) AS snapshot_date,
            item.*
        FROM read_json(
            ?,
            hive_partitioning = true
        ) AS source
        CROSS JOIN LATERAL UNNEST(source.polozky)
            AS items(item);
        """,
        [str(source_path)],
    )


argument_parser = argparse.ArgumentParser(
    description="Build Silver tables from a local Bronze snapshot"
)
argument_parser.add_argument(
    "--snapshot-date",
    type=date.fromisoformat,
    help="Snapshot date to process; defaults to the latest Bronze snapshot",
)
arguments = argument_parser.parse_args()

if arguments.snapshot_date is None:
    snapshot_path = max(
        BRONZE_ROOT.glob("volna-mista/snapshot_date=*/volna-mista.json.gz"),
        key=lambda path: path.parent.name,
    )
    snapshot_date = date.fromisoformat(
        snapshot_path.parent.name.removeprefix("snapshot_date=")
    )
else:
    snapshot_date = arguments.snapshot_date
    snapshot_path = (
        BRONZE_ROOT
        / "volna-mista"
        / f"snapshot_date={snapshot_date.isoformat()}"
        / "volna-mista.json.gz"
    )
    if not snapshot_path.is_file():
        raise FileNotFoundError(f"Missing Bronze vacancy snapshot: {snapshot_path}")

codelists_directory = BRONZE_ROOT / "codelists" / f"snapshot_date={snapshot_date.isoformat()}"

connection = duckdb.connect(DATABASE_PATH)
connection.execute(
    """
    CREATE OR REPLACE TEMP TABLE staged_vacancies AS
    SELECT
        CAST(source.snapshot_date AS DATE) AS snapshot_date,
        vacancy.*
    FROM read_json(
        ?,
        maximum_object_size = ?,
        hive_partitioning = true
    ) AS source,
    UNNEST(source.polozky) AS items(vacancy);
    """,
    [str(snapshot_path), MAXIMUM_OBJECT_SIZE],
)

for table, filename in CODELISTS:
    stage_codelist(connection, codelists_directory, table, filename)


# at this point we have rows with the first level unpacked

# make sure we have only the expected columns and none are missing
required_columns = {
    "id",
    "portalId",
    "mistoVykonuPrace",
    "zamestnavatel",
    "prvniKontaktSeZamestnavatelem",
}


known_columns = required_columns | {
    "snapshot_date",  # technical column
    "azylant",
    "cizinecMimoEu",
    "datumVlozeni",
    "datumZmeny",
    "expirace",
    "kontaktniPracoviste",
    "mesicniMzdaDo",
    "mesicniMzdaOd",
    "minPozadovaneVzdelani",
    "modraKarta",
    "pocetHodinTydne",
    "pocetMist",
    "pozadovanaDovednost",
    "pozadovanaJazykovaZnalost",
    "pozadovanaProfese",
    "pozadovanePovolani",
    "pozadovaneVzdelani",
    "pracovnePravniVztahy",
    "profeseCzIsco",
    "referencniCislo",
    "smennost",
    "souhlasAgenturyAgentura",
    "souhlasAgenturyUzivatel",
    "statniSpravaSamosprava",
    "terminUkonceniPracovnihoPomeru",
    "terminZahajeniPracovnihoPomeru",
    "typMzdy",
    "upresnujiciInformace",
    "urlAdresa",
    "vhodnostiPracovnihoMista",
    "vyhodyVolnehoMista",
    "zamestnaneckaKarta",
    "zverejnovat",
}

source_columns = {row[0] for row in connection.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
            AND UPPER(table_name) = 'STAGED_VACANCIES'
        ORDER BY ordinal_position
    """).fetchall()}
missing_columns = required_columns - source_columns
extra_columns = source_columns - known_columns

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")
if extra_columns:
    raise ValueError(f"Unexpected columns found: {extra_columns}")

for table, _ in CODELISTS:
    table.create(connection)
    table.validate(connection)
    table.export(connection, SILVER_ROOT, snapshot_date)

for table in SILVER_TABLES:
    table.create(connection)
    table.validate(connection)
    table.export(connection, SILVER_ROOT, snapshot_date)
