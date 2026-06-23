from datetime import datetime

import click
import json
from flask import Flask, request, jsonify

from app.analyzer import analyze_lines
from app.cloudwatch_client import publish_metrics
from app.s3_client import get_latest_key, stream_lines
from app.sns_client import publish_alert

app = Flask(__name__)


def parse_since(since_str: str | None) -> datetime | None:
    """Parse an ISO 8601 string into a timezone-aware datetime. Returns None if input is None or invalid."""
    if since_str is None:
        return None
    try:
        return datetime.fromisoformat(since_str.replace("Z", "+00:00"))
    except ValueError:
        return None


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


def _run_analysis(bucket: str, prefix: str, threshold: int, since: datetime | None) -> dict:
    """Fetch the latest log file from S3, analyze it, and publish metrics to CloudWatch. Returns the analysis result."""
    latest_key = get_latest_key(bucket, prefix)
    lines = stream_lines(bucket, latest_key)
    result = analyze_lines(lines, threshold, since=since)
    publish_metrics(result["total"], result["alert"])
    return result


@app.route("/analyze")
def analyze_route():
    bucket = request.args.get("bucket")
    prefix = request.args.get("prefix")
    threshold = request.args.get("threshold")
    since_str = request.args.get("since")

    if not bucket or prefix is None or not threshold:
        return jsonify({"error": "Missing required query parameters: bucket, prefix, threshold"}), 400

    try:
        threshold = int(threshold)
    except ValueError:
        return jsonify({"error": "threshold must be an integer"}), 400

    since = parse_since(since_str)

    try:
        result = _run_analysis(bucket, prefix, threshold, since)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/notify")
def notify_route():
    bucket = request.args.get("bucket")
    prefix = request.args.get("prefix")
    threshold = request.args.get("threshold")
    since_str = request.args.get("since")

    if not bucket or prefix is None or not threshold:
        return jsonify({"error": "Missing required query parameters: bucket, prefix, threshold"}), 400

    try:
        threshold = int(threshold)
    except ValueError:
        return jsonify({"error": "threshold must be an integer"}), 400

    since = parse_since(since_str)

    try:
        result = _run_analysis(bucket, prefix, threshold, since)

        # Only publish to SNS when the alert threshold is reached
        if result["alert"]:
            try:
                publish_alert(json.dumps(result))
            except RuntimeError as e:
                return jsonify({"error": str(e)}), 501

        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 422
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@click.group()
def cli():
    pass


@cli.command()
@click.option("--bucket", help="S3 bucket name")
@click.option("--prefix", help="S3 prefix for log files")
@click.option("--file", "file_path", help="Local log file path")
@click.option("--threshold", required=True, type=int, help="Alert threshold")
@click.option("--since", help="Filter entries from this timestamp onward (ISO 8601)")
def analyze(bucket, prefix, file_path, threshold, since):
    if file_path and (bucket or prefix):
        raise click.UsageError("--file is mutually exclusive with --bucket/--prefix")
    if not file_path and not (bucket and prefix is not None):
        raise click.UsageError("Provide either --file or both --bucket and --prefix")

    since_dt = parse_since(since)

    try:
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                result = analyze_lines(f, threshold, since=since_dt)
        else:
            latest_key = get_latest_key(bucket, prefix)
            lines = stream_lines(bucket, latest_key)
            result = analyze_lines(lines, threshold, since=since_dt)
        click.echo(json.dumps(result))
    except FileNotFoundError as e:
        click.echo(json.dumps({"error": str(e)}))
    except Exception as e:
        click.echo(json.dumps({"error": str(e)}))


if __name__ == "__main__":
    cli()
