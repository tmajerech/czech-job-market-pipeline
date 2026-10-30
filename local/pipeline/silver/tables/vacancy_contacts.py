import duckdb

from pipeline.base_table import BaseTable


class VacancyContactsTable(BaseTable):
    """Separate table because of PII"""

    name = "vacancy_contacts"
    grain_columns = ("snapshot_date", "portal_id")
    publish = False

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    CAST(vacancy.snapshot_date AS DATE) AS snapshot_date,
    CAST(vacancy.portalId AS BIGINT) AS portal_id,

    CAST(vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.jmeno AS VARCHAR)
        AS contact_person_first_name,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.prijmeni AS VARCHAR)
        AS contact_person_last_name,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.titulPredJmenem AS VARCHAR)
        AS contact_person_title_before_name,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.titulZaJmenem AS VARCHAR)
        AS contact_person_title_after_name,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.poziceVeSpolecnosti AS VARCHAR)
        AS contact_person_company_position,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.email AS VARCHAR)
        AS contact_person_email,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.telefon AS VARCHAR)
        AS contact_person_phone,

    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.email AS VARCHAR)
        AS contact_location_email,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.telefon AS VARCHAR)
        AS contact_location_phone,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.mistoKontaktu AS VARCHAR)
        AS contact_place,

    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.kodAdresnihoMista AS BIGINT)
        AS address_place_code,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.psc AS VARCHAR)
        AS postal_code,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.kraj.id AS VARCHAR)
        AS region_id,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.okres.id AS VARCHAR)
        AS district_id,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.obec.id AS VARCHAR)
        AS municipality_id,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.mestskyObvodMestskaCast.id AS VARCHAR)
        AS municipal_district_id,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.mestskyObvodVPraze.id AS VARCHAR)
        AS prague_district_id,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.castObce.id AS VARCHAR)
        AS municipality_part_id,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.ulice.nazev AS VARCHAR)
        AS street_name,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.cisloDomovni AS BIGINT)
        AS house_number,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.cisloOrientacni AS VARCHAR)
        AS orientation_number,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.typCislaDomovniho.id AS VARCHAR)
        AS house_number_type_id,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.dodatekAdresy AS VARCHAR)
        AS address_suffix,
    CAST(vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.nazevCastiObce AS VARCHAR)
        AS municipality_part_name
FROM staged_vacancies AS vacancy;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
