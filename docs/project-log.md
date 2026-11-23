# Project log

Read this file at the start of each task. Consult [project history](project-history.md)
only when earlier implementation details or decisions are relevant.

After material changes, update current state and next step here and append a
dated record to project-history.md. Preserve historical entries; keep proposals
separate from accepted decisions.

Last updated: 2026-11-23

## Current state

- Portfolio scope: local Python → DuckDB → Parquet pipeline. No AWS runtime.
- Bronze downloads the full MPSV vacancy snapshot and 22 codelists into one
  Prague-date partition. Atomic file downloads reuse existing non-empty files.
- Silver loads a Bronze snapshot once, checks source columns, casts explicit
  output types, and builds vacancy, child, and reference tables.
- Gold publishes snapshot dimensions, a vacancy fact, a regional bridge,
  and NEW/REMOVED events. Tables and grains: [data model](data-model.md).
- Each table uses the shared BaseTable create/validate/export lifecycle.
  Validation covers grains, declared references, and exported row counts.
- Silver and Gold stage all outputs before replacing final files. Replacement
  is atomic per file, not per snapshot. Publication and recovery details:
  [local pipeline operations](local-pipeline-operations.md).
- Gold rejects Silver snapshots marked _INCOMPLETE and skips marked Gold
  snapshots when choosing event predecessors. Legacy unmarked inputs are allowed.
- GitHub Actions runs the local pytest suite on pushes to main and PRs.
  Tests use synthetic data and temporary directories, not local publication roots.
- The README includes a reproducible aggregate chart generated from the latest
  readable Gold vacancy-event interval; no vacancy-level data is committed.
- Run tests from local/ with `.venv/bin/python -m pytest`.
- Discovery scripts use ignored analysis/raw/. The former data/ archive is
  removed; the output-free notebook uses notebooks/samples/.
- Downloaded data, local Parquet, and DuckDB databases are ignored by Git.
  Historical notebook contact outputs were purged from local Git history.

## Accepted decisions

### Scope and inputs

Use full daily snapshots as the source of truth. Source increments and
unemployment datasets are not processed. NEW and REMOVED are derived from
snapshot comparisons; CHANGED events and SCD2 are not implemented.
Bronze downloads current data only and cannot backfill past source dates.

Keep one entrypoint per layer: build_bronze.py, build_silver.py, build_gold.py.
Silver and Gold accept --snapshot-date; rebuild_all.py processes archived dates
chronologically and requires matching Bronze codelists.

### Model and privacy

Use explicit DuckDB SQL and one class per table with the shared lifecycle.
Keep typed list columns where currently implemented; do not assume every source
array has a normalized bridge. Source identifiers retain their namespaces.

Exclude vacancy_contacts from publication while still creating and validating
it. Published free text is not anonymized and can contain personal data.

Keep nationwide vacancies outside the regional bridge. Flatten district and
region attributes into dim_municipality. Regional totals are not additive.

Identify employers only by non-null IČO. Select the latest updated vacancy's
name, with descending portal_id as the tie-breaker. Keep missing references null.

### Publication and recovery

Run one build process at a time and avoid reading outputs during publication.
Markers do not provide concurrency control; _INCOMPLETE overrides _SUCCESS.
Raw Parquet queries, including example analytics SQL, do not check markers.

A historical Gold build refreshes its events and the next readable fact
snapshot's events; it does not modify that later fact. The two publications are
separate. Recover a failed later refresh by rebuilding that later date directly.

### Portfolio and analytics

Keep the public project focused on the working local implementation.
AWS work requires a complete, tested implementation before reintroduction;
verify live state before describing anything as deployed.

Use SQL over Gold for analytics. Materialize marts only for a demonstrated
consumer or performance need. Keep README short and docs implementation-focused.

## Next step

Keep CI green, documentation aligned with behavior, and refresh the committed
analytical chart after meaningful new Gold intervals.
