#!/usr/bin/env python3
"""Probe the documented public PongIQ events API without importing unverified results.

This is a source-health/discovery monitor only. Community events are never merged
into the professional WTT training set by this script.
"""
from __future__ import annotations
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "source_monitor"
URL = "https://www.pongiq.app/api/v1/events"


def fetch_json(url: str, attempts: int = 3) -> dict:
    last_error = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "TableTennisSim-SourceMonitor/1.0",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                body = response.read()
            if status != 200:
                raise RuntimeError(f"Unexpected HTTP status: {status}")
            parsed = json.loads(body.decode("utf-8"))
            if not isinstance(parsed, dict) or not isinstance(parsed.get("data"), dict):
                raise ValueError("API response did not contain the documented data envelope")
            return {"http_status": status, "body": parsed}
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
            last_error = str(exc)
            if attempt < attempts:
                delay = 5 * attempt
                print(f"Attempt {attempt}/{attempts} failed: {last_error}; retrying in {delay}s", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"PongIQ events endpoint failed after {attempts} attempts: {last_error}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    checked_at = datetime.now(timezone.utc).isoformat()
    result = fetch_json(URL)
    body = result["body"]
    data = body["data"]
    events = data.get("events")
    if not isinstance(events, list):
        raise ValueError("Documented data.events field is missing or is not a list")

    # Preserve the complete public response for audit; do not treat it as a match feed.
    snapshot = {
        "source": "PongIQ public API v1",
        "endpoint": URL,
        "checked_at_utc": checked_at,
        "http_status": result["http_status"],
        "meta": body.get("meta", {}),
        "events": events,
    }
    snapshot_path = OUT / "pongiq_events_latest.json"
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    statuses = {}
    for event in events:
        if isinstance(event, dict):
            status = str(event.get("status", "unknown"))
            statuses[status] = statuses.get(status, 0) + 1
    report = {
        "source": "PongIQ public API v1",
        "endpoint": URL,
        "checked_at_utc": checked_at,
        "api_generated_at": body.get("meta", {}).get("generatedAt") if isinstance(body.get("meta"), dict) else None,
        "http_status": result["http_status"],
        "event_count": len(events),
        "event_status_counts": statuses,
        "snapshot_file": str(snapshot_path.relative_to(ROOT)),
        "imported_into_professional_database": False,
        "reason": "Public tournament feed is supplementary/community data; event provenance and match-level fields must be validated before any separate import.",
    }
    report_path = OUT / "pongiq_source_health.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
