from pathlib import Path

import duckdb

from config import Config
from sql_expressions import extract_cs_text_sql

LOCAL_DIR = Path(__file__).parent
RAW_DIR = LOCAL_DIR / Config.RAW_PATH
DATABASE_PATH = LOCAL_DIR / "explore.duckdb"
MAXIMUM_OBJECT_SIZE = 512 * 1024 * 1024


snapshot_path = max(
    RAW_DIR.glob("snapshot_date=*/volna-mista.json.gz"),
    key=lambda path: path.parent.name,
)

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

source_columns = {
    row[0]
    for row in connection.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = current_schema()
            AND UPPER(table_name) = 'STAGED_VACANCIES'
        ORDER BY ordinal_position
    """).fetchall()
}
missing_columns = required_columns - source_columns
extra_columns = source_columns - known_columns

if missing_columns:
    raise ValueError(f"Missing required columns: {missing_columns}")
if extra_columns:
    raise ValueError(f"Unexpected columns found: {extra_columns}")

# create the main vacancy table
connection.execute(f"""
CREATE OR REPLACE TEMP TABLE vacancies AS
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
""")

# now lets extract the nested objects into separate tables


# mistoVykonuPrace.pracoviste
connection.execute(f"""
CREATE OR REPLACE TEMP TABLE vacancy_workplaces AS
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
""")


# vyhodyVolnehoMista
connection.execute(f"""
CREATE OR REPLACE TEMP TABLE vacancy_benefits AS
SELECT
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    benefit.vyhoda.id AS benefit_id,
    benefit.popis AS benefit_description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.vyhodyVolnehoMista
) AS unnested_benefits(benefit);
""")

# pozadovanaDovednost
connection.execute(f"""
CREATE OR REPLACE TEMP TABLE vacancy_required_skills AS
SELECT
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    skill.dovednost.id AS skill_id,
    skill.popis AS skill_description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.pozadovanaDovednost
) AS skills(skill);
""")

# pozadovanaJazykovaZnalost
connection.execute("""
CREATE OR REPLACE TEMP TABLE vacancy_required_language AS
SELECT
    vacancy.snapshot_date,
    vacancy.portalId AS portal_id,

    language.urovenZnalosti.id AS skill_level_id,
    language.jazyk.id AS language_id,
    language.popis AS description
FROM staged_vacancies AS vacancy
CROSS JOIN LATERAL UNNEST(
    vacancy.pozadovanaJazykovaZnalost
) AS languages(language);
""")

# prvniKontaktSeZamestnavatelem
# CONTAINS PII
connection.execute("""
CREATE OR REPLACE TEMP TABLE vacancy_contacts AS
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
""")
