#!/usr/bin/env python3
"""Produce a reviewable audit of DataSportsAPI's heuristic match classifications."""
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/database/table_tennis.sqlite"
OUT = ROOT / "data/processed/datasportsapi_classification_audit.json"
SOURCE_KEY = "datasportsapi_table_tennis"

def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = c.execute("""
      SELECT d.match_type,d.confidence,d.reason,d.competition,m.match_date,
             m.raw_row_json
      FROM datasportsapi_match_classification d
      JOIN matches m USING(match_pk)
      JOIN sources s USING(source_id)
      WHERE s.source_key=?
      ORDER BY d.match_type,d.confidence,d.competition,m.match_date
    """, (SOURCE_KEY,)).fetchall()
    grouped = Counter()
    leagues = defaultdict(Counter)
    examples = defaultdict(list)
    for r in rows:
        key = (r["match_type"], r["confidence"], r["reason"])
        grouped[key] += 1
        leagues[r["competition"] or "Unknown"][r["match_type"]] += 1
        if len(examples[key]) < 8:
            raw = json.loads(r["raw_row_json"])
            examples[key].append({
                "date": r["match_date"],
                "competition": r["competition"],
                "home": (raw.get("home") or {}).get("name"),
                "away": (raw.get("away") or {}).get("name"),
                "reason": r["reason"],
            })
    report = {
      "source": SOURCE_KEY,
      "total_classified": len(rows),
      "counts_by_type_confidence_reason": [
        {"match_type": k[0], "confidence": k[1], "reason": k[2], "count": n,
         "examples": examples[k]}
        for k,n in sorted(grouped.items())
      ],
      "competitions": [
        {"competition": name, "counts": dict(counts)}
        for name,counts in sorted(leagues.items())
      ],
      "review_guidance": "Heuristic labels are not ground truth. Review examples and competition formats before treating all singles labels as verified individual matches. Unknown fixtures remain excluded from individual-player records.",
      "database_integrity": c.execute("PRAGMA integrity_check").fetchone()[0]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"total_classified": len(rows),
      "classification_groups": len(grouped),
      "competition_count": len(leagues),
      "database_integrity": report["database_integrity"],
      "output": str(OUT)}, indent=2))
    c.close()
    if report["database_integrity"] != "ok":
        raise SystemExit("SQLite integrity check failed")

if __name__ == "__main__":
    main()
