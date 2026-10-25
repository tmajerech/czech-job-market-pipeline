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
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    workplace.nazev AS workplace_name,

    workplace.adresa.kodAdresnihoMista
        AS address_place_code,
    workplace.adresa.psc
        AS postal_code,
    workplace.adresa.kraj.id
        AS region_id,
    workplace.adresa.okres.id
        AS district_id,
    workplace.adresa.obec.id
        AS municipality_id,
    workplace.adresa.mestskyObvodMestskaCast.id
        AS municipal_district_id,
    workplace.adresa.mestskyObvodVPraze.id
        AS prague_district_id,
    workplace.adresa.castObce.id
        AS municipality_part_id,
    workplace.adresa.ulice.nazev
        AS street_name,
    workplace.adresa.cisloDomovni
        AS house_number,
    workplace.adresa.cisloOrientacni
        AS orientation_number,
    workplace.adresa.typCislaDomovniho.id
        AS house_number_type_id,
    workplace.adresa.dodatekAdresy
        AS address_suffix,
    workplace.adresa.nazevCastiObce
        AS municipality_part_name
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.mistoVykonuPrace.pracoviste
) AS unnested_workplaces(workplace);
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
