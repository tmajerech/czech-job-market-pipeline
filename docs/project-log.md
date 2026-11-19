# Project log

This is the short continuity log for the Jobs project. Read it at the start of
each work session. Update it after meaningful implementation changes or
architectural decisions, including the reason behind them.

Last updated: 2026-11-20

## Current state

- The discovery phase measured the official MPSV vacancy snapshot, increment
  feeds, codelists, and unemployment datasets. Detailed evidence is in
  `docs/data-sources.md`, `docs/data-profile.md`,
  `docs/incremental-behaviour.md`, and `docs/data-model-notes.md`.
- The committed CDK stack defines one S3 data bucket, a snapshot download
  Lambda, a Step Functions workflow, and an EventBridge Scheduler trigger at
  05:00 Europe/Prague.
- The download Lambda stores the unchanged source file at
  `raw/mpsv/volna-mista/snapshot_date=YYYY-MM-DD/volna-mista.json.gz`. A repeat
  invocation returns `already_exists` when that object is present.
- Work in progress adds `TransformSnapshot` after `DownloadSnapshot`. It is
  currently uncommitted and incomplete.
- The transform directory contains raw-key enums, a sample vacancy row,
  download-output event samples, `pyarrow`, an initial Silver schema, and a
  first `transform_vacancy` mapper.
- The local playground has one dependency-free Bronze entrypoint that downloads
  the daily MPSV vacancy snapshot and all 22 referenced codelists into the same
  date partition. Every file is streamed through an atomic rename and a repeat
  run reuses existing non-empty files.
- The local Silver prototype loads one Bronze snapshot into DuckDB once and
  builds explicit temporary tables for vacancies, workplaces, benefits,
  required skills, required languages, contacts, and reference tables for
  CZ-ISCO occupations, regions, districts, municipalities, salary types, and
  shift patterns, publication modes, work-location types, and contact offices.
  Each table has one class/file with its creation SQL, declared grain, shared
  grain validation, and atomic Parquet export through `BaseTable`. Personal
  vacancy contacts are validated but omitted from public output. Published
  tables have explicit output type contracts.
- The local Gold prototype can load every published Silver table for one
  selected snapshot into consistently named DuckDB temporary tables prefixed
  with `stage_`. Its first model publishes a deduplicated `bridge_vacancy_region`
  bridge at the grain `(snapshot_date, portal_id, region_id)`. The daily
  `fact_vacancy_snapshot` contains one row per vacancy and snapshot, including
  measures, dimension references, lifecycle dates, analytical flags, and the
  derived `location_scope` and `region_count`. The `dim_occupation` dimension
  publishes the descriptive CZ-ISCO occupation reference used by the fact, and
  the fact requires every occupation reference to resolve against it. The
  `dim_region` dimension publishes region descriptions used by
  `bridge_vacancy_region`, whose region references resolve against it. The
  `dim_salary_type` dimension describes monthly and hourly salary measures,
  and every fact salary-type reference must resolve against it. The
  `dim_shift_pattern` dimension describes the vacancy work schedule, including
  the source's explicit `neurceno` member. Publication mode, work-location
  type, municipality, and contact office also have Gold dimensions. Every
  required fact reference resolves; optional location references are validated
  whenever present. `dim_employer` contains one row per non-null IČO and uses
  the latest updated vacancy to select its descriptive employer name. The first
  documented analytical query reads the completed Gold star to report vacancy
  demand by region and occupation for the latest snapshot.
- Gold derives `fact_vacancy_event` by comparing the current snapshot fact
  with the closest earlier published Gold snapshot. It records `NEW` and
  `REMOVED` vacancies at `(snapshot_date, portal_id)` grain; the first snapshot
  has no event partition because it has no predecessor.
- The local pytest suite covers grain validation, Gold vacancy event behavior,
  occupation references, and location/region bridge validation; run it with
  `cd local && .venv/bin/python -m pytest`.
- Historical local Silver and Gold outputs can be rebuilt with
  `local/rebuild_all.py`; individual layer builders accept `--snapshot-date`
  for targeted reruns.
- Silver and Gold snapshots from `2026-10-28` through `2026-11-15` were
  rebuilt. The `2026-10-21` Bronze vacancy snapshot and its five Silver outputs
  were removed because no matching Bronze codelists were archived.

## Accepted decisions

### Full daily snapshots are the V1 source of truth

The official increment feeds contain duplicate and ambiguous events, so V1
stores and processes the complete daily snapshot. Changes such as `NEW`,
`REMOVED`, and `CHANGED` will later be derived by comparing snapshots.

### Use one S3 bucket with layer prefixes

V1 uses one data bucket rather than separate Raw and Silver buckets:

```text
raw/mpsv/volna-mista/snapshot_date=YYYY-MM-DD/volna-mista.json.gz
silver/mpsv/vacancies/snapshot_date=YYYY-MM-DD/part-00000.parquet
```

The Raw layer preserves the source's Czech naming and payload. Silver uses
standardized English dataset and column names.

### Keep the first transformation simple

The planned V1 transform is `gzip + json.load -> ordinary Python mapping ->
PyArrow Table -> Parquet`. Pandas and streaming JSON parsing are unnecessary
until measured memory usage proves otherwise. The first version writes one
`part-00000.parquet` file per table and snapshot.

### Validate before publishing Silver

Within one full snapshot, `portalId` must be present and unique. A duplicate is
a data-quality failure, not a row to silently discard. Parquet is written to
Lambda's local `/tmp` storage and uploaded to the final Silver key only after
validation succeeds.

### Use explicit PyArrow schemas

Silver Parquet files use explicit schemas so column types stay stable across
daily snapshots, including days where a nullable column contains only nulls.

### Prototype Silver locally with DuckDB

The local V1 uses a thin Python runner with explicit DuckDB SQL. It loads the
source snapshot once into `staged_vacancies`, checks required and unexpected
top-level columns, and builds table-specific temporary models. Repeated source
arrays become relationship tables; 1:1 structures are flattened into their
own table or the parent vacancy row.

`vacancy_contacts` contains personal contact data and must not be included in a
public Silver export without an explicit privacy decision.

### Keep contact PII out of the published Silver V1

`VacancyContactsTable` participates in creation and validation but has
`publish = False`. The local Silver export therefore contains no contact-person
names, email addresses, or phone numbers.

### Use explicit output types in local Silver

Every selected Silver column is cast to its intended output type in the table's
creation SQL. This keeps the Parquet schema stable when nullable source fields
change their observed values between snapshots.

### Share the table lifecycle across Silver and Gold

Silver and Gold table models use the shared `local/pipeline/base_table.py`
lifecycle for creation, grain validation, custom validation, and atomic Parquet
export. Bronze, Silver, and Gold implementations live under the common
`local/pipeline/` namespace, while their runnable build entrypoints remain at
the root of `local/`.

### Keep nationwide vacancies outside regional bridges

The Gold `bridge_vacancy_region` table contains only explicit or inferable regional
relationships. Vacancies whose source location type is `celaCR` remain a
separate nationwide business category rather than being duplicated across all
14 regions, which would make regional totals non-additive.

### Flatten municipality geography in Gold

`dim_municipality` includes its district and region identifiers and descriptive
attributes. This intentionally repeats a small amount of reference data so
business queries can filter a vacancy by municipality, district, or region
without traversing a snowflaked municipality-to-district-to-region chain.

### Identify employers only by IČO

`dim_employer` contains only employers with a non-null IČO. It does not create
name-based or unknown pseudo-identities. When one IČO has multiple observed
names in a snapshot, the latest updated vacancy supplies the descriptive name,
with `portal_id` as a deterministic tie-breaker. Fact rows without IČO retain a
null employer reference; every non-null fact IČO must resolve to the dimension.

### Prove analytical value before materializing marts

Business-facing SQL lives under `local/analytics/queries` and reads the reusable
Gold star. An aggregate should become a materialized mart only after a repeated
consumer, stable business contract, or measured performance need justifies its
additional storage and pipeline maintenance. Portfolio examples may still add
a mart later when it demonstrates that lifecycle honestly.

### Use one entrypoint per local data layer

The local pipeline exposes `build_bronze.py`, `build_silver.py`, and eventually
`build_gold.py` as the runnable layer entrypoints. Source-specific downloaders
and table-specific transforms remain separate modules called by those scripts.
One Bronze run calculates the snapshot date once and passes it to every source.
The MPSV endpoints expose only their current state, so the Bronze entrypoint
does not accept a historical snapshot date or claim to support backfills.

## Known transform issues

`infra/handlers/transform_snapshot/index.py` is a work in progress and should
not be deployed yet. Known issues include:

- gzip/S3 reading mode still needs correction;
- snapshot date should be derived from the input object key rather than wall
  clock time;
- the output should check idempotency and return structured metadata;
- final data-quality checks and tests are missing;
- the Lambda currently has 512 MB memory even though the selected
  `json.load` approach is expected to start around 2 GB;
- `pandas` remains in the transform requirements even though the current
  decision is to use only PyArrow.
- Silver vacancy partitions from `2026-10-21` and `2026-10-28` still expose the
  superseded `profession_cz_isco_id` name. Rebuild them before querying all
  vacancy partitions together; current outputs use `occupation_id`.

## Next step

Add focused tests for other required Gold fact dimension references when their
validation logic changes. Do not deploy the incomplete Lambda transform yet.

## Changes

### 2026-11-20: Test Gold location references

Added offline tests for region-bridge vacancy/region references, nationwide
vacancy exclusion, and detection of a municipality dropped by its region join.
All tests use synthetic DuckDB tables.

### 2026-11-19: Start local unit tests

Added in-memory DuckDB tests for grain rules, `NEW`/`REMOVED` event derivation
and validation, and rejection of an unresolved occupation reference. The
tests use synthetic rows and require no network or archived snapshots.

### 2026-11-18: Add a vacancy-change analysis query

Added `local/analytics/queries/vacancy_changes_by_occupation.sql` to compare
new and removed vacancies by occupation for a selected snapshot interval. For
removed vacancies, occupation attributes are resolved from the previous
snapshot; new vacancies use the current snapshot.

### 2026-11-15: Rebuild historical local outputs

Rebuilt Silver and Gold chronologically for all six Bronze vacancy snapshots
with matching codelists, from `2026-10-28` through `2026-11-15`. Removed the
`2026-10-21` Bronze vacancy file and its five Silver partitions because its
required codelists were unavailable, so that snapshot could not be reproduced
faithfully. The rebuilt vacancy counts match between Silver and Gold for every
processed date.

### 2026-11-15: Add a historical local rebuild command

`local/rebuild_all.py` rebuilds every Silver snapshot with a matching local
Bronze vacancy file, then rebuilds the available Silver-backed Gold snapshots
in chronological order. This order preserves the prior-snapshot dependency of
`fact_vacancy_event`. The layer builders accept an optional `--snapshot-date`
for targeted reprocessing, while their default remains the latest snapshot.

### 2026-11-15: Add the Gold vacancy change fact

The Gold build stages the closest earlier published `fact_vacancy_snapshot`
partition and compares it with the current snapshot. `fact_vacancy_event`
records only `NEW` and `REMOVED` rows, validates event semantics, and exports
under the current snapshot date. The first snapshot skips the event table
because there is no prior state to compare.

### 2026-11-08: Add the first documented Gold analysis

`local/analytics/queries/vacancies_by_region_and_occupation.sql` demonstrates a
business query over the Gold fact, regional bridge, and dimensions. The
initial materialized version was removed because the measured query is cheap
and has no repeated consumer yet; keeping it as SQL exposes the same modeling
and aggregation skills without adding an unjustified pipeline artifact.

### 2026-10-21: Add the local Bronze downloader

The original local Bronze downloader stored the unchanged vacancy snapshot in a
daily partition. It reused a non-empty local snapshot and wrote through a
temporary file so interrupted transfers were not exposed as complete input.

### 2026-10-25: Add the local DuckDB Silver V1 models

`local/build_silver.py` now loads the latest local Bronze snapshot, validates
its top-level columns, and creates explicit temporary models for the initial
Silver table set. Nested 1:N arrays use relationship tables, while 1:1 objects
are flattened. Contact data remains isolated because it contains PII.

### 2026-10-25: Split Silver models into table classes

Each V1 Silver table now lives in its own module and implements the shared
class-based create/validate lifecycle. Grain validation checks required key
values and duplicate semantic rows before a table can be published. The
workplace grain uses `(snapshot_date, portal_id, workplace_name)` because the
measured source has 7,692 missing address-place codes but no missing or
duplicate workplace names within a vacancy snapshot.

### 2026-10-26: Export the validated local Silver snapshot

`BaseTable` now writes publishable tables through a temporary file, re-reads
the Parquet to verify its row count, and atomically replaces the final output.
The first complete run produced vacancies, workplaces, benefits, required
skills, and required languages for snapshot `2026-10-21`; contacts remained
local because `publish = False`.

### 2026-10-26: Define the Silver output types

Every selected column across vacancies, workplaces, benefits, required skills,
required languages, and contacts is now explicitly cast before validation and
export. Source timestamps retain their time component, monetary and hour values
use fixed-precision decimals, source identifiers remain strings, and repeated
identifiers use typed string lists. The full snapshot build passed with 39,640
vacancy rows.

### 2026-10-28: Expand the local Bronze stage

`local/build_bronze.py` now drives the complete local Bronze run for one shared
snapshot date. Vacancy and codelist downloads live in separate modules, while a
shared downloader preserves the existing atomic and idempotent file behavior.
The Bronze snapshot now contains the vacancy source and all 22 MPSV codelists
needed to resolve the identifiers used by Silver.

### 2026-10-29: Add the Silver occupations reference

The local Silver build now expands the CZ-ISCO codelist into one occupation per
row for the same snapshot date as vacancies. The typed `occupations` table keeps
the source ID, code and Czech name, records the hierarchy level, and derives the
parent occupation from the CZ-ISCO code prefix.

### 2026-10-29: Add regions and salary types to Silver

The local Silver build now publishes typed `regions` and `salary_types`
references from the matching Bronze snapshot. Codelist codes remain strings,
including CZ-ISCO occupation codes whose leading zeroes carry hierarchical
meaning. The complete build produced 1,995 occupations, 14 regions, and two
salary types.

### 2026-10-29: Share codelist staging logic

The local Silver builder now stages codelists through one shared function driven
by explicit `(table class, source filename)` definitions. Table-specific output
SQL and validation remain in their individual classes; adding another codelist
does not require duplicating its Bronze loading SQL.

### 2026-10-29: Add districts and municipalities to Silver

The local Silver build now publishes typed `districts` and `municipalities`
references. Validation enforces municipality-to-district and district-to-region
relationships and checks the non-null municipality, district, and region IDs
used by vacancies and workplaces before export.

### 2026-10-29: Standardize vacancy identifier names

The Silver `vacancies` table now exposes the source vacancy identifier as
`vacancy_id` instead of the ambiguous `id`. Its CZ-ISCO reference is named
`occupation_id`, matching the key in the `occupations` reference table.

### 2026-10-30: Add reusable Gold input staging

The Gold table module now loads all published Silver tables for one explicit
snapshot through a reusable function. Each input is exposed as a temporary
`stage_<table>` table. The Gold runner selects the latest available Silver
vacancy snapshot and passes its date to every staged input.

### 2026-10-30: Share the Silver and Gold table base

The generic table lifecycle moved out of the Silver package into
`local/pipeline/base_table.py`. Bronze, Silver, and Gold implementation packages
now share the `pipeline` namespace, while existing Silver models and future
Gold models use the same validation and export behavior without duplication.

### 2026-10-30: Add the Gold vacancy-region bridge

The first Gold model resolves vacancy regions from structured workplaces,
municipalities, and district lists. It stores one deduplicated row per vacancy
and region, validates both sides of the relationship, and publishes one atomic
Parquet file for the selected snapshot. The `2026-10-30` build produced 43,005
relationships for 38,594 vacancies with no null grain values, duplicates, or
nationwide relationships.

### 2026-10-30: Use dimensional-model names in Gold

The vacancy-to-region relationship is published as `bridge_vacancy_region`
rather than `vacancy_regions`. The name makes its many-to-many relationship
role distinct from future `fact_*` observations and descriptive `dim_*`
tables. The next Gold model is the daily `fact_vacancy_snapshot`.

### 2026-10-31: Add the daily vacancy snapshot fact

Gold now publishes `fact_vacancy_snapshot` at the grain
`(snapshot_date, portal_id)`. It retains analytical measures, dimension
references, lifecycle dates, and flags from Silver, then derives region counts
and single-region, multi-region, nationwide, or unresolved location scope from
the validated vacancy-region bridge. The `2026-10-30` build produced 40,043
unique fact rows and matched the staged vacancy row count.

### 2026-10-31: Add the Gold occupation dimension

Gold now publishes `dim_occupation` from the staged Silver CZ-ISCO reference at
the grain `(snapshot_date, occupation_id)`. It retains the code, Czech name,
hierarchy level, and parent occupation ID so facts can resolve their occupation
reference without depending directly on a Silver table. The fact build fails
when an occupation ID is null or missing from the dimension.

### 2026-10-31: Add the Gold region dimension

Gold now publishes `dim_region` from the staged Silver region reference at the
grain `(snapshot_date, region_id)`, retaining its source code, name, and NUTS 3
code. The vacancy-region bridge now validates region references against the
Gold dimension rather than directly against its staged Silver input.

### 2026-10-31: Add the Gold salary-type dimension

Gold now publishes `dim_salary_type` from the staged Silver salary-type
reference at the grain `(snapshot_date, salary_type_id)`. The fact build
requires every salary-type reference to resolve to the dimension.

### 2026-10-31: Add the shift-pattern reference and dimension

Silver now publishes the ten-member `shift_patterns` reference from the Bronze
`smennosti` codelist. Gold publishes it as `dim_shift_pattern` at the grain
`(snapshot_date, shift_pattern_id)`, and the fact build requires every shift
pattern reference to resolve. The source's `neurceno` member remains a real
descriptive value rather than being converted to SQL `NULL`.

### 2026-10-31: Complete the codelist-backed fact dimensions

Silver now publishes publication modes, work-location types, and contact
offices. Gold publishes these as `dim_publish_type`,
`dim_work_location_type`, and `dim_contact_office`. Gold also publishes a
flattened `dim_municipality` with district and region context. All current fact
references resolve. The 12 missing work-location types and optional municipality
references remain SQL `NULL`, while explicit source values such as `neurceno`
remain ordinary dimension members.

### 2026-11-01: Add the Gold employer dimension

Gold now publishes `dim_employer` at the grain
`(snapshot_date, employer_ico)`, selecting the employer name from the latest
updated vacancy for each IČO. The dimension intentionally excludes vacancies
without IČO instead of deriving identities from names, and the fact validates
every non-null employer reference against it. The `2026-10-30` snapshot
contains 18,161 dimension rows.
