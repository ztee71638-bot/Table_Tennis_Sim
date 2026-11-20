#!/usr/bin/env python3
"""Health-check the documented public PongIQ events API.

This probe is discovery/health monitoring only. It never imports events into
professional match history. Provider outages are recorded as degraded health
rather than failing the scheduled monitoring job.
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
        request = urllib.request.Request(url, headers={
            "User-Agent": "TableTennisSim-SourceMonitor/1.0",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                status = response.status
                parsed = json.loads(response.read().decode("utf-8"))
            if status != 200:
                raise RuntimeError(f"Unexpected HTTP status: {status}")
            if not isinstance(parsed, dict) or not isinstance(parsed.get("data"), dict):
                raise ValueError("API response did not contain the documented data envelope")
            events = parsed["data"].get("events")
            if not isinstance(events, list):
                raise ValueError("API response data.events is missing or not a list")
            return {"http_status": status, "body": parsed, "events": events}
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
            last_error = str(exc)
            if attempt < attempts:
                delay = 5 * attempt
                print(f"Attempt {attempt}/{attempts} failed: {last_error}; retrying in {delay}s", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"PongIQ endpoint failed after {attempts} attempts: {last_error}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    checked_at = datetime.now(timezone.utc).isoformat()
    try:
        result = fetch_json(URL)
        body, events = result["body"], result["events"]
        snapshot = {
            "source": "PongIQ public API v1",
            "endpoint": URL,
            "checked_at_utc": checked_at,
            "http_status": result["http_status"],
            "meta": body.get("meta", {}),
            "events": events,
        }
        (OUT / "pongiq_events_latest.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8"
        )
        statuses = {}
        for event in events:
            if isinstance(event, dict):
                status = str(event.get("status", "unknown"))
                statuses[status] = statuses.get(status, 0) + 1
        report = {
            "source": "PongIQ public API v1", "endpoint": URL,
            "checked_at_utc": checked_at, "source_status": "available",
            "api_generated_at": body.get("meta", {}).get("generatedAt") if isinstance(body.get("meta"), dict) else None,
            "http_status": result["http_status"], "event_count": len(events),
            "event_status_counts": statuses,
            "imported_into_professional_database": False,
            "reason": "Supplementary/community feed; event provenance, score schema, and reuse terms require validation before import.",
        }
    except Exception as exc:
        report = {
            "source": "PongIQ public API v1", "endpoint": URL,
            "checked_at_utc": checked_at, "source_status": "unavailable_or_invalid",
            "error": str(exc), "imported_into_professional_database": False,
            "reason": "Provider failure is logged for monitoring; no records are imported.",
        }
    path = OUT / "pongiq_source_health.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
