import logging
import os
from datetime import UTC, datetime
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import boto3
from botocore.exceptions import ClientError

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

SOURCE_URL = "https://data.mpsv.cz/od/soubory/volna-mista/volna-mista.json.gz"
DATA_BUCKET_NAME = os.environ["DATA_BUCKET_NAME"]
SOURCE_TIMEZONE = ZoneInfo("Europe/Prague")

s3 = boto3.client("s3")


def lambda_handler(event, context):
    retrieval_time = datetime.now(SOURCE_TIMEZONE)
    snapshot_date = retrieval_time.date().isoformat()
    object_key = (
        f"raw/mpsv/volna-mista/snapshot_date={snapshot_date}/volna-mista.json.gz"
    )

    if _object_exists(DATA_BUCKET_NAME, object_key):
        LOGGER.info(f"Snapshot already exists at s3://{DATA_BUCKET_NAME}/{object_key}")
        return {
            "status": "already_exists",
            "bucket": DATA_BUCKET_NAME,
            "key": object_key,
            "source_url": SOURCE_URL,
        }

    retrieved_at = retrieval_time.astimezone(UTC).isoformat()
    request = Request(SOURCE_URL)

    LOGGER.info(f"Downloading {SOURCE_URL} to s3://{DATA_BUCKET_NAME}/{object_key}")

    with urlopen(request, timeout=60) as response:
        if response.status != 200:
            raise RuntimeError(
                f"Source returned HTTP {response.status} for {SOURCE_URL}"
            )

        s3.upload_fileobj(
            response,
            DATA_BUCKET_NAME,
            object_key,
            ExtraArgs={
                "ContentType": "application/json",
                "ContentEncoding": "gzip",
                "Metadata": {
                    "source-url": SOURCE_URL,
                    "retrieved-at": retrieved_at,
                },
            },
        )

    uploaded_object = s3.head_object(Bucket=DATA_BUCKET_NAME, Key=object_key)
    size_bytes = uploaded_object["ContentLength"]

    LOGGER.info(
        f"Uploaded {size_bytes} bytes to s3://{DATA_BUCKET_NAME}/{object_key}",
    )

    return {
        "status": "downloaded",
        "bucket": DATA_BUCKET_NAME,
        "key": object_key,
        "size_bytes": size_bytes,
        "source_url": SOURCE_URL,
    }


def _object_exists(bucket: str, key: str) -> bool:
    try:
        s3.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code")
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise
