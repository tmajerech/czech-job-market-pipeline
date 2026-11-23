# Initial analysis scripts

These scripts supported source discovery and profiling. Daily pipeline
entrypoints live in [`local/`](../local/README).

- `download_samples.sh` downloads the discovery inputs into `analysis/raw/`.
- `profile_data.py` measures those inputs and writes profiling results under
  the Git-ignored `analysis/` directory and the manifest in `analysis/raw/`.
- `profile_increment_semantics.py` examines duplicate and reordered increment
  records and writes results under `analysis/`.

The scripts contain fixed dates and paths from the original investigation.
The downloader's `2026-10-03` retrieval label does not make today's endpoint
responses historical: rerunning it cannot reproduce the original capture.
Review those constants before reusing the scripts for another analysis.
