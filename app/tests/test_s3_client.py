import logging
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.s3_client import get_latest_key, stream_lines


@patch("app.s3_client.boto3")
def test_get_latest_key_single_file(mock_boto3):
    page = {"Contents": [{"Key": "logs/2025-09-15T14-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    result = get_latest_key("my-bucket", "logs/")

    assert result.key == "logs/2025-09-15T14-00.jsonl"
    assert result.oversized_skipped == []


@patch("app.s3_client.boto3")
def test_get_latest_key_picks_most_recent_by_filename(mock_boto3):
    page = {
        "Contents": [
            {"Key": "logs/2025-09-15T13-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024},
            {"Key": "logs/2025-09-15T17-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024},
            {"Key": "logs/2025-09-15T12-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024},
        ]
    }
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    result = get_latest_key("my-bucket", "logs/")

    assert result.key == "logs/2025-09-15T17-00.jsonl"
    assert result.oversized_skipped == []


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
    page = {"Contents": [{"Key": "2025-09-15T14-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    result = get_latest_key("my-bucket", "")

    assert result.key == "2025-09-15T14-00.jsonl"


@patch("app.s3_client.boto3")
def test_get_latest_key_ignores_non_jsonl(mock_boto3):
    """Non-.jsonl files under the prefix should be skipped."""
    page = {
        "Contents": [
            {"Key": "logs/archive.gz", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024},
            {"Key": "logs/2025-09-15T14-00.jsonl", "LastModified": datetime(2025, 9, 14, tzinfo=timezone.utc), "Size": 1024},
        ]
    }
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    result = get_latest_key("my-bucket", "logs/")

    assert result.key == "logs/2025-09-15T14-00.jsonl"


@patch("app.s3_client.boto3")
def test_get_latest_key_skips_file_with_bad_format_and_warns(mock_boto3, caplog):
    """Files that do not match the expected name format are skipped with a warning."""
    page = {
        "Contents": [
            {"Key": "logs/2025-09-15T14-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024},
            {"Key": "logs/unknown-name.jsonl", "LastModified": datetime(2025, 9, 16, tzinfo=timezone.utc), "Size": 1024},
        ]
    }
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    with caplog.at_level(logging.WARNING, logger="app.s3_client"):
        result = get_latest_key("my-bucket", "logs/")

    assert result.key == "logs/2025-09-15T14-00.jsonl"
    assert "YYYY-MM-DDTHH-MM.jsonl" in caplog.text
    assert "unknown-name" not in caplog.text


@patch("app.s3_client.boto3")
def test_get_latest_key_all_bad_format_raises(mock_boto3):
    """If all files fail format parsing, FileNotFoundError is raised."""
    page = {"Contents": [{"Key": "logs/unknown-name.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 100}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    with pytest.raises(FileNotFoundError):
        get_latest_key("my-bucket", "logs/")


@patch("app.s3_client.boto3")
def test_get_latest_key_skips_oversized_file_and_picks_next(mock_boto3):
    """Oversized files are skipped; the next most recent valid file is returned and skipped files are reported."""
    page = {
        "Contents": [
            {"Key": "logs/2025-09-15T17-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 51 * 1024 * 1024},
            {"Key": "logs/2025-09-15T16-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 1024},
        ]
    }
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    result = get_latest_key("my-bucket", "logs/")

    assert result.key == "logs/2025-09-15T16-00.jsonl"
    assert len(result.oversized_skipped) == 1
    assert result.oversized_skipped[0]["key"] == "logs/2025-09-15T17-00.jsonl"
    assert result.oversized_skipped[0]["size_mb"] == 51


@patch("app.s3_client.boto3")
def test_get_latest_key_all_oversized_raises(mock_boto3):
    """If all files exceed the size limit, FileNotFoundError is raised."""
    page = {"Contents": [{"Key": "logs/2025-09-15T17-00.jsonl", "LastModified": datetime(2025, 9, 15, tzinfo=timezone.utc), "Size": 51 * 1024 * 1024}]}
    paginator = MagicMock()
    paginator.paginate.return_value = [page]
    mock_boto3.client.return_value.get_paginator.return_value = paginator

    with pytest.raises(FileNotFoundError):
        get_latest_key("my-bucket", "logs/")


@patch("app.s3_client.boto3")
def test_stream_lines_decodes_bytes(mock_boto3):
    """Lines are yielded as strings, not bytes."""
    mock_boto3.client.return_value.get_object.return_value = {
        "Body": MagicMock(iter_lines=lambda: [b'{"level":"ERROR"}', b'{"level":"INFO"}'])
    }

    lines = list(stream_lines("my-bucket", "logs/app.jsonl"))

    assert lines == ['{"level":"ERROR"}', '{"level":"INFO"}']
