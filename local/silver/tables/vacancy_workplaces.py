import duckdb

from silver.tables.base import BaseTable


class VacancyWorkplacesTable(BaseTable):
    name = "vacancy_workplaces"
    grain_columns = ("snapshot_date", "portal_id", "workplace_name")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(vacancy.snapshot_date AS DATE) AS snapshot_date,
    CAST(vacancy.portalId AS BIGINT) AS portal_id,

    CAST(workplace.nazev AS VARCHAR) AS workplace_name,

    CAST(workplace.adresa.kodAdresnihoMista AS BIGINT)
        AS address_place_code,
    CAST(workplace.adresa.psc AS VARCHAR)
        AS postal_code,
    CAST(workplace.adresa.kraj.id AS VARCHAR)
        AS region_id,
    CAST(workplace.adresa.okres.id AS VARCHAR)
        AS district_id,
    CAST(workplace.adresa.obec.id AS VARCHAR)
        AS municipality_id,
    CAST(workplace.adresa.mestskyObvodMestskaCast.id AS VARCHAR)
        AS municipal_district_id,
    CAST(workplace.adresa.mestskyObvodVPraze.id AS VARCHAR)
        AS prague_district_id,
    CAST(workplace.adresa.castObce.id AS VARCHAR)
        AS municipality_part_id,
    CAST(workplace.adresa.ulice.nazev AS VARCHAR)
        AS street_name,
    CAST(workplace.adresa.cisloDomovni AS BIGINT)
        AS house_number,
    CAST(workplace.adresa.cisloOrientacni AS VARCHAR)
        AS orientation_number,
    CAST(workplace.adresa.typCislaDomovniho.id AS VARCHAR)
        AS house_number_type_id,
    CAST(workplace.adresa.dodatekAdresy AS VARCHAR)
        AS address_suffix,
    CAST(workplace.adresa.nazevCastiObce AS VARCHAR)
        AS municipality_part_name
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.mistoVykonuPrace.pracoviste
) AS unnested_workplaces(workplace);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
