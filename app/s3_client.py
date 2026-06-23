import logging
from datetime import datetime, timezone

import boto3

logger = logging.getLogger(__name__)

_FILENAME_FORMAT = "%Y-%m-%dT%H-%M"
_FILENAME_EXAMPLE = "YYYY-MM-DDTHH-MM.jsonl"

_MAX_FILE_SIZE_MB = 50
_MAX_FILE_SIZE_BYTES = _MAX_FILE_SIZE_MB * 1024 * 1024


def _parse_key_timestamp(key: str) -> datetime | None:
    """Extract a datetime from a key basename in YYYY-MM-DDTHH-MM.jsonl format. Returns None if the name does not match."""
    stem = key.rsplit("/", 1)[-1].removesuffix(".jsonl")
    try:
        return datetime.strptime(stem, _FILENAME_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def get_latest_key(bucket: str, prefix: str) -> str:
    """Return the S3 key of the most recently dated .jsonl file under prefix.

    Files must follow the naming convention YYYY-MM-DDTHH-MM.jsonl. Files that
    do not match are skipped with a warning. Raises FileNotFoundError if no
    matching file is found.
    """
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    latest_date = datetime(1000, 1, 1, tzinfo=timezone.utc)
    latest_key = None

    for page in pages:
        for obj in page.get("Contents", []):
            if not obj["Key"].endswith(".jsonl"):
                continue
            ts = _parse_key_timestamp(obj["Key"])
            if ts is None:
                logger.warning("Skipping log file with unexpected name format. Expected: %s", _FILENAME_EXAMPLE)
                continue
            if ts > latest_date:
                latest_date = ts
                latest_key = obj["Key"]

    if latest_key is None:
        raise FileNotFoundError(f"No .jsonl files found in bucket '{bucket}' with prefix '{prefix}'")
    return latest_key


def stream_lines(bucket: str, key: str):
    """Stream lines from an S3 object without loading the full file into memory.

    Raises ValueError if the file exceeds _MAX_FILE_SIZE_MB.
    """
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    if response.get("ContentLength", 0) > _MAX_FILE_SIZE_BYTES:
        raise ValueError(f"Log file exceeds the maximum allowed size of {_MAX_FILE_SIZE_MB} MB")
    for line in response["Body"].iter_lines():
        yield line.decode("utf-8")
