from datetime import datetime, timezone

import boto3


def get_latest_key(bucket: str, prefix: str) -> str:
    """Return the S3 key of the most recently modified .jsonl file under prefix.

    Raises FileNotFoundError if no matching file is found.
    """
    s3 = boto3.client("s3")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    latest_date = datetime(1000, 1, 1, tzinfo=timezone.utc)
    latest_key = None

    for page in pages:
        for obj in page.get("Contents", []):
            if obj["Key"].endswith(".jsonl") and obj["LastModified"] > latest_date:
                latest_date = obj["LastModified"]
                latest_key = obj["Key"]

    if latest_key is None:
        raise FileNotFoundError(f"No .jsonl files found in bucket '{bucket}' with prefix '{prefix}'")
    return latest_key


def stream_lines(bucket: str, key: str):
    """Stream lines from an S3 object without loading the full file into memory."""
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    for line in response["Body"].iter_lines():
        yield line.decode("utf-8")
