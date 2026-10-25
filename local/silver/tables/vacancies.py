import duckdb

from silver.tables.base import BaseTable
from sql_expressions import extract_cs_text_sql


class VacanciesTable(BaseTable):
    name = "vacancies"
    grain_columns = ("snapshot_date", "portal_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
SELECT
    snapshot_date,
    portalId AS portal_id,
    id,
    referencniCislo AS reference_number,

    azylant,
    cizinecMimoEu AS non_eu_foreign_national,
    modraKarta AS blue_card,
    zamestnaneckaKarta AS employee_card,

    datumVlozeni AS created_at,
    datumZmeny AS updated_at,
    expirace AS expiration_date,
    terminUkonceniPracovnihoPomeru AS employment_end_date,
    terminZahajeniPracovnihoPomeru AS employment_start_date,

    mesicniMzdaDo AS monthly_salary_to,
    mesicniMzdaOd AS monthly_salary_from,
    pocetHodinTydne AS weekly_hours,
    pocetMist AS number_of_positions,

    {extract_cs_text_sql("pozadovanaProfese")} AS required_profession,
    {extract_cs_text_sql("upresnujiciInformace")} AS additional_information,
    urlAdresa AS url_address,

    statniSpravaSamosprava AS public_administration,
    souhlasAgenturyAgentura AS agency_agency_consent,
    souhlasAgenturyUzivatel AS agency_user_consent,

    minPozadovaneVzdelani.id AS minimum_required_education_id,
    smennost.id AS shift_pattern_id,
    typMzdy.id AS salary_type_id,
    zverejnovat.id AS publish_type_id,

    mistoVykonuPrace.typMistaVykonuPrace.id AS work_location_type_id,
    mistoVykonuPrace.obec.id AS work_location_municipality_id,
    LIST_TRANSFORM(
        mistoVykonuPrace.okresy,
        district -> district.id
    ) AS work_location_district_ids,
    mistoVykonuPrace.adresaText AS work_location_address_text,

    zamestnavatel.ico AS employer_ico,
    zamestnavatel.nazev AS employer_name,

    profeseCzIsco.id AS profession_cz_isco_id,
    LIST_TRANSFORM(
        pracovnePravniVztahy,
        relation -> relation.id
    ) AS employment_relation_type_ids,
    LIST_TRANSFORM(
        vhodnostiPracovnihoMista,
        suitability -> suitability.id
    ) AS work_place_suitability_type_ids,
    LIST_TRANSFORM(
        pozadovaneVzdelani,
        education -> education.id
    ) AS required_education_ids,

    kontaktniPracoviste.id AS contact_office_id
FROM staged_vacancies;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
