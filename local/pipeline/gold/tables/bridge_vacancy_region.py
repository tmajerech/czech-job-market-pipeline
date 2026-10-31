import duckdb

from pipeline.base_table import BaseTable


class BridgeVacancyRegionTable(BaseTable):
    """Table linking vacancies to their respective regions."""

    name = "bridge_vacancy_region"
    grain_columns = ("snapshot_date", "portal_id", "region_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
WITH region_eligible_vacancies AS (
    SELECT
        snapshot_date,
        portal_id,
        work_location_municipality_id,
        work_location_district_ids
    FROM stage_vacancies
    WHERE work_location_type_id IS NULL
        OR work_location_type_id <> 'TypMistaVykonuPrace/celaCR'
),
region_links AS (
    -- cover the case when there is a workplace. Join on municipality and district to catch cases when the region is not directly specified for the workplace
    SELECT
        workplace.snapshot_date,
        workplace.portal_id,
        COALESCE(
            workplace.region_id,
            workplace_district.region_id,
            municipality_district.region_id
        ) AS region_id
    FROM stage_vacancy_workplaces AS workplace
    INNER JOIN region_eligible_vacancies AS vacancy
        ON vacancy.snapshot_date = workplace.snapshot_date
        AND vacancy.portal_id = workplace.portal_id
    LEFT JOIN stage_districts AS workplace_district
        ON workplace_district.snapshot_date = workplace.snapshot_date
        AND workplace_district.district_id = workplace.district_id
    LEFT JOIN stage_municipalities AS workplace_municipality
        ON workplace_municipality.snapshot_date = workplace.snapshot_date
        AND workplace_municipality.municipality_id = workplace.municipality_id
    LEFT JOIN stage_districts AS municipality_district
        ON municipality_district.snapshot_date = workplace_municipality.snapshot_date
        AND municipality_district.district_id = workplace_municipality.district_id

    UNION

    -- cover case when the vacancy has a municipality
    SELECT
        vacancy.snapshot_date,
        vacancy.portal_id,
        district.region_id
    FROM region_eligible_vacancies AS vacancy
    INNER JOIN stage_municipalities AS municipality
        ON municipality.snapshot_date = vacancy.snapshot_date
        AND municipality.municipality_id = vacancy.work_location_municipality_id
    INNER JOIN stage_districts AS district
        ON district.snapshot_date = municipality.snapshot_date
        AND district.district_id = municipality.district_id

    UNION

    -- cover case when the vacancy has a district
    SELECT
        vacancy.snapshot_date,
        vacancy.portal_id,
        district.region_id
    FROM region_eligible_vacancies AS vacancy
    CROSS JOIN LATERAL UNNEST(
        vacancy.work_location_district_ids
    ) AS district_ids(district_id)
    INNER JOIN stage_districts AS district
        ON district.snapshot_date = vacancy.snapshot_date
        AND district.district_id = district_ids.district_id
)
SELECT
    CAST(snapshot_date AS DATE) AS snapshot_date,
    CAST(portal_id AS BIGINT) AS portal_id,
    CAST(region_id AS VARCHAR) AS region_id
FROM region_links
WHERE region_id IS NOT NULL;
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        unresolved_vacancies = connection.execute("""
            SELECT
                vacancy_region.snapshot_date,
                vacancy_region.portal_id
            FROM bridge_vacancy_region AS vacancy_region
            LEFT JOIN stage_vacancies AS vacancy
                ON vacancy.snapshot_date = vacancy_region.snapshot_date
                AND vacancy.portal_id = vacancy_region.portal_id
            WHERE vacancy.portal_id IS NULL
            LIMIT 10
        """).fetchall()

        if unresolved_vacancies:
            raise ValueError("Vacancy-region bridge references unknown vacancies: " f"{unresolved_vacancies}")

        unresolved_regions = connection.execute("""
            SELECT
                vacancy_region.snapshot_date,
                vacancy_region.region_id
            FROM bridge_vacancy_region AS vacancy_region
            LEFT JOIN dim_region AS region
                ON region.snapshot_date = vacancy_region.snapshot_date
                AND region.region_id = vacancy_region.region_id
            WHERE region.region_id IS NULL
            LIMIT 10
        """).fetchall()

        if unresolved_regions:
            raise ValueError(f"Vacancy-region bridge references unknown regions: {unresolved_regions}")

        nationwide_vacancies = connection.execute("""
            SELECT
                vacancy_region.snapshot_date,
                vacancy_region.portal_id
            FROM bridge_vacancy_region AS vacancy_region
            INNER JOIN stage_vacancies AS vacancy
                ON vacancy.snapshot_date = vacancy_region.snapshot_date
                AND vacancy.portal_id = vacancy_region.portal_id
            WHERE vacancy.work_location_type_id = 'TypMistaVykonuPrace/celaCR'
            LIMIT 10
        """).fetchall()

        if nationwide_vacancies:
            raise ValueError("Nationwide vacancies must not be expanded into regions: " f"{nationwide_vacancies}")
