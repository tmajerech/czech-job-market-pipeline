# Project log

This is the short continuity log for the Jobs project. Read it at the start of
each work session. Update it after meaningful implementation changes or
architectural decisions, including the reason behind them.

Last updated: 2026-10-25

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
- The local playground has a dependency-free Bronze downloader that streams the
  daily MPSV vacancy snapshot to a date-partitioned path using an atomic rename.
- The local Silver prototype loads one Bronze snapshot into DuckDB once and
  builds explicit temporary tables for vacancies, workplaces, benefits,
  required skills, required languages, and contacts. It does not export
  Parquet yet.

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

## Open design decisions

- Decide which temporary Silver models are published to Parquet.
- Decide whether `vacancy_contacts` stays local/restricted or is omitted
  entirely from published Silver because it contains PII.
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

Validate the keys and schemas of the local temporary Silver tables, decide
which of them are publishable, and export the selected tables as partitioned
Parquet. Do not deploy the incomplete Lambda transform yet.

## Changes

### 2026-10-21: Add the local Bronze downloader

`local/download_bronze.py` now downloads the unchanged vacancy snapshot into a
daily Bronze partition. It reuses a non-empty local snapshot and writes through
a temporary file so interrupted transfers are not exposed as complete input.

### 2026-10-25: Add the local DuckDB Silver V1 models

`local/build_silver.py` now loads the latest local Bronze snapshot, validates
its top-level columns, and creates explicit temporary models for the initial
Silver table set. Nested 1:N arrays use relationship tables, while 1:1 objects
are flattened. Contact data remains isolated because it contains PII.
