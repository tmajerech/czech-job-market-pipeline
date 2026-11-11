-- Business question:
-- How many vacancies are available for each occupation in each region in the
-- latest snapshot?
--
-- Output grain:
-- One row per snapshot, region, and occupation.
--
-- Caveats:
-- A multi-region vacancy is counted once in every applicable region, so
-- vacancy_count is not additive across regions. Nationwide vacancies are not
-- included because they are deliberately excluded from bridge_vacancy_region.
-- Vacancies whose region cannot be resolved are also absent from the bridge
-- and therefore from this regional analysis.

WITH latest_snapshot AS (
    SELECT MAX(snapshot_date) AS snapshot_date
    FROM fact_vacancy_snapshot
),
vacancies_by_region_and_occupation AS (
    SELECT
        snapshot_date,
        region_id,
        occupation_id,
        COUNT(*) AS vacancy_count
    FROM fact_vacancy_snapshot
    INNER JOIN latest_snapshot
        USING (snapshot_date)
    INNER JOIN bridge_vacancy_region
        USING (snapshot_date, portal_id)
    GROUP BY
        snapshot_date,
        region_id,
        occupation_id
)
SELECT
    snapshot_date,
    region_id,
    region_name,
    occupation_id,
    occupation_code,
    occupation_name,
    vacancy_count
FROM vacancies_by_region_and_occupation
INNER JOIN dim_region
    USING (snapshot_date, region_id)
INNER JOIN dim_occupation
    USING (snapshot_date, occupation_id)
ORDER BY
    region_name,
    vacancy_count DESC,
    occupation_code;
