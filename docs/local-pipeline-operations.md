# Local pipeline operations

This runbook describes the failure and recovery contract for the local
Bronze, Silver, and Gold pipeline. The repository does not currently include
an AWS runtime.

## Run one daily snapshot

Run the layers sequentially from `local/`:

```bash
.venv/bin/python build_bronze.py
.venv/bin/python build_silver.py --snapshot-date YYYY-MM-DD
.venv/bin/python build_gold.py --snapshot-date YYYY-MM-DD
```

Stop after the first non-zero exit code. Do not start the next layer after a
failure.

## Single-writer requirement

The local demo has no process lock. Run only one local build process at a time.
In particular, never run two publishers for the same layer and snapshot date,
and never overlap an upstream rebuild with its downstream reader. Concurrent
runs could interleave file replacements, completion markers, and reads.

Add a real lock for `(layer, snapshot_date)` plus dependency-aware orchestration
before scheduling builds, running them in CI, or allowing multiple operators
to use the same local publication root.

## Snapshot markers

Silver and Gold stage and validate every table before changing final files.
Publication then uses these markers:

- `_INCOMPLETE` means publication started but did not finish. In-repository
  readers reject the snapshot.
- `_SUCCESS` means every table in that publication attempt was replaced.
- `_INCOMPLETE` takes precedence if both markers exist after an interruption.
- Snapshots created before markers were introduced remain readable for
  backward compatibility.

Direct Parquet readers can bypass this contract, so operational queries should
not read a snapshot carrying `_INCOMPLETE`.

## Recovery

### Bronze failure

Each download is written through a `.part` file and renamed only when complete.
Bronze does not have a whole-snapshot completion marker, so a failed run can
leave some completed source files and omit later ones. Rerun `build_bronze.py`;
it reuses completed non-empty files and downloads the missing files. Start
Silver only after Bronze exits successfully.

### Silver or Gold failure before publication

Validation or staging failures do not change final files. Fix the input or
code problem and rerun the same layer and snapshot date. A previously
successful snapshot remains readable.

### Silver or Gold failure during publication

The affected snapshot retains `_INCOMPLETE`, and the build exits non-zero.
Rerun the same layer and snapshot date. A successful rerun replaces every
published file, writes `_SUCCESS`, and removes `_INCOMPLETE`.

### Historical Gold rebuild

Rebuilding Gold date `D` also refreshes `fact_vacancy_event` for the closest
later Gold fact snapshot `D_next` after `D` publishes successfully.

- If publication of `D` fails, only `D` is incomplete. Rerun `D`.
- If `D` succeeds but the automatic event refresh fails, `D_next` is
  incomplete. Rerun Gold directly for `D_next`; rerunning only `D` is not the
  recovery command.

For example, if `D_next` is `2026-11-21`:

```bash
.venv/bin/python build_gold.py --snapshot-date 2026-11-21
```
