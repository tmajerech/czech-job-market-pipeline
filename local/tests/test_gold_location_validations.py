from datetime import date

import pytest

from pipeline.gold.tables.bridge_vacancy_region import BridgeVacancyRegionTable
from pipeline.gold.tables.dim_municipality import DimMunicipalityTable


SNAPSHOT_DATE = date(2026, 11, 14)


def create_bridge_tables(connection, vacancies, regions, bridge_rows) -> None:
    connection.execute("""
        CREATE TEMP TABLE stage_vacancies (
            snapshot_date DATE,
            portal_id BIGINT,
            work_location_type_id VARCHAR
        )
    """)
    connection.execute("""
        CREATE TEMP TABLE dim_region (
            snapshot_date DATE,
            region_id VARCHAR
        )
    """)
    connection.execute("""
        CREATE TEMP TABLE bridge_vacancy_region (
            snapshot_date DATE,
            portal_id BIGINT,
            region_id VARCHAR
        )
    """)

    if vacancies:
        connection.executemany(
            "INSERT INTO stage_vacancies VALUES (?, ?, ?)", vacancies
        )
    if regions:
        connection.executemany("INSERT INTO dim_region VALUES (?, ?)", regions)
    if bridge_rows:
        connection.executemany(
            "INSERT INTO bridge_vacancy_region VALUES (?, ?, ?)", bridge_rows
        )


@pytest.mark.parametrize(
    ("vacancies", "regions", "bridge_rows", "message"),
    [
        (
            [],
            [(SNAPSHOT_DATE, "CZ010")],
            [(SNAPSHOT_DATE, 100, "CZ010")],
            "references unknown vacancies",
        ),
        (
            [(SNAPSHOT_DATE, 100, None)],
            [],
            [(SNAPSHOT_DATE, 100, "CZ010")],
            "references unknown regions",
        ),
        (
            [(SNAPSHOT_DATE, 100, "TypMistaVykonuPrace/celaCR")],
            [(SNAPSHOT_DATE, "CZ010")],
            [(SNAPSHOT_DATE, 100, "CZ010")],
            "Nationwide vacancies must not be expanded",
        ),
    ],
    ids=["unknown-vacancy", "unknown-region", "nationwide-vacancy"],
)
def test_region_bridge_rejects_invalid_references(
    connection, vacancies, regions, bridge_rows, message
) -> None:
    create_bridge_tables(connection, vacancies, regions, bridge_rows)

    with pytest.raises(ValueError, match=message):
        BridgeVacancyRegionTable.validate(connection)


def test_region_bridge_accepts_resolved_regional_vacancy(connection) -> None:
    create_bridge_tables(
        connection,
        [(SNAPSHOT_DATE, 100, None)],
        [(SNAPSHOT_DATE, "CZ010")],
        [(SNAPSHOT_DATE, 100, "CZ010")],
    )

    BridgeVacancyRegionTable.validate(connection)


def test_municipality_dimension_rejects_a_dropped_region_join(connection) -> None:
    connection.execute("""
        CREATE TEMP TABLE stage_municipalities AS
        SELECT
            DATE '2026-11-14' AS snapshot_date,
            'M1' AS municipality_id,
            '000001' AS municipality_code,
            'Test municipality' AS municipality_name,
            'D1' AS district_id
    """)
    connection.execute("""
        CREATE TEMP TABLE stage_districts AS
        SELECT
            DATE '2026-11-14' AS snapshot_date,
            'D1' AS district_id,
            '0001' AS district_code,
            'Test district' AS district_name,
            'CZ0100' AS lau_code,
            'CZ010' AS region_id
    """)
    connection.execute("""
        CREATE TEMP TABLE dim_region (
            snapshot_date DATE,
            region_id VARCHAR,
            region_code VARCHAR,
            region_name VARCHAR,
            nuts3_code VARCHAR
        )
    """)

    DimMunicipalityTable.create(connection)

    with pytest.raises(RuntimeError, match="row count mismatch"):
        DimMunicipalityTable.validate(connection)
