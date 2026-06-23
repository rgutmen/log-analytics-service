from datetime import datetime, timezone
from app.analyzer import analyze_lines

def test_basic_count():
    """Basic test to verify that the analyze_lines function counts errors correctly."""
    lines = [
        '{"service":"api","level":"ERROR","msg":"error"}',
        '{"service":"api","level":"INFO","msg":"ok"}',
    ]                                                                                            
    result = analyze_lines(lines, threshold=5)
    assert result["total"] == 1
    assert result["byService"]["api"] == 1

def test_alert_threshold():
    """Test that the alert is triggered when the total errors meet or exceed the threshold."""
    lines = [
        '{"service":"api","level":"ERROR","msg":"error"}',
        '{"service":"orders","level":"ERROR","msg":"error"}',
        '{"service":"billing","level":"ERROR","msg":"error"}',
    ]
    result = analyze_lines(lines, threshold=3)
    assert result["alert"]

def test_alert_below_threshold():
    """Test that the alert is not triggered when the total errors are below the threshold."""
    lines = [
        '{"service":"api","level":"ERROR","msg":"error"}',
        '{"service":"orders","level":"ERROR","msg":"error"}',
    ]
    result = analyze_lines(lines, threshold=3)
    assert not result["alert"]

def test_empty_input():
    """Test that an empty input returns total=0 and no alert."""
    lines = []
    result = analyze_lines(lines, threshold=3)
    assert result["total"] == 0
    assert not result["alert"]

def test_invalid_json():
    """Test that invalid JSON lines are ignored and do not break the function."""
    lines = [
        '{"service":"api","level":"ERROR","msg":"error"}',
        'invalid json line',
        '{"service":"orders","level":"ERROR","msg":"error"}',
    ]
    result = analyze_lines(lines, threshold=3)
    assert result["total"] == 2
    assert result["byService"]["api"] == 1
    assert result["byService"]["orders"] == 1

def test_since_filters_old_entries():
    lines = [
        '{"service":"api","level":"ERROR","ts":"2025-09-15T13:00:00Z","msg":"old error"}',
        '{"service":"api","level":"ERROR","ts":"2025-09-15T15:00:00Z","msg":"recent error"}',
    ]
    since = datetime(2025, 9, 15, 14, 0, 0, tzinfo=timezone.utc)
    result = analyze_lines(lines, threshold=1, since=since)
    assert result["total"] == 1
    assert result["byService"]["api"] == 1


def test_since_none_includes_all():
    lines = [
        '{"service":"api","level":"ERROR","ts":"2025-09-15T13:00:00Z","msg":"old error"}',
        '{"service":"api","level":"ERROR","ts":"2025-09-15T15:00:00Z","msg":"recent error"}',
    ]
    result = analyze_lines(lines, threshold=5, since=None)
    assert result["total"] == 2


def test_fixture_analysis():
    """Test that the analyze_lines function works correctly with a fixture file."""
    with open('app/tests/fixtures/sample.jsonl', 'r') as f:
        lines = f.readlines()
    result = analyze_lines(lines, threshold=3)
    assert result["total"] == 4
    assert result["byService"]["api"] == 1
    assert result["byService"]["orders"] == 1
    assert result["byService"]["billing"] == 1
    assert result["alert"]
