import duckdb

from pipeline.base_table import BaseTable


class FactVacancySnapshotTable(BaseTable):
    """Fact table capturing vacancy snapshots."""

    name = "fact_vacancy_snapshot"
    grain_columns = ("snapshot_date", "portal_id")

    @classmethod
    def create_sql(cls) -> str:
        return f"""
CREATE OR REPLACE TEMP TABLE {cls.name} AS
WITH vacancy_region_counts AS (
    SELECT
        snapshot_date,
        portal_id,
        COUNT(*) AS region_count
    FROM bridge_vacancy_region
    GROUP BY
        snapshot_date,
        portal_id
)
SELECT
    snapshot_date,
    portal_id,

    -- source identifier
    vacancy_id,

    -- dimensions
    occupation_id,
    salary_type_id,
    shift_pattern_id,
    publish_type_id,
    work_location_type_id,
    work_location_municipality_id,
    contact_office_id,
    employer_ico,

    -- measures
    monthly_salary_from,
    monthly_salary_to,
    weekly_hours,
    number_of_positions,

    -- lifecycle
    created_at,
    updated_at,
    expiration_date,
    employment_start_date,
    employment_end_date,

    -- derived location
    COALESCE(vrc.region_count, 0) AS region_count,
    CASE
        WHEN v.work_location_type_id = 'TypMistaVykonuPrace/celaCR'
            THEN 'nationwide'
        WHEN region_count IS NULL
            THEN 'unresolved'
        WHEN region_count = 1
            THEN 'single_region'
        ELSE 'multi_region'
    END AS location_scope,


    -- analytical flags
    asylum_seeker,
    non_eu_foreign_national,
    blue_card,
    employee_card,
    public_administration,
    agency_agency_consent,
    agency_user_consent
FROM 
    stage_vacancies v
LEFT JOIN 
    vacancy_region_counts vrc
    USING (snapshot_date, portal_id)
"""

    @classmethod
    def validate_custom(cls, connection: duckdb.DuckDBPyConnection) -> None:
        # make sure the number of rows match
        result = connection.execute(f"""
            SELECT
                (SELECT COUNT(*) FROM {cls.name}),
                (SELECT COUNT(*) FROM stage_vacancies)
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not read row counts from {cls.name} and stage_vacancies")
        actual_row_count, expected_row_count = result

        if expected_row_count != actual_row_count:
            raise RuntimeError(f"Row count mismatch: expected {expected_row_count}, got {actual_row_count}")

        # make sure all the occupation ids exist in the dim_occupation table
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_occupation d
            USING (snapshot_date, occupation_id)
            WHERE d.occupation_id IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate occupation ids in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(f"{missing_count} occupation ids in {cls.name} do not exist in dim_occupation")

        # make sure all the salary type ids exist in the dim_salary_type table
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_salary_type d
            USING (snapshot_date, salary_type_id)
            WHERE d.salary_type_id IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate salary type ids in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(f"{missing_count} salary type ids in {cls.name} do not exist in dim_salary_type")

        # make sure all the shift pattern ids exist in the dim_shift_pattern table
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_shift_pattern d
            USING (snapshot_date, shift_pattern_id)
            WHERE d.shift_pattern_id IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate shift pattern ids in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(f"{missing_count} shift pattern ids in {cls.name} do not exist in dim_shift_pattern")

        # make sure all the publish type ids exist in the dim_publish_type table
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_publish_type d
            USING (snapshot_date, publish_type_id)
            WHERE d.publish_type_id IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate publish type ids in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(f"{missing_count} publish type ids in {cls.name} do not exist in dim_publish_type")

        # make sure all non-null work location type ids exist in the dimension
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_work_location_type d
            USING (snapshot_date, work_location_type_id)
            WHERE v.work_location_type_id IS NOT NULL
                AND d.work_location_type_id IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate work location type ids in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(
                f"{missing_count} work location type ids in {cls.name} "
                "do not exist in dim_work_location_type"
            )

        # make sure all non-null municipality ids exist in dim_municipality
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_municipality d
                ON d.snapshot_date = v.snapshot_date
                AND d.municipality_id = v.work_location_municipality_id
            WHERE v.work_location_municipality_id IS NOT NULL
                AND d.municipality_id IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate municipality ids in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(
                f"{missing_count} municipality ids in {cls.name} do not exist in dim_municipality"
            )

        # make sure all contact office ids exist in dim_contact_office
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_contact_office d
            USING (snapshot_date, contact_office_id)
            WHERE d.contact_office_id IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate contact office ids in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(
                f"{missing_count} contact office ids in {cls.name} do not exist in dim_contact_office"
            )

        # make sure all non-null employer IČOs exist in dim_employer
        result = connection.execute(f"""
            SELECT COUNT(*)
            FROM {cls.name} v
            LEFT JOIN dim_employer d
            USING (snapshot_date, employer_ico)
            WHERE v.employer_ico IS NOT NULL
                AND d.employer_ico IS NULL
        """).fetchone()
        if result is None:
            raise RuntimeError(f"Could not validate employer IČOs in {cls.name}")
        missing_count = result[0]
        if missing_count > 0:
            raise RuntimeError(
                f"{missing_count} employer IČOs in {cls.name} do not exist in dim_employer"
            )
