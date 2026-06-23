import json
from datetime import datetime


def analyze_lines(lines, threshold: int, since: datetime | None = None) -> dict:
    """Parse JSONL lines, count ERROR entries per service, and return a summary.

    Skips malformed JSON, entries without a timestamp when since is set,
    and entries whose ts predates since.
    """
    by_service = {}
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if since is not None:
            ts_raw = entry.get("ts")
            if ts_raw is None:
                continue
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except ValueError:
                continue
            if ts < since:
                continue

        if entry.get("level", "").lower() == "error":
            service = entry.get("service", "unknown").lower()
            by_service[service] = by_service.get(service, 0) + 1

    total = sum(by_service.values())
    return {"total": total, "byService": by_service, "alert": total >= threshold}
