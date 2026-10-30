from datetime import date
from pathlib import Path

from pipeline.bronze.download import download_file


SOURCE_URL = "https://data.mpsv.cz/od/soubory/volna-mista/volna-mista.json.gz"


def download_vacancies(bronze_root: Path, snapshot_date: date) -> Path:
    destination = (
        bronze_root
        / "volna-mista"
        / f"snapshot_date={snapshot_date.isoformat()}"
        / "volna-mista.json.gz"
    )
    return download_file(SOURCE_URL, destination)
