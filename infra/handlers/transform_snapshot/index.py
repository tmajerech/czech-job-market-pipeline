from compression import gzip
import json
import logging
import os
from datetime import UTC, date, datetime
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
import pyarrow
import pyarrow.parquet as parquet

import boto3
from botocore.exceptions import ClientError

from models import RawDatasetKey, RawVacancyKey
from schemas import VACANCY_SCHEMA

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DATA_BUCKET_NAME = os.environ["DATA_BUCKET_NAME"]
SOURCE_TIMEZONE = ZoneInfo("Europe/Prague")

s3 = boto3.client("s3")

# event fail
# {
#   "status": "already_exists",
#   "bucket": "meddea-jobs-data",
#   "key": "raw/mpsv/volna-mista/snapshot_date=2026-10-06/volna-mista.json.gz",
#   "source_url": "https://data.mpsv.cz/od/soubory/volna-mista/volna-mista.json.gz"
# }

# event success
# {
#     "status": "downloaded",
#     "bucket": "meddea-jobs-data",
#     "key": "raw/mpsv/volna-mista/snapshot_date=2026-10-06/volna-mista.json.gz",
#     "size_bytes": 17368295,
#     "source_url": "https://data.mpsv.cz/od/soubory/volna-mista/volna-mista.json.gz",
# }


def lambda_handler(event, context):
    # the event should come naked
    LOGGER.info("Received event: %s", event)
    bucket = event["bucket"]
    key = event["key"]
    temp_raw_path = "/tmp/volna-mista.json.gz"
    temp_vacancy_parquet_path = "/tmp/vacancy.parquet"
    temp_workplaces_parquet_path = "/tmp/workplaces.parquet"
    snapshot_date = datetime.now(SOURCE_TIMEZONE).date()

    s3.download_file(bucket, key, temp_raw_path)

    with gzip.open(temp_raw_path, "rb", encoding="utf-8-sig") as f:
        vacancies = json.load(f)[RawDatasetKey]

    seen_portal_ids: set[int] = set()  # TODO doublecheck it is reliable
    rows: list[dict] = []

    for raw in vacancies:
        portal_id = raw[RawVacancyKey.PORTAL_ID]
        if portal_id in seen_portal_ids:
            raise ValueError(f"Duplicate portal_id found: {portal_id}")
        seen_portal_ids.add(portal_id)
        rows.append(transform_vacancy(raw, snapshot_date))

    table = pyarrow.Table.from_pylist(rows, schema=VACANCY_SCHEMA)
    parquet.write_table(table, temp_vacancy_parquet_path)

    # TODO CHECKS

    s3.upload_file(
        temp_vacancy_parquet_path,
        event["bucket"],
        f"silver/mpsv/vacancies/snapshot_date={snapshot_date}/part-00000.parquet",
    )

    # nacist event
    # zacit zpacovani per radek
    # zkontrolovat validitu dat
    # ulozit transformovana data do S3
    pass


def transform_vacancy(raw: dict, snapshot_date: date) -> dict:
    profession = raw.get(RawVacancyKey.POZADOVANA_PROFESE) or {}
    employer = raw.get(RawVacancyKey.ZAMESTNAVATEL) or {}
    cz_isco = raw.get(RawVacancyKey.PROFESE_CZ_ISCO) or {}

    return {
        "snapshot_date": snapshot_date,
        "portal_id": raw[RawVacancyKey.PORTAL_ID],
        "source_id": raw[RawVacancyKey.ID],
        "reference_number": raw.get(RawVacancyKey.REFERENCNI_CISLO),
        "title": profession.get("cs"),
        "created_at": _parse_timestamp(raw.get(RawVacancyKey.DATUM_VLOZENI)),
        "updated_at": _parse_timestamp(raw.get(RawVacancyKey.DATUM_ZMENY)),
        "positions_count": raw.get(RawVacancyKey.POCET_MIST),
        "weekly_hours": raw.get(RawVacancyKey.POCET_HODIN_TYDNE),
        "salary_from": raw.get(RawVacancyKey.MESICNI_MZDA_OD),
        "salary_to": raw.get(RawVacancyKey.MESICNI_MZDA_DO),
        "employer_ico": employer.get("ico"),
        "employer_name": employer.get("nazev"),
        "cz_isco_id": cz_isco.get("id"),
    }


def _parse_timestamp(value: str | None) -> datetime | None:
    if value is None:
        return None

    return datetime.fromisoformat(value.replace("Z", "+00:00"))
