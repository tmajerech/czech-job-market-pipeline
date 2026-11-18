-- Query to analyze net changes in vacancies
-- for specific date
WITH event_vacancies AS (
    SELECT event.snapshot_date,
        event.previous_snapshot_date,
        event.event_type,
        vacancy.snapshot_date AS attribute_snapshot_date,
        vacancy.occupation_id
    FROM fact_vacancy_event AS event
        INNER JOIN fact_vacancy_snapshot AS vacancy ON vacancy.portal_id = event.portal_id
        AND vacancy.snapshot_date = CASE
            WHEN event.event_type = 'NEW' THEN event.snapshot_date
            WHEN event.event_type = 'REMOVED' THEN event.previous_snapshot_date
        END
    WHERE event.snapshot_date = DATE '2026-11-14'
),
occupation_counts AS (
    SELECT events.snapshot_date,
        events.previous_snapshot_date,
        occupation.occupation_id,
        occupation.occupation_name,
        SUM(
            CASE
                WHEN events.event_type = 'NEW' THEN 1
                ELSE 0
            END
        ) AS new_count,
        SUM(
            CASE
                WHEN events.event_type = 'REMOVED' THEN 1
                ELSE 0
            END
        ) AS removed_count
    FROM event_vacancies AS events
        INNER JOIN dim_occupation AS occupation ON occupation.snapshot_date = events.attribute_snapshot_date
        AND occupation.occupation_id = events.occupation_id
    GROUP BY events.snapshot_date,
        events.previous_snapshot_date,
        occupation.occupation_id,
        occupation.occupation_name
)
SELECT snapshot_date,
    previous_snapshot_date,
    occupation_id,
    occupation_name,
    new_count,
    removed_count,
    new_count - removed_count AS net_change
FROM occupation_counts
ORDER BY net_change DESC,
    occupation_name;
