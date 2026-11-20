#!/usr/bin/env python3
"""Create a conservative human-review queue for Polymarket/DataSportsAPI name candidates."""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/polymarket_datasportsapi_player_coverage.csv"
OUTPUT = ROOT / "data/processed/polymarket_identity_review_queue.csv"
REVIEW_STATUSES = {"initial_abbreviation_review", "ambiguous_candidate"}

def build_queue(rows: list[dict]) -> list[dict]:
    queue = []
    for row in rows:
        if row.get("database_status") not in REVIEW_STATUSES:
            continue
        try:
            options = json.loads(row.get("candidate_options") or "[]")
        except json.JSONDecodeError:
            options = []
        queue.append({
            "polymarket_player": row.get("polymarket_player", ""),
            "competition_scope": row.get("competition_scope", ""),
            "database_status": row.get("database_status", ""),
            "candidate_count": row.get("candidate_count", str(len(options))),
            "candidate_options_json": json.dumps(options, ensure_ascii=False),
            "selected_source_player_id": "", "decision": "",
            "independent_evidence_source": "", "evidence_reference": "",
            "reviewer_notes": "", "reviewer": "", "reviewed_at_utc": "",
            "review_rule": "Do not approve from name similarity or H2H alone; verify with an independent player profile or official competition record.",
        })
    return sorted(queue, key=lambda r: (r["competition_scope"].casefold(), r["polymarket_player"].casefold()))

def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Reconciliation coverage file missing: {INPUT}")
    with INPUT.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    queue = build_queue(rows)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(queue[0]) if queue else ["polymarket_player","competition_scope","database_status","candidate_count","candidate_options_json","selected_source_player_id","decision","independent_evidence_source","evidence_reference","reviewer_notes","reviewer","reviewed_at_utc","review_rule"]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(queue)
    print(json.dumps({"review_queue_rows":len(queue),"output":str(OUTPUT.relative_to(ROOT)),"auto_approved":0,"identity_merges":0},indent=2))

if __name__ == "__main__":
    main()
