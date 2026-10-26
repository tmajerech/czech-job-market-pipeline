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
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(portalId AS BIGINT) AS portal_id,
    CAST(id AS VARCHAR) AS id,
    CAST(referencniCislo AS VARCHAR) AS reference_number,

    CAST(azylant AS BOOLEAN) AS asylum_seeker,
    CAST(cizinecMimoEu AS BOOLEAN) AS non_eu_foreign_national,
    CAST(modraKarta AS BOOLEAN) AS blue_card,
    CAST(zamestnaneckaKarta AS BOOLEAN) AS employee_card,

    CAST(datumVlozeni AS TIMESTAMP) AS created_at,
    CAST(datumZmeny AS TIMESTAMP) AS updated_at,
    CAST(expirace AS DATE) AS expiration_date,
    CAST(terminUkonceniPracovnihoPomeru AS DATE)
        AS employment_end_date,
    CAST(terminZahajeniPracovnihoPomeru AS DATE)
        AS employment_start_date,

    CAST(mesicniMzdaDo AS DECIMAL(18,2)) AS monthly_salary_to,
    CAST(mesicniMzdaOd AS DECIMAL(18,2)) AS monthly_salary_from,
    CAST(pocetHodinTydne AS DECIMAL(5,2)) AS weekly_hours,
    CAST(pocetMist AS BIGINT) AS number_of_positions,

    CAST({extract_cs_text_sql("pozadovanaProfese")} AS VARCHAR)
        AS required_profession,
    CAST({extract_cs_text_sql("upresnujiciInformace")} AS VARCHAR)
        AS additional_information,
    CAST(urlAdresa AS VARCHAR) AS url_address,

    CAST(statniSpravaSamosprava AS BOOLEAN) AS public_administration,
    CAST(souhlasAgenturyAgentura AS BOOLEAN) AS agency_agency_consent,
    CAST(souhlasAgenturyUzivatel AS BOOLEAN) AS agency_user_consent,

    CAST(minPozadovaneVzdelani.id AS VARCHAR) AS minimum_required_education_id,
    CAST(smennost.id AS VARCHAR) AS shift_pattern_id,
    CAST(typMzdy.id AS VARCHAR) AS salary_type_id,
    CAST(zverejnovat.id AS VARCHAR) AS publish_type_id,

    CAST(mistoVykonuPrace.typMistaVykonuPrace.id AS VARCHAR)
        AS work_location_type_id,
    CAST(mistoVykonuPrace.obec.id AS VARCHAR)
        AS work_location_municipality_id,
    CAST(
        LIST_TRANSFORM(
            mistoVykonuPrace.okresy,
            district -> district.id
        ) AS VARCHAR[]
    ) AS work_location_district_ids,
    CAST(mistoVykonuPrace.adresaText AS VARCHAR)
        AS work_location_address_text,

    CAST(zamestnavatel.ico AS VARCHAR) AS employer_ico,
    CAST(zamestnavatel.nazev AS VARCHAR) AS employer_name,

    CAST(profeseCzIsco.id AS VARCHAR) AS profession_cz_isco_id,
    CAST(
        LIST_TRANSFORM(
            pracovnePravniVztahy,
            relation -> relation.id
        ) AS VARCHAR[]
    ) AS employment_relation_type_ids,
    CAST(
        LIST_TRANSFORM(
            vhodnostiPracovnihoMista,
            suitability -> suitability.id
        ) AS VARCHAR[]
    ) AS work_place_suitability_type_ids,
    CAST(
        LIST_TRANSFORM(
            pozadovaneVzdelani,
            education -> education.id
        ) AS VARCHAR[]
    ) AS required_education_ids,

    CAST(kontaktniPracoviste.id AS VARCHAR) AS contact_office_id
FROM staged_vacancies;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        pass
