# Czech Job Market Data Platform — discovery phase

This workspace contains the data-discovery and profiling phase for a possible Czech labour-market data platform. It deliberately stops before AWS infrastructure, Snowflake models, dbt, APIs, or production pipelines.

The probe used official MPSV / Úřad práce sources retrieved on 3 October 2026. Start with:

- [`docs/data-sources.md`](docs/data-sources.md)
- [`docs/data-profile.md`](docs/data-profile.md)
- [`docs/incremental-behaviour.md`](docs/incremental-behaviour.md)
- [`docs/data-model-notes.md`](docs/data-model-notes.md)
- [`docs/initial-assessment.md`](docs/initial-assessment.md)

## Reproduce the probe

Requirements: Bash, curl, Python 3.12+, and the `jsonschema` Python package for exhaustive schema checks.

```bash
./scripts/download_samples.sh
python3 scripts/profile_data.py
python3 scripts/profile_increment_semantics.py
```

Generated measurements are under `analysis/`; raw checksums, retrieval timestamps, source URLs, and compressed/uncompressed sizes are in `data/raw/manifest.json`.

## Raw-data note

The files are present locally under `data/raw/`, but large/generated payloads are ignored by Git. The full vacancy export includes contact names, phone numbers, and emails, and its official metadata says the distribution contains personal data. Re-download it from the official source rather than publishing a copy in a public repository.
