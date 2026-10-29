from datetime import date
from pathlib import Path

import duckdb

from config import Config
from silver.tables import (
    VacanciesTable,
    VacancyBenefitsTable,
    VacancyContactsTable,
    VacancyRequiredLanguageTable,
    VacancyRequiredSkillsTable,
    VacancyWorkplacesTable,
)
from silver.tables.codelists import OccupationsTable, RegionsTable, SalaryTypesTable

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
CODELIST_TABLES = (
    OccupationsTable,
    RegionsTable,
    SalaryTypesTable,
)


snapshot_path = max(
    BRONZE_ROOT.glob("volna-mista/snapshot_date=*/volna-mista.json.gz"),
    key=lambda path: path.parent.name,
)
snapshot_date = date.fromisoformat(snapshot_path.parent.name.removeprefix("snapshot_date="))
codelists_directory = BRONZE_ROOT / "codelists" / f"snapshot_date={snapshot_date.isoformat()}"
occupations_path = codelists_directory / "cz-isco.json.gz"
regions_path = codelists_directory / "kraje.json.gz"
salary_types_path = codelists_directory / "typy-mzdy.json.gz"

if not occupations_path.is_file():
    raise FileNotFoundError(f"Missing occupations codelist: {occupations_path}")
if not regions_path.is_file():
    raise FileNotFoundError(f"Missing regions codelist: {regions_path}")
if not salary_types_path.is_file():
    raise FileNotFoundError(f"Missing salary types codelist: {salary_types_path}")

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

connection.execute(
    """
    CREATE OR REPLACE TEMP TABLE staged_occupations AS
    SELECT
        CAST(source.snapshot_date AS DATE) AS snapshot_date,
        occupation.*
    FROM read_json(
        ?,
        hive_partitioning = true
    ) AS source
    CROSS JOIN LATERAL UNNEST(source.polozky)
        AS occupations(occupation);
    """,
    [str(occupations_path)],
)
connection.execute(
    """
    CREATE OR REPLACE TEMP TABLE staged_regions AS
    SELECT
        CAST(source.snapshot_date AS DATE) AS snapshot_date,
        region.*
    FROM read_json(
        ?,
        hive_partitioning = true
    ) AS source
    CROSS JOIN LATERAL UNNEST(source.polozky)
        AS regions(region);
    """,
    [str(regions_path)],
)
connection.execute(
    """
    CREATE OR REPLACE TEMP TABLE staged_salary_types AS
    SELECT
        CAST(source.snapshot_date AS DATE) AS snapshot_date,
        salary_type.*
    FROM read_json(
        ?,
        hive_partitioning = true
    ) AS source
    CROSS JOIN LATERAL UNNEST(source.polozky)
        AS salary_types(salary_type);
    """,
    [str(salary_types_path)],
)


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

for table in CODELIST_TABLES:
    table.create(connection)
    table.validate(connection)
    table.export(connection, SILVER_ROOT, snapshot_date)

for table in SILVER_TABLES:
    table.create(connection)
    table.validate(connection)
    table.export(connection, SILVER_ROOT, snapshot_date)
