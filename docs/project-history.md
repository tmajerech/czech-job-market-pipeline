# Project history

Dated records preserved from the project log. They describe the state at the
time, including experiments and files subsequently removed.
Read [project-log.md](project-log.md) for current state and accepted decisions.

## Changes

### 2026-11-23: Update the integration fixture sample path

Updated the Bronze integration fixture to use notebooks/samples/ after the
sample relocation. The pre-commit test run caught the remaining old path.

### 2026-11-23: Separate session context from historical records

Kept current state, accepted decisions, and the next step in project-log.md.
Moved every existing dated entry here without changing its content. Session
startup reads only the short log; consult this history when relevant.

### 2026-11-23: Focus public documentation on the implementation

Removed obsolete discovery reports and condensed source, model, and operations
documentation. Corrected event attribute joins and clarified that excluding
structured contacts does not anonymize published free text.

### 2026-11-23: Remove the discovery data archive

Removed `data/` from the working tree, retaining the notebook sample under
`notebooks/samples/`. Discovery scripts now read and write ignored
`analysis/raw/`; findings remain in docs with archival payload links removed.
The local pipeline's Bronze, Silver, and Gold data paths are unchanged.

### 2026-11-23: Explain analysis folders

Added short READMEs for data, discovery scripts, notebooks, and documentation.
They identify historical inputs, ignored profiling outputs, fixed discovery
dates, and the current pipeline location so readers do not mistake initial
analysis assets or proposals for the working implementation.

### 2026-11-23: Correct the local operations guide

Verified the guide against the builders and publication helpers. Clarified
per-file replacement versus whole-snapshot publication, marker checks and raw
SQL limitations, Bronze retries across date boundaries, and interrupted
historical event refreshes. Daily commands now stop on a failed layer, and the
README link matches the document title. Runtime behavior is unchanged.

### 2026-11-23: Document the implemented data model

Replaced the discovery-era modelling notes with `docs/data-model.md`, an
implementation contract for the current local pipeline. It now lists every
published Silver and Gold table with its grain, documents region and event
derivations, PII boundaries, validation and publication rules, supported
analytics, and explicit V1 limits. The portfolio README links this current
model instead of speculative increment, unemployment, and SCD proposals.

### 2026-11-22: Polish the public portfolio repository

Added GitHub Actions for the local test suite and a compact README architecture
diagram, moved the sanitized exploration notebook to a descriptive path, and
removed the incomplete AWS experiment from the public project. The README now
links durable design and recovery documentation instead of the internal change
log. GitHub description and data-engineering topics identify the project for
recruiters and repository search. The first public CI run passed all 20 tests
on Python 3.14.

### 2026-11-22: Clarify the portfolio scope

Replaced the generated and discovery-heavy README text with a short portfolio
overview, local run commands, and an explicit warning that AWS is not
implemented. Added the same scope statement to the local and infra READMEs so
the repository does not imply a production-ready cloud pipeline.

### 2026-11-22: Remove the incomplete AWS transform

Removed the nonfunctional `TransformSnapshot` Lambda handler, its dependencies,
CDK resource, bucket grant, and Step Functions task. The scheduled AWS workflow
now ends after the working Raw snapshot download instead of failing in an
unfinished Silver transform. Added a synthesis assertion that the stack has one
application Lambda and no `TransformSnapshot` resource.

### 2026-11-21: Document recovery and purge notebook PII history

Added a local operations runbook that defines sequential execution, the
single-writer constraint, marker semantics, and recovery for ordinary and
historical Gold failures. Rewrote all local Git refs to remove historical
versions of `Untitled.ipynb` and its checkpoint, expired reflogs, pruned
unreachable objects, and added back only the sanitized output-free notebook.

### 2026-11-21: Make local snapshot publication failure-safe

Changed Silver and Gold to validate all models before export, stage all output
away from final partitions, and publish with snapshot completion markers.
Gold now refuses incomplete Silver/Gold inputs and refreshes the closest later
event partition after a targeted historical rebuild. Added regression tests for
failed Silver reruns, completion markers, and dependent event recalculation.
Cleared PII-bearing notebook outputs, removed the tracked checkpoint, and
ignored future Jupyter checkpoints. Existing Git history still requires a
separate purge before publication.

### 2026-11-21: Keep failed historical Gold rebuilds isolated

Removed failure propagation that marked the closest later Gold snapshot as
incomplete when publication of a historical snapshot failed. The failed
snapshot still remains incomplete and the build still raises; later event
partitions are refreshed only after the historical publication succeeds.

### 2026-11-20: Test Bronze schema-drift rejection end to end

Added an E2E failure-path test proving that a Bronze snapshot missing the
required `zamestnavatel` column is rejected before any Silver table is exported.

### 2026-11-20: Add a local Bronze-to-Gold end-to-end test

Refactored the Silver and Gold builders into callable snapshot functions with
injectable input, output, and database paths; their existing CLI entrypoints
delegate to those functions. Added a two-snapshot E2E test that generates small
synthetic Bronze JSON files, runs both layers chronologically, and checks the
exported Gold facts and vacancy events without touching local project data.

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
