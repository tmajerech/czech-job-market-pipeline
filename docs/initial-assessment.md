# Initial assessment

## Verdict

**Continue the project, but change its central claim.** This is a good data-engineering portfolio dataset because it has real nested data, reference integrity, imperfect publisher schemas, mutable snapshots, event-like files, privacy considerations, and a second fact domain at a different grain. It is not a big-data project, and the increment feed should not be advertised as clean CDC or as sufficient for exact retrospective reconstruction.

The strongest portfolio story is:

> Build an observable, idempotent snapshot-and-change ingestion platform that preserves source evidence, reconciles unreliable increment signals to authoritative snapshots, and produces geography/profession labour-market marts.

That is more credible than claiming to reconstruct all Czech vacancy history from the published increment archive.

## Assessment against the goals

| Goal | Assessment |
|---|---|
| Reliable incremental ingestion | **Qualified yes.** Files can be discovered and stored idempotently, but logical deduplication and reconciliation are required. Filename, byte hash, `portalId`, and `datumZmeny` are each insufficient alone |
| Historical reconstruction | **Prospective yes; retrospective incomplete.** Daily full snapshots collected by the project can establish authoritative history. The existing increment archive lacks an initial baseline, has 189 missing dates, duplicates batches, and re-emits stale rows |
| Dimensional modelling | **Yes.** Date, geography, CZ-ISCO, employer, education, salary type, shift, and multiple bridge dimensions are real—not invented complexity |
| Meaningful facts | **Yes.** Vacancy state/places, observed vacancy events, municipality-month-sex unemployment, and legacy geography-month unemployment are distinct facts |
| Multiple related entities | **Yes.** Employers, workplace/address variants, professions, codelists, languages, skills, benefits, education, and contact office are observed |
| Vacancy ↔ unemployment analysis | **Yes at aggregate geography/time grain.** All 2,587 observed vacancy municipality codes match the current unemployment fact. Direct row joins and pre-collection time-series joins are not valid |
| Useful marts | **Yes.** Current supply by geography/profession, openings/closures with quality flags, salary availability/distribution, month-end vacancy-to-job-seeker ratios, and long-run legacy trends |
| Real data-engineering complexity | **Yes.** Source discovery, immutable raw capture, schema compatibility, nested normalization, reference validation, idempotency, backfills, state reconciliation, privacy, and observability are all justified |
| Local/cloud manageability | **Yes.** Current volumes are small: 39,217 vacancies and 250,360 selected unemployment rows. This needs disciplined batch engineering, not a distributed streaming platform |

## Important limitations

- The full vacancy URL is mutable and old snapshots are not archived.
- Published increments currently cover 2024-10-31 onward, not the full business-date range of current records.
- 513 increment dates exist across 702 calendar days; 189 dates are absent with no zero-change manifest.
- 25 and 26 September 2026 contain the exact same canonical record multiset under different filenames/bytes.
- A daily file can contain multiple rows for one `portalId`, including identical `new`/`changed` pairs in either order.
- 8,643 of 23,339 sampled increment rows have `datumZmeny` more than 30 days older than the file date.
- Cancelled IDs can reactivate, and `datumVlozeni` can reset.
- The increment schema misspells the actual change field; its change-type codelist is empty.
- The full snapshot has 38 schema-invalid records and clear date/salary outliers.
- Current unemployment begins only in January 2025. The legacy series is longer but lacks geographic codes.
- The full vacancy export contains personal contact data; raw redistribution in a public Git repository is inappropriate.

These are not reasons to abandon the project. They are the substance of a credible reliability/governance portfolio project.

## What the data technically requires

- Immutable object storage with retrieval metadata and content hashes.
- Scheduled batch ingestion (daily vacancy, monthly unemployment); no streaming bus.
- Versioned capture of the mutable full snapshot.
- Streaming or bounded-memory JSON parsing and Parquet output.
- An internal compatibility schema plus quarantine/exception handling for publisher-schema violations.
- Reference-data validation and archived codelist versions.
- Snapshot/event reconciliation and data-quality metrics.
- Aggregate modelling at explicit grains, especially municipality × date.
- Privacy-aware handling of raw contact data.

It does **not** technically require Kafka/Kinesis, Spark clusters, EMR, an always-running database, or Snowflake. DuckDB locally and S3 + Athena in AWS would comfortably handle the measured data volume.

## What to add intentionally for learning/portfolio value

Snowflake is reasonable as an explicit learning objective, provided the project says so plainly. Its justified portfolio uses are:

- loading curated Parquet from an external S3 stage;
- demonstrating incremental batch `COPY`, deduplication, and replay-safe loads;
- implementing dimensions, bridge tables, observed-history models, and gold marts;
- showing resource monitors, auto-suspend, query-cost awareness, and separation of storage/compute;
- comparing Snowflake results/costs with the simpler Athena/DuckDB baseline.

At this scale Snowflake is not a technical necessity. It must stay out of a future public request path and should run only in short scheduled batches on the smallest practical warehouse.

## Recommended high-level architecture

```text
MPSV / Úřad práce HTTPS
        |
        v
EventBridge schedule -> Step Functions
        |
        +--> lightweight index/download task
        |    (Lambda if runtime fits; otherwise an on-demand Fargate/Batch task)
        v
S3 RAW / Bronze, versioned and immutable
  dataset/source_date/retrieved_at/content_hash
        |
        v
schema + quality + reconciliation job (on demand, no service)
        |
        v
S3 Silver Parquet + Glue Data Catalog
        |                         |
        |                         +--> Athena / DuckDB validation baseline
        v
Snowflake external stage -> short batch load
        |
        v
dimensions, bridges, observed vacancy versions, analytical facts/marts
        |
        v
precomputed small public extracts to S3
        |
        +--> CloudFront static files, or API Gateway + Lambda over a cheap serving store
             (never Snowflake in the synchronous request path)
```

The exact transformation runtime should be chosen after benchmarking the real daily job. The 185.6 MB uncompressed snapshot is small enough that Lambda may work with streaming, but an ephemeral container task may be operationally simpler for Parquet libraries. Either is preferable to an always-running ECS service.

## Ingestion and quality policy implied by the probe

- Capture the full vacancy snapshot every day; make it the state authority.
- Discover and archive increment files, but retain row ordinal and treat them as observations.
- Use byte, uncompressed, and canonical-record-multiset hashes. Alert on a new filename with an already-seen semantic batch.
- Make raw ingestion replay-safe through deterministic S3 keys and a source-object manifest.
- Quarantine unknown schemas/types; admit the known `kdeSeHlasit=null` and telephone-length cases only through documented compatibility rules.
- Track at least: source freshness, missing dates, row counts by event type, duplicate IDs within a file, timestamp-lag distribution, snapshot/event reconciliation, unresolved codelist IDs, schema failures, null-rate shifts, salary outliers, and Snowflake load/query cost.
- For a backfill, replay immutable raw objects into a new processing run/version; never overwrite the original raw files.

## Cost outlook

Storage and AWS batch processing should be cheap. A daily copy of the observed 17.4 MB compressed vacancy snapshot is roughly 6.3 GB/year before increments and codelists. Even with Parquet versions and logs, this is modest S3 usage. The 147 MB unemployment cumulative JSON changes monthly.

Snowflake compute will dominate cost if left running. Use batch loads, auto-suspend in about a minute, resource monitors, transient staging tables where appropriate, and explicit teardown of learning environments. Avoid NAT Gateway, EC2, RDS, Redshift, always-running ECS services, and continuously running orchestration.

## Recommended next step

Before production architecture work, run a **4–6 week prospective capture** of daily full snapshots and all published increment files. The purpose is to measure:

- whether missing increment dates correlate with zero state changes;
- how often cancelled IDs reactivate;
- whether a deterministic reconciliation rule reproduces the next full snapshot;
- actual daily schema drift and codelist change frequency;
- Parquet transform runtime/cost on Lambda versus an ephemeral container;
- month-end alignment with the unemployment release.

After that evidence exists, freeze the bronze/silver contracts and only then implement the AWS/Snowflake platform. This phase stops here; no production infrastructure or warehouse model has been built.
