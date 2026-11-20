#!/usr/bin/env python3
"""Audit the combined table-tennis database and create leakage-safe WTT Elo features."""
import csv, json, sqlite3
from collections import Counter, defaultdict
from itertools import groupby
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/database/table_tennis.sqlite"
OUT = ROOT / "data/processed"
OUT.mkdir(parents=True, exist_ok=True)

def main():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    integrity = c.execute("PRAGMA integrity_check").fetchone()[0]
    fk_errors = c.execute("PRAGMA foreign_key_check").fetchall()
    c.execute("""CREATE TABLE IF NOT EXISTS match_quality_flags (
        flag_pk INTEGER PRIMARY KEY,
        match_pk INTEGER NOT NULL REFERENCES matches(match_pk) ON DELETE CASCADE,
        flag_code TEXT NOT NULL, severity TEXT NOT NULL, evidence_json TEXT NOT NULL,
        UNIQUE(match_pk,flag_code))""")
    c.execute("DELETE FROM match_quality_flags")
    wtt = c.execute("""SELECT m.*,s.source_key,pa.display_name player_a,pb.display_name player_b
        FROM matches m JOIN sources s USING(source_id)
        LEFT JOIN players pa ON pa.player_pk=m.player_a_pk
        LEFT JOIN players pb ON pb.player_pk=m.player_b_pk
        WHERE s.source_key LIKE 'wtt_%' ORDER BY m.match_date,m.match_pk""").fetchall()
    flags, feature_rows, ratings = [], [], {}
    metric_n = correct = 0
    brier = 0.0
    # No within-day leakage: every match on a date uses prior-date ratings.
    for day, day_iter in groupby(wtt, key=lambda x: x["match_date"]):
        day_updates = defaultdict(float)
        for m in day_iter:
            raw = json.loads(m["raw_row_json"] or "{}")
            games = c.execute("SELECT points_a,points_b FROM match_games WHERE match_pk=? ORDER BY game_number",
                              (m["match_pk"],)).fetchall()
            parsed = raw.get("score", "")
            parts = [x.strip() for x in parsed.split(",") if x.strip()]
            valid_tokens = []
            for token in parts:
                bits = token.split("-")
                if len(bits) == 2:
                    try: valid_tokens.append((int(bits[0]), int(bits[1])))
                    except ValueError: pass
            raw_winner = raw.get("winner")
            calculated = "1" if (m["sets_a"] or 0) > (m["sets_b"] or 0) else "2" if (m["sets_b"] or 0) > (m["sets_a"] or 0) else "tie"
            row_flags = []
            if calculated != raw_winner:
                row_flags.append(("WINNER_SETS_DISAGREE", {"raw_winner":raw_winner,"sets_a":m["sets_a"],"sets_b":m["sets_b"],"sets_implied_winner":calculated,"score":parsed}))
            if len(valid_tokens) != len(parts) or len(valid_tokens) != len(games):
                row_flags.append(("SCORE_PARSE_INCOMPLETE", {"raw_score":parsed,"score_tokens":len(parts),"parsed_games":len(valid_tokens),"stored_games":len(games)}))
            if raw_winner not in ("1","2"):
                row_flags.append(("INVALID_WINNER_CODE", {"raw_winner":raw_winner}))
            # Source says best_of=7 for every row although most results end at 3 wins.
            # Do not enforce that inconsistent field; flag only records with <3 set wins.
            if max(m["sets_a"] or 0,m["sets_b"] or 0) < 3:
                row_flags.append(("MATCH_SCORE_NOT_DECISIVE", {"source_best_of":raw.get("best_of"),"sets_a":m["sets_a"],"sets_b":m["sets_b"]}))
            for code, evidence in row_flags:
                item = {"match_pk":m["match_pk"],"source_key":m["source_key"],"source_match_id":m["source_match_id"],
                        "event_date":m["match_date"],"player_a":m["player_a"],"player_b":m["player_b"],
                        "flag_code":code,"severity":"error","evidence":evidence}
                flags.append(item)
                c.execute("INSERT OR IGNORE INTO match_quality_flags(match_pk,flag_code,severity,evidence_json) VALUES(?,?,?,?)",
                          (m["match_pk"],code,"error",json.dumps(evidence,ensure_ascii=False,sort_keys=True)))
            pool = m["source_key"]
            pool_ratings = ratings.setdefault(pool,{})
            ra = pool_ratings.get(m["player_a_pk"],1500.0)
            rb = pool_ratings.get(m["player_b_pk"],1500.0)
            p = 1/(1+10**((rb-ra)/400))
            if not row_flags and raw_winner in ("1","2"):
                y = 1.0 if raw_winner == "1" else 0.0
                metric_n += 1
                correct += int((p >= 0.5) == (y == 1))
                brier += (p-y)**2
                feature_rows.append({"source_key":pool,"event_date":m["match_date"],"source_match_id":m["source_match_id"],
                    "player_a":m["player_a"],"player_b":m["player_b"],"elo_a_pre":round(ra,3),"elo_b_pre":round(rb,3),
                    "elo_diff_pre":round(ra-rb,3),"elo_prob_a_pre":round(p,6),"winner_a":int(y),
                    "sets_a":m["sets_a"],"sets_b":m["sets_b"],"games_recorded":len(games)})
                k = 24.0
                day_updates[(pool,m["player_a_pk"])] += k*(y-p)
                day_updates[(pool,m["player_b_pk"])] += k*((1-y)-(1-p))
        for (pool,player_pk),delta in day_updates.items():
            pool_ratings = ratings.setdefault(pool,{})
            pool_ratings[player_pk] = pool_ratings.get(player_pk,1500.0) + delta
    table_counts = {r["name"]:c.execute(f"SELECT COUNT(*) FROM {r['name']}").fetchone()[0]
                    for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    source_rows = c.execute("""SELECT s.source_key,s.row_count,COUNT(m.match_pk) match_rows,
        COUNT(DISTINCT m.source_match_id) distinct_match_ids
        FROM sources s LEFT JOIN matches m ON m.source_id=s.source_id
        GROUP BY s.source_id ORDER BY s.source_key""").fetchall()
    c.commit()
    with (OUT/"wtt_pre_match_features.csv").open("w",newline="",encoding="utf-8") as f:
        cols = list(feature_rows[0]) if feature_rows else []
        w = csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(feature_rows)
    report = {"sqlite_integrity":integrity,"foreign_key_errors":len(fk_errors),"table_counts":table_counts,
      "sources":[dict(r) for r in source_rows],"wtt_matches_examined":len(wtt),
      "source_metadata_warning":"WTT files label all matches best_of=7, while scores predominantly end at 3 wins. Audit does not enforce a seven-game target; it requires at least 3 game wins for a completed result.",
      "quality_flag_count":len(flags),"flagged_match_count":len(set(x["match_pk"] for x in flags)),
      "flags_by_code":dict(Counter(x["flag_code"] for x in flags)),"quality_flags":flags,
      "baseline":"Chronological source-specific Elo; initial 1500, K=24; all matches on a date use prior-date ratings; flagged matches excluded from metrics and rating updates.",
      "backtest_matches":metric_n,"baseline_accuracy":round(correct/metric_n,6) if metric_n else None,
      "baseline_brier_score":round(brier/metric_n,6) if metric_n else None,
      "limitations":["Not a trained machine-learning model.","No cross-source player identity merging.",
        "WTT data only; Setka and Elo sample are not mixed into this evaluation.",
        "No odds, calibration tuning, confidence claims, or betting recommendations."]}
    (OUT/"database_quality_report.json").write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="quality_flags"},indent=2))
    print(f"Detailed flags: {OUT/'database_quality_report.json'}")
    print(f"Pre-match features: {len(feature_rows)} rows -> {OUT/'wtt_pre_match_features.csv'}")
    c.close()

if __name__ == "__main__":
    main()
