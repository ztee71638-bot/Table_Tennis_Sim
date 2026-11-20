#!/usr/bin/env python3
"""Build source-isolated player/competitor records for DataSportsAPI results."""
import json, sqlite3
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/database/table_tennis.sqlite"
OUT = ROOT / "data/processed/datasportsapi_player_records.json"
SOURCE_KEY = "datasportsapi_table_tennis"


def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    rows = c.execute("""
        SELECT m.match_pk,m.source_match_id,m.match_date,m.competition,
               m.player_a_pk,m.player_b_pk,m.sets_a,m.sets_b,m.winner_player_pk,
               a.source_player_id aid,a.display_name aname,
               b.source_player_id bid,b.display_name bname
        FROM matches m JOIN sources s USING(source_id)
        JOIN players a ON a.player_pk=m.player_a_pk
        JOIN players b ON b.player_pk=m.player_b_pk
        JOIN datasportsapi_match_classification dc ON dc.match_pk=m.match_pk
        WHERE s.source_key=? AND m.winner_player_pk IS NOT NULL
          AND dc.match_type='singles'
        ORDER BY m.match_date,m.match_pk
    """, (SOURCE_KEY,)).fetchall()
    classification_counts = dict(c.execute(
        "SELECT match_type,COUNT(*) FROM datasportsapi_match_classification "
        "GROUP BY match_type"
    ).fetchall())
    states = defaultdict(lambda: {
        "matches": 0, "wins": 0, "losses": 0, "last_date": None,
        "recent": [], "competitions": defaultdict(lambda: {"matches": 0, "wins": 0, "losses": 0}),
        "opponents": defaultdict(lambda: {"matches": 0, "wins": 0, "losses": 0}),
        "elo": 1500.0
    })
    by_id = {}
    for r in rows:
        by_id[r["aid"]] = r["aname"]
        by_id[r["bid"]] = r["bname"]
        a_won = r["winner_player_pk"] == r["player_a_pk"]
        for pid, opp, won in ((r["aid"], r["bid"], a_won), (r["bid"], r["aid"], not a_won)):
            s = states[pid]
            s["matches"] += 1
            s["wins"] += int(won)
            s["losses"] += int(not won)
            s["last_date"] = r["match_date"]
            s["recent"].append({"date": r["match_date"], "opponent_id": opp,
                                "opponent": by_id.get(opp), "result": "W" if won else "L",
                                "sets_for": r["sets_a"] if pid == r["aid"] else r["sets_b"],
                                "sets_against": r["sets_b"] if pid == r["aid"] else r["sets_a"]})
            comp = s["competitions"][r["competition"] or "Unknown"]
            comp["matches"] += 1
            comp["wins"] += int(won)
            comp["losses"] += int(not won)
            record = s["opponents"][opp]
            record["matches"] += 1
            record["wins"] += int(won)
            record["losses"] += int(not won)
        # Same-date outcomes are applied in order only to this descriptive Elo;
        # no pre-match predictions are produced from this file.
        ea, eb = states[r["aid"]]["elo"], states[r["bid"]]["elo"]
        expected = 1 / (1 + 10 ** ((eb - ea) / 400))
        score = 1.0 if a_won else 0.0
        delta = 24 * (score - expected)
        states[r["aid"]]["elo"] += delta
        states[r["bid"]]["elo"] -= delta
    output = {}
    for pid, s in states.items():
        total = s["matches"]
        output[pid] = {
            "display_name": by_id.get(pid), "matches": total, "wins": s["wins"],
            "losses": s["losses"], "win_percentage": round(100 * s["wins"] / total, 2) if total else None,
            "last_match_date": s["last_date"], "recent_form_last_10": s["recent"][-10:],
            "competition_records": dict(s["competitions"]), "opponent_records": dict(s["opponents"]),
            "elo_descriptive_only": round(s["elo"], 2),
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"source": SOURCE_KEY, "individual_singles_matches": len(rows),
                               "classification_counts": classification_counts,
                               "competitors": len(output), "records": output},
                              indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"source": SOURCE_KEY, "individual_singles_matches": len(rows),
                      "classification_counts": classification_counts, "competitors": len(output),
                      "database_integrity": c.execute("PRAGMA integrity_check").fetchone()[0],
                      "output": str(OUT)}, indent=2))
    c.close()


if __name__ == "__main__":
    main()
