# Local pipeline operations

Install dependencies using the [README](../README.md). Run from `local/`:

```bash
.venv/bin/python build_bronze.py &&
.venv/bin/python build_silver.py &&
.venv/bin/python build_gold.py
```

The sequence stops on an error. Bronze uses today's Prague date; Silver and
Gold default to the latest input date. Run one build process at a time and
wait for completion before querying outputs. There is no process lock.

## Publication

Silver and Gold validate and export tables to temporary storage before
replacing final Parquet files. Each file replacement is atomic; the whole
snapshot is not.

Status files live under `<layer_root>/_snapshots/snapshot_date=YYYY-MM-DD/`:

- `_INCOMPLETE` blocks a snapshot during publication or event refresh and
  remains after failure. Gold rejects marked Silver inputs and skips marked
  Gold snapshots when choosing event predecessors.
- `_SUCCESS` records a publication and may be left over from an older attempt.
  It never overrides `_INCOMPLETE`.

Success writes `_SUCCESS` and removes `_INCOMPLETE`. Readers allow legacy
snapshots without markers. Example analytics SQL reads Parquet without marker
checks: only query successfully built dates without `_INCOMPLETE`.

## Recovery

Fix the reported error and stop downstream builds until recovery succeeds.
Never remove markers manually.

**Bronze:** rerun on the same Prague day to reuse non-empty downloads and fetch
missing ones. Reuse checks size, not content validity. A retry on another day
creates a new partition; it cannot complete a past snapshot from current data.

**Silver or Gold:** failure before normal publication leaves final files
unchanged. Failure during publication may leave mixed files and `_INCOMPLETE`.
Rerun the failed layer with the affected date:

```bash
.venv/bin/python build_silver.py --snapshot-date YYYY-MM-DD
# After Silver succeeds, rebuild Gold for that date:
.venv/bin/python build_gold.py --snapshot-date YYYY-MM-DD
```

For a Gold-only failure, run only Gold. Silver does not automatically refresh
existing Gold outputs.

**Historical Gold:** publishing date D also triggers an event refresh for the
closest later unmarked fact snapshot. These are separate publications:

- If D fails, rerun D.
- If the later event refresh fails, rerun Gold directly for that later date.
  Rerunning D skips a later date marked incomplete.
- If execution stops between publishing D and marking the later date, its
  events may be stale without a marker. Rebuild the next stored fact date
  explicitly before querying events.

Repair affected dates chronologically. Confirm successful exits and no
`_INCOMPLETE` on affected dates. To rebuild all archived dates, run
`.venv/bin/python rebuild_all.py`; each Bronze date needs its matching codelists.
