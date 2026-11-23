# Data model

Silver and Gold store daily snapshots as Parquet. Table keys include
`snapshot_date`; source IDs retain their MPSV namespaces. History reflects
captured dates, not SCD2 validity intervals.

## Bronze

Unchanged vacancy JSON.gz and 22 codelists are stored under:

```text
local/s3_doppelganger/bronze/mpsv/
├── volna-mista/snapshot_date=YYYY-MM-DD/
└── codelists/snapshot_date=YYYY-MM-DD/
```

See [sources](data-sources.md) for inputs and download behavior.

## Silver

| Table | Grain | Content |
|---|---|---|
| `vacancies` | `(snapshot_date, portal_id)` | Source vacancy ID, lifecycle dates, salary and position measures, analytical flags, employer and codelist references, location fields, and selected repeated IDs stored as typed lists |
| `vacancy_workplaces` | `(snapshot_date, portal_id, workplace_name)` | Structured workplace address and municipality, district, and region references |
| `vacancy_benefits` | `(snapshot_date, portal_id, benefit_id)` | Benefit identifier and source description |
| `vacancy_required_skills` | `(snapshot_date, portal_id, skill_id)` | Required skill identifier and description |
| `vacancy_required_language` | `(snapshot_date, portal_id, language_id, skill_level_id)` | Required language, required level, and description |

Employment relationships, suitability, and required education remain typed
lists in `vacancies`.

| Table | Grain | Content |
|---|---|---|
| `occupations` | `(snapshot_date, occupation_id)` | CZ-ISCO code, Czech name, hierarchy level, and derived parent occupation ID |
| `regions` | `(snapshot_date, region_id)` | Source code, Czech name, and NUTS 3 code |
| `districts` | `(snapshot_date, district_id)` | Source code, name, LAU code, and region reference |
| `municipalities` | `(snapshot_date, municipality_id)` | Source code, name, and district reference |
| `salary_types` | `(snapshot_date, salary_type_id)` | Salary-type code and name |
| `shift_patterns` | `(snapshot_date, shift_pattern_id)` | Shift-pattern code and name |
| `publish_types` | `(snapshot_date, publish_type_id)` | Publication-mode code and name |
| `work_location_types` | `(snapshot_date, work_location_type_id)` | Work-location-type code and name |
| `contact_offices` | `(snapshot_date, contact_office_id)` | Labour Office code and name |

`vacancy_contacts` is created and validated but not exported. This excludes
structured contact fields; published free text is not anonymized and may still
contain personal data.

## Gold

| Table | Grain | Purpose |
|---|---|---|
| `fact_vacancy_snapshot` | `(snapshot_date, portal_id)` | One row per vacancy present in a daily snapshot, with measures, lifecycle dates, dimension references, analytical flags, `region_count`, and `location_scope` |
| `fact_vacancy_event` | `(snapshot_date, portal_id)` | `NEW` and `REMOVED` events derived by comparing the current fact snapshot with the closest earlier completed Gold snapshot |
| `bridge_vacancy_region` | `(snapshot_date, portal_id, region_id)` | Deduplicated many-to-many relationship between vacancies and explicitly resolvable regions |

Events compare the current fact snapshot with the closest earlier one without
`_INCOMPLETE`. The first snapshot has no event partition. Attribute changes
do not produce events.

To join events to vacancy attributes, use `portal_id` and:

- `snapshot_date` for NEW;
- `previous_snapshot_date` for REMOVED, which has no current vacancy row.

Rebuilding a historical fact refreshes its events and those of the next
readable fact snapshot. Later facts themselves are unchanged.

The regional bridge resolves workplaces, direct municipalities, or district
lists. Nationwide and unresolved vacancies have no bridge rows.
`location_scope` is `nationwide`, `single_region`, `multi_region`, or
`unresolved`; `region_count` counts bridge rows. Regional vacancy counts
are not additive across regions.

| Table | Grain | Purpose |
|---|---|---|
| `dim_occupation` | `(snapshot_date, occupation_id)` | Snapshot-specific CZ-ISCO hierarchy |
| `dim_region` | `(snapshot_date, region_id)` | Region description and NUTS 3 code |
| `dim_municipality` | `(snapshot_date, municipality_id)` | Municipality flattened with its district and region hierarchy |
| `dim_salary_type` | `(snapshot_date, salary_type_id)` | Monthly/hourly salary-type description |
| `dim_shift_pattern` | `(snapshot_date, shift_pattern_id)` | Work-schedule description |
| `dim_publish_type` | `(snapshot_date, publish_type_id)` | Vacancy publication mode |
| `dim_work_location_type` | `(snapshot_date, work_location_type_id)` | Source work-location classification |
| `dim_contact_office` | `(snapshot_date, contact_office_id)` | Labour Office contact-office description |
| `dim_employer` | `(snapshot_date, employer_ico)` | Disclosed employers identified only by non-null IČO |

Join dimensions using their business key **and** `snapshot_date`.
Municipality includes district and region attributes. Employers require a
non-null IČO; the latest updated vacancy supplies the name, with descending
`portal_id` as a tie-breaker. Missing employer references remain null.

## Validation and use

Models validate non-null, unique grains and declared reference relationships.
Silver casts output types explicitly. Exports verify Parquet row counts;
Gold preserves the vacancy row count and validates event semantics.
[Operations](local-pipeline-operations.md) defines publication and recovery.

[Analytics SQL](../local/analytics/queries/) reports demand by region and
occupation, and new/removed vacancy counts. Salary values retain their source
monthly/hourly type; they are not normalized.

Source increments, unemployment data, SCD2, and materialized marts are not
implemented. Prior occupations are not published.
