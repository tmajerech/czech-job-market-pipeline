# Vacancy increment behaviour

The increment feed is **not reliable textbook CDC**. It is valuable, but it must be ingested as an append-only observed-event source and reconciled to captured full snapshots. Do not treat each filename as a complete, immutable set of changes that happened on that date.

The probe used nine files spanning 22 September–2 October 2026. Exact outputs are in [`analysis/incremental-profile.json`](../analysis/incremental-profile.json) and [`analysis/increment-semantics.json`](../analysis/increment-semantics.json).

## Sample summary

| File date | Rows | New | Changed | Cancelled | Duplicate `portalId` rows within file |
|---|---:|---:|---:|---:|---:|
| 2026-09-22 | 2,514 | 418 | 1,767 | 329 | 311 |
| 2026-09-23 | 3,203 | 446 | 2,339 | 418 | 342 |
| 2026-09-24 | 2,422 | 321 | 1,702 | 399 | 235 |
| 2026-09-25 | 2,022 | 230 | 1,440 | 352 | 171 |
| 2026-09-26 | 2,022 | 230 | 1,440 | 352 | 171 |
| 2026-09-27 | 5,632 | 1 | 5,600 | 31 | 1 |
| 2026-09-30 | 2,853 | 340 | 1,438 | 1,075 | 258 |
| 2026-10-01 | 1,105 | 340 | 571 | 194 | 56 |
| 2026-10-02 | 1,566 | 314 | 656 | 596 | 50 |
| **Total** | **23,339** | **2,640** | **16,953** | **3,746** | **1,595 same-ID groups** |

There are 15,247 distinct `portalId` values; 5,319 appear in more than one sampled file. Every increment `id` equals `VolneMistoPrirustek/<portalId>`.

## How events are represented

Actual rows have `typZmenyOpenData.id` values:

- `TypyZmenOpenData/novy`
- `TypyZmenOpenData/zmeneny`
- `TypyZmenOpenData/zruseny`

The published schema instead names the property `typyZmenOpenData`. Because it does not prohibit additional properties and the misspelled property is optional, standards validation does not catch the real field as an error. The referenced change-type codelist is empty. An ingestion schema therefore needs an explicit compatibility alias and an internal allowed-value list, while preserving the source spelling.

All 23,339 rows contain every required vacancy field. None is tombstone-shaped. Cancelled records still carry profession and lower salary in all 3,746 cases, employer and location in 3,727 cases, plus the normal nested payload. This is a full-record feed, not partial patches.

Cancellation is not equivalent to `pocetMist=0`: 3,256 of 3,746 cancelled rows have zero places, while 490 retain a positive count. Use the event type, not offered-place count, as the cancellation signal.

## File date is not change date

The official page says a file is restricted to changes made on the date in its filename. That does not match the sample:

| `file_date - date(datumZmeny)` | Rows |
|---|---:|
| Same day | 7,003 |
| One day old | 3,588 |
| 2–7 days old | 1,231 |
| 8–30 days old | 2,874 |
| More than 30 days old | 8,643 |

Median lag is 6 days, p75 is 52 days, p99 is about 248 days, and the maximum is 1,776 days. The 27 September file is especially unlike a daily delta: 5,600 of 5,632 rows are marked changed, its median `datumZmeny` lag is 45 days, and 3,706 rows are more than 30 days old.

This means `datumZmeny` is a business/source timestamp, while file date is an observation/publication date. Neither alone is a complete event ordering key.

## Duplicate and ambiguous events

`portalId` is not unique within a daily file. Common same-file patterns are an identical payload emitted once as `novy` and once as `zmeneny`, with the same `datumZmeny`. Both orders occur:

- `portalId=67295387`, 2026-09-22: `novy` then `zmeneny`, identical payload and timestamp.
- `portalId=67295391`, 2026-09-22: `zmeneny` then `novy`, identical payload and timestamp.

Therefore `(portalId, datumZmeny)` is not an event key, and change-type priority cannot recover a documented source order. Preserve the source row ordinal.

The 25 and 26 September files are more serious: their compressed and uncompressed file hashes differ, but after canonicalizing and sorting records they have the **same exact record multiset** (2,022 rows, 1,851 distinct IDs). Filename-based idempotency alone would ingest the same logical batch twice; raw-file hash alone would also miss the semantic duplication.

Across consecutive observations, 6,514 of 8,092 same-ID event pairs have identical vacancy payloads after excluding the increment-only ID/change-type fields. Re-emission is normal enough that payload hashing is necessary.

## Concrete lifecycles

### New plus repeated unchanged changes

`portalId=67295387` (Database Administrator, salary from 115,000):

1. 2026-09-22 file: `novy`, then `zmeneny`, both with `datumZmeny=2026-09-21T14:30:04.120Z` and identical payload.
2. 2026-09-23 and 2026-09-24: re-emitted as `zmeneny` with the same old timestamp and payload.
3. 2026-10-01: `zmeneny` with a genuinely new timestamp.

The ID is in the 3 October full snapshot. This demonstrates full replacement plus repeated observations, not one event per business change.

### Changed to cancelled

`portalId=322178`:

1. 2026-09-27: `zmeneny`, one offered place, `datumZmeny=2025-01-07T20:58:50Z`.
2. 2026-09-30: `zruseny`, zero places, new change timestamp; changed top-level fields include `datumZmeny`, `pocetMist`, contact, and free text.

This is a usable closure event and contains the full prior business context.

### Created and cancelled within the window

`portalId=67295399`:

1. 2026-09-22 file: first `zmeneny`, then `novy`, identical timestamp and payload.
2. 2026-09-30: `zruseny`, zero places.

The lifecycle is clear at day granularity, but same-day event ordering is internally contradictory.

### Repeated stale record, then cancelled

`portalId=67244907` is re-emitted as `zmeneny` in seven sampled files with an unchanged `datumZmeny=2026-04-02T21:37:40Z`; on 2026-10-02 it is finally `zruseny` with zero places. This is direct evidence that “changed” rows can be old unchanged re-publications.

### Cancellation and reactivation

`portalId=67042903` keeps the same reference number, employer, profession, and CZ-ISCO:

1. 2026-10-01: `zruseny`, `datumVlozeni=2024-04-05`, zero places.
2. 2026-10-02: `zmeneny`, `datumVlozeni=2026-10-01`, one place.

Eleven sampled IDs change `datumVlozeni`; observed cases look like reactivation/reset of the same logical vacancy rather than reassignment to an unrelated employer. `portalId` is stable enough to link the lifecycle, but “cancelled” is not permanently terminal and `datumVlozeni` is not immutable.

### Re-emitted event with mutated payload

`portalId=67296080` is cancelled in both the 23 September and 2 October files with the same `datumZmeny=2026-09-23T12:56:52.970Z`, but its `referencniCislo` changes from `35071517784` to `35105087738`. Three IDs show reference-number variation. Published event payloads are therefore not guaranteed immutable even when the business timestamp and change type are unchanged.

## Reconciliation with the full snapshot

For the last sampled event per ID, checked against the full snapshot retrieved after the 2 October batch:

| Last sampled type | Present in snapshot | Absent |
|---|---:|---:|
| New | 1,259 | 4 |
| Changed | 10,730 | 175 |
| Cancelled | 42 | 3,037 |

The dominant pattern is sensible, but it is not exact. The 42 cancelled-yet-present and 175 changed-yet-absent cases may include reactivation or later processing not represented in the selected files. The current snapshot should be the authoritative current-state source.

## Historical reconstruction verdict

- The archive starts on 31 October 2024, while the current dataset contains older vacancies.
- No dated full snapshot from 31 October 2024 was found. Starting from an empty state and replaying increments cannot recover pre-existing vacancies that did not change after that date.
- There are 189 missing dates in the published 702-day archive range, with no manifest distinguishing zero-change days from absent/failed exports.
- Same-day event ordering is ambiguous, batches can be semantically duplicated, old records are re-emitted, cancelled IDs can reactivate, and identical business timestamps can carry changed payloads.

Consequently, the archive cannot support a defensible exact reconstruction of all historical daily vacancy states before this project starts collecting its own snapshots. It can support observed change history and partial lifecycles.

## Recommended ingestion semantics

1. Store every source object immutably with URL, retrieval time, HTTP metadata, byte hash, uncompressed hash, and canonical-record-multiset hash.
2. Give every raw event a technical key `(source_object_id, row_ordinal)`; retain `portalId`, file date, `datumZmeny`, event type, and payload hash as attributes.
3. Do not deduplicate raw events. In a curated observed-event table, collapse exact canonical duplicates while retaining first/last observation and all source-object references.
4. Treat daily captured full snapshots as authoritative state from collection start. Use increments for timeliness, audit, lifecycle evidence, and anomaly detection—not as the sole state-reconstruction mechanism.
5. Model reactivation explicitly. Do not make `zruseny` an irreversible terminal state and do not use `datumVlozeni` as a stable lifecycle-start attribute without versioning.
6. Alert on missing dates, cross-date semantic duplicates, schema drift, unknown change types, same-file multi-events, and snapshot/event reconciliation failures.
