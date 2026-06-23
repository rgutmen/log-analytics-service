import logging
from datetime import datetime, timezone
from typing import NamedTuple

import boto3

logger = logging.getLogger(__name__)

_FILENAME_FORMAT = "%Y-%m-%dT%H-%M"
_FILENAME_EXAMPLE = "YYYY-MM-DDTHH-MM.jsonl"

_MAX_FILE_SIZE_MB = 50
_MAX_FILE_SIZE_BYTES = _MAX_FILE_SIZE_MB * 1024 * 1024


class S3SelectionResult(NamedTuple):
    key: str
    oversized_skipped: list[dict]  # [{"key": str, "size_mb": int}]


def _parse_key_timestamp(key: str) -> datetime | None:
    """Extract a datetime from a key basename in YYYY-MM-DDTHH-MM.jsonl format. Returns None if the name does not match."""
    stem = key.rsplit("/", 1)[-1].removesuffix(".jsonl")
    try:
        return datetime.strptime(stem, _FILENAME_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def get_latest_key(bucket: str, prefix: str) -> S3SelectionResult:
    """Return the most recently dated eligible .jsonl file under prefix.

    Files must follow the naming convention YYYY-MM-DDTHH-MM.jsonl. Files that
    do not match the format or exceed _MAX_FILE_SIZE_MB are skipped with a warning.
    Oversized skipped files are returned in S3SelectionResult.oversized_skipped so
    the caller can act on them (e.g. publish an SNS alert).
    Raises FileNotFoundError if no eligible file is found.
    """
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    latest_date = datetime(1000, 1, 1, tzinfo=timezone.utc)
    latest_key = None
    oversized_skipped = []

    for page in pages:
        for obj in page.get("Contents", []):
            if not obj["Key"].endswith(".jsonl"):
                continue
            ts = _parse_key_timestamp(obj["Key"])
            if ts is None:
                logger.warning("Skipping log file with unexpected name format. Expected: %s", _FILENAME_EXAMPLE)
                continue
            if obj.get("Size", 0) > _MAX_FILE_SIZE_BYTES:
                size_mb = obj.get("Size", 0) // (1024 * 1024)
                logger.warning("Skipping log file that exceeds the maximum allowed size of %d MB", _MAX_FILE_SIZE_MB)
                oversized_skipped.append({"key": obj["Key"], "size_mb": size_mb})
                continue
            if ts > latest_date:
                latest_date = ts
                latest_key = obj["Key"]

    if latest_key is None:
        raise FileNotFoundError(f"No .jsonl files found in bucket '{bucket}' with prefix '{prefix}'")
    return S3SelectionResult(key=latest_key, oversized_skipped=oversized_skipped)


def stream_lines(bucket: str, key: str):
    """Stream lines from an S3 object without loading the full file into memory."""
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    for line in response["Body"].iter_lines():
        yield line.decode("utf-8")
