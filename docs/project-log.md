# Project log

This is the short continuity log for the Jobs project. Read it at the start of
each work session. Update it after meaningful implementation changes or
architectural decisions, including the reason behind them.

Last updated: 2026-10-30

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
  CZ-ISCO occupations, regions, districts, municipalities, and salary types.
  Each table has one class/file with its creation SQL, declared grain, shared
  grain validation, and atomic Parquet export through `BaseTable`. Contacts are
  validated but omitted from public output. Published tables have explicit
  output type contracts.
- The local Gold prototype can load every published Silver table for one
  selected snapshot into consistently named DuckDB temporary tables prefixed
  with `stage_`.

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

### Use one entrypoint per local data layer

The local pipeline exposes `build_bronze.py`, `build_silver.py`, and eventually
`build_gold.py` as the runnable layer entrypoints. Source-specific downloaders
and table-specific transforms remain separate modules called by those scripts.
One Bronze run calculates the snapshot date once and passes it to every source.
The MPSV endpoints expose only their current state, so the Bronze entrypoint
does not accept a historical snapshot date or claim to support backfills.

## Open design decisions

- Keep employer data vacancy-scoped for now. A deduplicated employer dimension
  remains a later Gold decision because IČO can be absent and names are not
  stable keys.

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

## Next step

Define the first Gold vacancy-region bridge with explicit handling for
single-region, multi-region, nationwide, and unresolved locations. Do not deploy
the incomplete Lambda transform yet.

## Changes

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
