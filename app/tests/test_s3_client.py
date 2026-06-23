from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.s3_client import get_latest_key, stream_lines


@patch("app.s3_client.boto3")
def test_get_latest_key_single_file(mock_boto3):
    page = {"Contents": [{"Key": "logs/2025-09-15.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc)}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    key = get_latest_key("my-bucket", "logs/")

    assert key == "logs/2025-09-15.jsonl"


@patch("app.s3_client.boto3")
def test_get_latest_key_picks_most_recent(mock_boto3):
    page = {
        "Contents": [
            {"Key": "logs/2025-09-14.jsonl", "LastModified": datetime(2025, 9, 14, tzinfo=timezone.utc)},
            {"Key": "logs/2025-09-15.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc)},
            {"Key": "logs/2025-09-13.jsonl", "LastModified": datetime(2025, 9, 13, tzinfo=timezone.utc)},
        ]
    }
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    key = get_latest_key("my-bucket", "logs/")

    assert key == "logs/2025-09-15.jsonl"


@patch("app.s3_client.boto3")
def test_get_latest_key_no_files_raises(mock_boto3):
    paginator = MagicMock()
    paginator.paginate.return_value = [{}]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    with pytest.raises(FileNotFoundError):
        get_latest_key("my-bucket", "logs/")


@patch("app.s3_client.boto3")
def test_get_latest_key_empty_prefix(mock_boto3):
    """Empty prefix is a valid value meaning the root of the bucket."""
    page = {"Contents": [{"Key": "app.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc)}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    key = get_latest_key("my-bucket", "")

    assert key == "app.jsonl"


@patch("app.s3_client.boto3")
def test_get_latest_key_ignores_non_jsonl(mock_boto3):
    """Non-.jsonl files under the prefix should be skipped."""
    page = {
        "Contents": [
            {"Key": "logs/archive.gz", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc)},
            {"Key": "logs/data.jsonl", "LastModified": datetime(2025, 9, 14, tzinfo=timezone.utc)},
        ]
    }
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    key = get_latest_key("my-bucket", "logs/")

    assert key == "logs/data.jsonl"


@patch("app.s3_client.boto3")
def test_stream_lines_decodes_bytes(mock_boto3):
    """Lines are yielded as strings, not bytes."""
    mock_boto3.client.return_value.get_object.return_value = {
        "Body": MagicMock(iter_lines=lambda: [b'{"level":"ERROR"}', b'{"level":"INFO"}'])
    }

    lines = list(stream_lines("my-bucket", "logs/app.jsonl"))

    assert lines == ['{"level":"ERROR"}', '{"level":"INFO"}']
