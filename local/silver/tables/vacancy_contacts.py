import duckdb

from silver.tables.base import BaseTable


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
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.jmeno
        AS contact_person_first_name,
    vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.prijmeni
        AS contact_person_last_name,
    vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.titulPredJmenem
        AS contact_person_title_before_name,
    vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.titulZaJmenem
        AS contact_person_title_after_name,
    vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.poziceVeSpolecnosti
        AS contact_person_company_position,
    vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.email
        AS contact_person_email,
    vacancy.prvniKontaktSeZamestnavatelem.komuSeHlasit.telefon
        AS contact_person_phone,

    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.email
        AS contact_location_email,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.telefon
        AS contact_location_phone,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.mistoKontaktu
        AS contact_place,

    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.kodAdresnihoMista
        AS address_place_code,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.psc
        AS postal_code,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.kraj.id
        AS region_id,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.okres.id
        AS district_id,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.obec.id
        AS municipality_id,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.mestskyObvodMestskaCast.id
        AS municipal_district_id,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.mestskyObvodVPraze.id
        AS prague_district_id,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.castObce.id
        AS municipality_part_id,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.ulice.nazev
        AS street_name,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.cisloDomovni
        AS house_number,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.cisloOrientacni
        AS orientation_number,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.typCislaDomovniho.id
        AS house_number_type_id,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.dodatekAdresy
        AS address_suffix,
    vacancy.prvniKontaktSeZamestnavatelem.kdeSeHlasit.adresa.nazevCastiObce
        AS municipality_part_name
FROM staged_vacancies AS vacancy;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
