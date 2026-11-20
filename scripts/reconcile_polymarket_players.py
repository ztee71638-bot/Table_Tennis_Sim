#!/usr/bin/env python3
"""Reconcile Polymarket table-tennis listings against source-scoped recent match histories.

This is an evidence report only: it never merges player identities or changes match rows.
"""
from __future__ import annotations

import csv
import json
import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/table_tennis.sqlite"
RAW_EVENTS = ROOT / "data/raw/polymarket_us_table_tennis_events.json"
OUT_DIR = ROOT / "data/processed"
SOURCE_KEY = "datasportsapi_table_tennis"
VS_RE = re.compile(r"^(.+?)\s+(?:vs?\.?|versus)\s+(.+?)\s*$", re.IGNORECASE)


def tokens(value: str) -> list[str]:
    ascii_value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z]+", ascii_value.casefold())


def normalized_tokens_match(query: str, candidate: str) -> str | None:
    """Order-independent full-token match; initials are allowed only as review hints."""
    left, right = tokens(query), tokens(candidate)
    if not left or len(left) != len(right):
        return None
    remaining = list(right)
    used_initial = False
    for token in sorted(left, key=len, reverse=True):
        exact = next((i for i, item in enumerate(remaining) if item == token), None)
        if exact is not None:
            remaining.pop(exact)
            continue
        initial = next(
            (i for i, item in enumerate(remaining)
             if (len(item) == 1 and token.startswith(item))
             or (len(token) == 1 and item.startswith(token))),
            None,
        )
        if initial is None:
            return None
        used_initial = True
        remaining.pop(initial)
    return "initial" if used_initial else "exact"


def event_pair(event: dict) -> tuple[str | None, str | None]:
    title = str(event.get("title") or event.get("name") or "")
    match = VS_RE.match(title)
    if not match:
        markets = event.get("markets") if isinstance(event.get("markets"), list) else []
        for market in markets:
            if isinstance(market, dict):
                match = VS_RE.match(str(market.get("title") or market.get("question") or ""))
                if match:
                    break
    return tuple(part.strip(" ?:-–—") for part in match.groups()) if match else (None, None)


def event_competition(event: dict) -> str:
    tags = event.get("tags") if isinstance(event.get("tags"), list) else []
    labels = []
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        league = tag.get("league") if isinstance(tag.get("league"), dict) else {}
        labels.extend([str(league.get("name") or ""), str(tag.get("label") or "")])
    joined = " ".join(labels).casefold()
    if "setka" in joined:
        return "Setka Cup"
    if "czech liga pro" in joined:
        return "Czech Liga Pro"
    if "tt elite" in joined:
        return "TT Elite Series"
    if "tt cup" in joined:
        return "TT Cup"
    if "challenger" in joined:
        return "Challenger Series"
    if "wtt" in joined:
        return "WTT"
    return ""


def competition_matches(scope: str, competition: str) -> bool:
    if not scope:
        return True
    comp = competition.casefold()
    if scope == "WTT":
        return comp.startswith("wtt ")
    if scope == "Setka Cup":
        return comp == "setka cup"
    return comp == scope.casefold()


def load_source_history(conn: sqlite3.Connection) -> tuple[list[dict], dict]:
    source = conn.execute("SELECT source_id FROM sources WHERE source_key=?", (SOURCE_KEY,)).fetchone()
    if not source:
        return [], {"available": False, "reason": "DataSportsAPI source is not present in this build"}
    source_id = source[0]
    rows = conn.execute(
        """SELECT m.match_date,m.match_time,m.competition,m.source_match_id,
                  m.sets_a,m.sets_b,m.winner_player_pk,
                  m.player_a_pk,m.player_b_pk,
                  a.player_pk AS a_pk,a.source_player_id AS a_id,a.display_name AS a_name,
                  b.player_pk AS b_pk,b.source_player_id AS b_id,b.display_name AS b_name
           FROM matches m
           JOIN players a ON a.player_pk=m.player_a_pk
           JOIN players b ON b.player_pk=m.player_b_pk
           JOIN datasportsapi_match_classification dc ON dc.match_pk=m.match_pk
           WHERE m.source_id=? AND m.winner_player_pk IS NOT NULL
             AND dc.match_type='singles'
           ORDER BY m.match_date,m.match_time,m.match_pk""",
        (source_id,),
    ).fetchall()
    history = [dict(row) for row in rows]
    return history, {"available": True, "matches_loaded": len(history), "source_key": SOURCE_KEY}


def player_candidates(name: str, history: list[dict], scope: str) -> list[dict]:
    player_map: dict[str, dict] = {}
    for match in history:
        for side in ("a", "b"):
            pid = match[f"{side}_id"]
            player_map.setdefault(pid, {
                "source_player_id": pid,
                "display_name": match[f"{side}_name"],
                "matches": [],
            })
            player_map[pid]["matches"].append(match)

    candidates = []
    for player in player_map.values():
        match_type = normalized_tokens_match(name, player["display_name"] or "")
        if not match_type:
            continue
        relevant = [m for m in player["matches"] if competition_matches(scope, m["competition"] or "")]
        candidates.append({
            **player,
            "match_type": match_type,
            "relevant_matches": relevant,
            "scope_match": bool(relevant),
        })
    scoped = [c for c in candidates if c["scope_match"]]
    usable = scoped if scoped else candidates
    exact = [c for c in usable if c["match_type"] == "exact"]
    return exact if exact else usable


def summarize_candidate(candidate: dict | None, ambiguous: bool = False) -> dict:
    if candidate is None:
        return {
            "database_name": "", "source_player_id": "", "name_match_type": "none",
            "matches_in_competition": 0, "matches_all_competitions": 0,
            "wins_in_competition": 0, "losses_in_competition": 0,
            "last_match_date": "", "competition_scope_match": False,
        }
    relevant = candidate["relevant_matches"]
    wins = 0
    for m in relevant:
        is_a = m["a_id"] == candidate["source_player_id"]
        won = m["winner_player_pk"] == (m["a_pk"] if is_a else m["b_pk"])
        wins += int(won)
    losses = len(relevant) - wins
    all_dates = [m["match_date"] for m in candidate["matches"] if m["match_date"]]
    return {
        "database_name": candidate["display_name"],
        "source_player_id": candidate["source_player_id"],
        "name_match_type": "ambiguous" if ambiguous else candidate["match_type"],
        "matches_in_competition": len(relevant),
        "matches_all_competitions": len(candidate["matches"]),
        "wins_in_competition": wins,
        "losses_in_competition": losses,
        "last_match_date": max(all_dates) if all_dates else "",
        "competition_scope_match": candidate["scope_match"],
    }


def reconcile(events: list[dict], history: list[dict], source_info: dict) -> tuple[list[dict], list[dict], dict]:
    player_rows: dict[str, dict] = {}
    matchup_rows = []
    pair_history: dict[frozenset, list[dict]] = defaultdict(list)
    for match in history:
        pair_history[frozenset((match["a_id"], match["b_id"]))].append(match)

    for event in events:
        name_a, name_b = event_pair(event)
        if not name_a or not name_b:
            continue
        scope = event_competition(event)
        cands_a = player_candidates(name_a, history, scope)
        cands_b = player_candidates(name_b, history, scope)
        unique_a = cands_a[0] if len(cands_a) == 1 else None
        unique_b = cands_b[0] if len(cands_b) == 1 else None
        sum_a = summarize_candidate(unique_a, ambiguous=len(cands_a) > 1)
        sum_b = summarize_candidate(unique_b, ambiguous=len(cands_b) > 1)

        if len(cands_a) > 1:
            sum_a = summarize_candidate(cands_a[0], ambiguous=True)
        if len(cands_b) > 1:
            sum_b = summarize_candidate(cands_b[0], ambiguous=True)

        h2h = []
        if unique_a and unique_b:
            h2h = pair_history.get(frozenset((unique_a["source_player_id"], unique_b["source_player_id"])), [])
            if scope:
                h2h = [m for m in h2h if competition_matches(scope, m["competition"] or "")]

        def status(candidates, summary):
            if not source_info.get("available"):
                return "source_not_loaded"
            if len(candidates) > 1:
                return "ambiguous_candidate"
            if not candidates:
                return "not_found"
            if not summary["competition_scope_match"]:
                return "candidate_other_competition_only"
            if summary["name_match_type"] == "exact":
                return "exact_name_match"
            return "initial_abbreviation_review"

        row = {
            "event_id": event.get("id", ""),
            "event_title": event.get("title") or event.get("name") or "",
            "competition_scope": scope,
            "start_time_utc": event.get("startTime", ""),
            "player_a": name_a,
            "player_a_status": status(cands_a, sum_a),
            "player_a_database_name": sum_a["database_name"],
            "player_a_source_id": sum_a["source_player_id"],
            "player_a_matches_in_competition": sum_a["matches_in_competition"],
            "player_a_wins_in_competition": sum_a["wins_in_competition"],
            "player_a_losses_in_competition": sum_a["losses_in_competition"],
            "player_a_last_match_date": sum_a["last_match_date"],
            "player_b": name_b,
            "player_b_status": status(cands_b, sum_b),
            "player_b_database_name": sum_b["database_name"],
            "player_b_source_id": sum_b["source_player_id"],
            "player_b_matches_in_competition": sum_b["matches_in_competition"],
            "player_b_wins_in_competition": sum_b["wins_in_competition"],
            "player_b_losses_in_competition": sum_b["losses_in_competition"],
            "player_b_last_match_date": sum_b["last_match_date"],
            "historical_h2h_matches_in_competition": len(h2h),
            "latest_h2h_date": max((m["match_date"] or "" for m in h2h), default=""),
            "identity_decision": "review only; no automatic cross-source identity merge",
        }
        matchup_rows.append(row)

        for name, stat in ((name_a, sum_a), (name_b, sum_b)):
            player_rows[name] = {
                "polymarket_player": name,
                "competition_scope": scope,
                "database_status": status(cands_a if name == name_a else cands_b, stat),
                **stat,
                "identity_decision": "review only; no automatic cross-source identity merge",
            }

    player_list = sorted(player_rows.values(), key=lambda r: (r["competition_scope"], r["polymarket_player"].casefold()))
    counts = {
        "events_reconciled": len(matchup_rows),
        "distinct_polymarket_players": len(player_list),
        "players_with_exact_name_match": sum(r["database_status"] == "exact_name_match" for r in player_list),
        "players_with_initial_abbreviation_candidate": sum(r["database_status"] == "initial_abbreviation_review" for r in player_list),
        "players_with_ambiguous_candidates": sum(r["database_status"] == "ambiguous_candidate" for r in player_list),
        "players_not_found": sum(r["database_status"] == "not_found" for r in player_list),
        "players_found_only_outside_competition": sum(r["database_status"] == "candidate_other_competition_only" for r in player_list),
        "matchups_with_historical_h2h": sum(r["historical_h2h_matches_in_competition"] > 0 for r in matchup_rows),
    }
    return player_list, matchup_rows, counts


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["no_rows"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        if rows:
            writer.writerows(rows)


def main() -> None:
    if not RAW_EVENTS.exists():
        raise FileNotFoundError(f"Polymarket scan output missing: {RAW_EVENTS}")
    payload = json.loads(RAW_EVENTS.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Simulator database missing: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        history, source_info = load_source_history(conn)
    finally:
        conn.close()

    players, matchups, counts = reconcile(events, history, source_info)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    player_path = OUT_DIR / "polymarket_datasportsapi_player_coverage.csv"
    matchup_path = OUT_DIR / "polymarket_datasportsapi_matchup_evidence.csv"
    write_csv(player_path, players)
    write_csv(matchup_path, matchups)
    report = {
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_info": source_info,
        "counts": counts,
        "outputs": {
            "player_coverage": str(player_path.relative_to(ROOT)),
            "matchup_evidence": str(matchup_path.relative_to(ROOT)),
        },
        "safety": [
            "DataSportsAPI player IDs remain source-scoped.",
            "Name and head-to-head evidence are review aids only; no identities are automatically merged.",
            "Only finished matches with a recorded winner from the DataSportsAPI source are considered.",
            "No simulator match records are changed by this reconciliation report.",
        ],
    }
    report_path = OUT_DIR / "polymarket_datasportsapi_reconciliation_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
