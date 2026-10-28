import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from bronze import download_codelists, download_vacancies
from config import Config


LOCAL_DIR = Path(__file__).parent
SOURCE_TIMEZONE = ZoneInfo("Europe/Prague")


def build_bronze() -> tuple[Path, ...]:
    snapshot_date = datetime.now(SOURCE_TIMEZONE).date()
    bronze_root = LOCAL_DIR / Config.BRONZE_PATH
    vacancy_path = download_vacancies(bronze_root, snapshot_date)
    codelist_paths = download_codelists(bronze_root, snapshot_date)
    return (vacancy_path, *codelist_paths)


if __name__ == "__main__":
    argparse.ArgumentParser(description="Download the current local MPSV Bronze snapshot").parse_args()
    for downloaded_path in build_bronze():
        print(downloaded_path)
