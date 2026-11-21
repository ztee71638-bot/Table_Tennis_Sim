#!/usr/bin/env python3
"""Prepare static JSON assets for the GitHub Pages match simulator."""
import csv
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "data"
PROCESSED = ROOT / "data" / "processed"


def build_polymarket_payload(events_csv: Path, coverage_csv: Path, raw_json: Path) -> dict:
    raw = json.loads(raw_json.read_text(encoding="utf-8"))
    coverage = {
        row["polymarket_player"]: {
            "database_status": row.get("database_status", "not_checked"),
            "possible_database_name": row.get("possible_database_name", ""),
        }
        for row in csv.DictReader(coverage_csv.open(encoding="utf-8", newline=""))
    }
    events = []
    players = {}
    for row in csv.DictReader(events_csv.open(encoding="utf-8", newline="")):
        if str(row.get("active", "")).casefold() != "true" or str(row.get("closed", "")).casefold() == "true":
            continue
        a, b = row.get("player_a", "").strip(), row.get("player_b", "").strip()
        if not a or not b:
            continue
        events.append({
            "event_id": row.get("event_id", ""),
            "event_slug": row.get("event_slug", ""),
            "title": row.get("event_title", ""),
            "competition": row.get("competition_tags", ""),
            "start_time": row.get("start_time", ""),
            "market_count": int(row.get("market_count") or 0),
            "players": [a, b],
        })
        for name in (a, b):
            info = coverage.get(name, {})
            players[name] = {
                "name": name,
                "database_status": info.get("database_status", "not_checked"),
                "possible_database_name": info.get("possible_database_name", ""),
            }
    events.sort(key=lambda event: (event["start_time"], event["title"].casefold()))
    return {
        "source": raw.get("source", "https://polymarket.us/sports/table-tennis"),
        "retrieved_at_utc": raw.get("retrieved_at_utc", ""),
        "event_count": len(events),
        "player_count": len(players),
        "events": events,
        "players": sorted(players.values(), key=lambda player: player["name"].casefold()),
        "identity_note": "Name matching is a search hint only. Polymarket identities have not been independently verified or merged.",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name in ("current_player_states.json", "prediction_model.json"):
        src = PROCESSED / name
        if not src.exists():
            raise SystemExit(f"Missing required model artifact: {src}")
        shutil.copy2(src, OUT / name)
        print(f"Published {name}: {src.stat().st_size:,} bytes")

    payload = build_polymarket_payload(
        PROCESSED / "polymarket_us_events.csv",
        PROCESSED / "polymarket_us_player_coverage.csv",
        ROOT / "data/raw/polymarket_us_table_tennis_events.json",
    )
    target = OUT / "polymarket_us_active.json"
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Published {payload['event_count']} active Polymarket events and {payload['player_count']} players")


if __name__ == "__main__":
    main()
