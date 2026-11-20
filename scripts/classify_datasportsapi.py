#!/usr/bin/env python3
"""Conservatively classify DataSportsAPI fixtures before building player records.

Only confirmed individual singles enter player form/opponent histories.
Doubles pairs, club/team fixtures, and ambiguous fixtures remain separately
classified and are excluded from individual-player statistics.
"""
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/database/table_tennis.sqlite"
SOURCE_KEY = "datasportsapi_table_tennis"

# Explicit provider competition labels for individual-match circuits.
SINGLES_COMPETITIONS = (
    "tt elite series", "setka cup", "tt cup", "czech liga pro",
    "liga pro", "challenger series",
)
DOUBLES_SUFFIXES = (", md", ", wd", ", xd", " men doubles",
                    " women doubles", " mixed doubles")
TEAM_TOKENS = (
    "ttc", " tt", "tt ", "club", "tenis de mesa", "table tennis",
    "grodzisk", "bogoria", "skst", "stk ", "spg ", "ucam", "ctt ",
    "cd ", "ks ", "ask ", "asrtt", "hodonin", "metz tt",
    "saint-quentin",
)
INITIAL_NAME = re.compile(r".+\s+[A-ZА-ЯЁ]\\.$")


def classify(fixture):
    league = ((fixture.get("league") or {}).get("name") or "").strip().lower()
    names = [
        (fixture.get("home") or {}).get("name") or "",
        (fixture.get("away") or {}).get("name") or "",
    ]
    if any(league.endswith(s) for s in DOUBLES_SUFFIXES):
        return "doubles", "high", "competition label identifies doubles"
    if any(any(token in name.lower() for token in TEAM_TOKENS) for name in names):
        return "team", "high", "participant name matches club/team naming rule"
    if any(label in league for label in SINGLES_COMPETITIONS):
        return "singles", "high", "recognized individual table-tennis circuit"
    if league.endswith((", ms", ", ws")):
        return "singles", "high", "WTT men's/women's singles event label"
    if all(INITIAL_NAME.fullmatch(name.strip()) for name in names):
        return "singles", "medium", "both participants use surname-plus-initial format"
    return "unknown", "low", "insufficient evidence to distinguish individual/team/doubles"


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    source = c.execute("SELECT source_id FROM sources WHERE source_key=?",
                       (SOURCE_KEY,)).fetchone()
    if not source:
        raise SystemExit("DataSportsAPI source not found in database")
    source_id = source["source_id"]
    rows = c.execute(
        "SELECT match_pk, raw_row_json FROM matches WHERE source_id=?",
        (source_id,),
    ).fetchall()
    c.execute("""
        CREATE TABLE IF NOT EXISTS datasportsapi_match_classification (
            match_pk INTEGER PRIMARY KEY REFERENCES matches(match_pk),
            match_type TEXT NOT NULL CHECK(match_type IN ('singles','doubles','team','unknown')),
            confidence TEXT NOT NULL CHECK(confidence IN ('high','medium','low')),
            reason TEXT NOT NULL,
            competition TEXT
        )
    """)
    c.execute("DELETE FROM datasportsapi_match_classification WHERE match_pk IN "
              "(SELECT match_pk FROM matches WHERE source_id=?)", (source_id,))
    counts = Counter()
    for row in rows:
        fixture = json.loads(row["raw_row_json"])
        match_type, confidence, reason = classify(fixture)
        competition = ((fixture.get("league") or {}).get("name") or "Unknown")
        c.execute("""
            INSERT INTO datasportsapi_match_classification
            (match_pk,match_type,confidence,reason,competition)
            VALUES(?,?,?,?,?)
        """, (row["match_pk"], match_type, confidence, reason, competition))
        counts[match_type] += 1
    c.commit()
    integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
    c.close()
    print(json.dumps({
        "source": SOURCE_KEY, "classified_matches": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "individual_singles_eligible_for_player_records": counts["singles"],
        "excluded_from_individual_records": counts["doubles"] + counts["team"] + counts["unknown"],
        "database_integrity": integrity,
    }, indent=2))
    if integrity != "ok":
        raise SystemExit("Database integrity check failed")


if __name__ == "__main__":
    main()
