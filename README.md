# Czech Job Market Data Pipeline

Portfolio data-engineering project built with official Czech MPSV job-market
data.

**Current scope is local only.** The working pipeline builds validated
Bronze → Silver → Gold datasets with Python, DuckDB, and Parquet. The AWS
pipeline is not implemented; `infra/` is an unfinished experiment and should
not be deployed.

```bash
cd local
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python build_bronze.py
.venv/bin/python build_silver.py
.venv/bin/python build_gold.py
.venv/bin/python -m pytest
```

See [project status](docs/project-log.md) and
[local recovery notes](docs/local-pipeline-operations.md). Raw source data is
ignored by Git because it can contain personal contact information.
