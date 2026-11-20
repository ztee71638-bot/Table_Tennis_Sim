#!/usr/bin/env python3
"""Read-only Polymarket US table-tennis discovery and database coverage audit."""
from __future__ import annotations

import csv
import difflib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/database/table_tennis.sqlite"
RAW_DIR = ROOT / "data/raw"
OUT_DIR = ROOT / "data/processed"
SOURCE_URL = "https://gateway.polymarket.us"
SEARCH_TERMS = (
    "table tennis", "ping pong", "WTT", "Setka Cup",
    "TT Elite", "Czech Liga Pro", "TT Cup",
)
VS_RE = re.compile(r"^(.+?)\s+(?:vs?\.?|versus)\s+(.+?)\s*$", re.IGNORECASE)


def name_tokens(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def norm_name(value: str) -> str:
    return " ".join(name_tokens(value))


def is_table_tennis_event(event: dict) -> bool:
    """Require Polymarket's explicit Table Tennis sport/category tag."""
    tags = event.get("tags") if isinstance(event.get("tags"), list) else []
    for tag in tags:
        if not isinstance(tag, dict):
            continue
        sport = tag.get("sport") if isinstance(tag.get("sport"), dict) else {}
        if (
            str(tag.get("slug", "")).casefold() == "table-tennis"
            or str(tag.get("label", "")).casefold() == "table tennis"
            or str(sport.get("slug", "")).casefold() == "table-tennis"
            or str(sport.get("name", "")).casefold() == "table tennis"
        ):
            return True
    return False


def extract_player_pair(title: str | None) -> tuple[str | None, str | None]:
    if not title:
        return None, None
    cleaned = re.sub(r"^(who will win|winner:?)\s*", "", str(title).strip(), flags=re.I)
    match = VS_RE.match(cleaned)
    if not match:
        return None, None
    a, b = (part.strip(" ?:-–—") for part in match.groups())
    if not a or not b or len(a) > 90 or len(b) > 90:
        return None, None
    return a, b


def as_list(response: Any, key: str) -> list[dict]:
    if isinstance(response, dict):
        value = response.get(key, [])
        return value if isinstance(value, list) else []
    return []


def discover_events() -> tuple[list[dict], dict]:
    """Search several phrases, then filter to active, tagged table-tennis events."""
    from polymarket_us import PolymarketUS

    client = PolymarketUS()
    candidates: dict[str, dict] = {}
    try:
        for term in SEARCH_TERMS:
            response = client.search.query({"query": term, "limit": 100, "status": "active"})
            for event in as_list(response, "events"):
                if not isinstance(event, dict):
                    continue
                key = str(event.get("id") or event.get("slug") or json.dumps(event, sort_keys=True))
                if key not in candidates:
                    candidates[key] = dict(event)
                    candidates[key]["_matched_search_terms"] = [term]
                else:
                    current = candidates[key]
                    current["_matched_search_terms"] = sorted(
                        set(current.get("_matched_search_terms", [])) | {term}
                    )
                    if len(json.dumps(event, default=str)) > len(json.dumps(current, default=str)):
                        merged_terms = current["_matched_search_terms"]
                        candidates[key] = dict(event)
                        candidates[key]["_matched_search_terms"] = merged_terms
    finally:
        client.close()

    events = []
    excluded_non_table_tennis = 0
    excluded_inactive_or_closed = 0
    for event in candidates.values():
        if not is_table_tennis_event(event):
            excluded_non_table_tennis += 1
            continue
        if event.get("active") is False or event.get("closed") is True:
            excluded_inactive_or_closed += 1
            continue
        events.append(event)

    events.sort(key=lambda e: (str(e.get("startTime") or ""), str(e.get("title") or "")))
    stats = {
        "unique_search_results": len(candidates),
        "excluded_non_table_tennis": excluded_non_table_tennis,
        "excluded_inactive_or_closed_table_tennis": excluded_inactive_or_closed,
    }
    return events, stats


def load_database_names() -> list[str]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Simulator database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """SELECT DISTINCT TRIM(display_name) FROM players
               WHERE display_name IS NOT NULL AND TRIM(display_name) <> ''
               ORDER BY display_name"""
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def token_name_match(polymarket_name: str, database_name: str) -> str | None:
    """Match tokens independent of order; allow one-letter initials for review."""
    left = name_tokens(polymarket_name)
    right = name_tokens(database_name)
    if not left or len(left) != len(right):
        return None
    remaining = list(right)
    used_initial = False
    for token in sorted(left, key=len, reverse=True):
        exact_index = next((i for i, candidate in enumerate(remaining) if candidate == token), None)
        if exact_index is not None:
            remaining.pop(exact_index)
            continue
        initial_index = next(
            (i for i, candidate in enumerate(remaining)
             if (len(candidate) == 1 and token.startswith(candidate))
             or (len(token) == 1 and candidate.startswith(token))),
            None,
        )
        if initial_index is None:
            return None
        used_initial = True
        remaining.pop(initial_index)
    return "initial" if used_initial else "exact"


def find_database_match(name: str, database_names: list[str]) -> tuple[str, str, float | None]:
    target = norm_name(name)
    for candidate in database_names:
        if target == norm_name(candidate):
            return "exact", candidate, 1.0

    for candidate in database_names:
        match_type = token_name_match(name, candidate)
        if match_type == "exact":
            return "exact_name_match_order_insensitive", candidate, 1.0
        if match_type == "initial":
            return "possible_name_match_review_only", candidate, 0.95

    target_sorted = " ".join(sorted(name_tokens(name)))
    candidate_keys = {" ".join(sorted(name_tokens(candidate))): candidate for candidate in database_names}
    close = difflib.get_close_matches(target_sorted, list(candidate_keys), n=1, cutoff=0.90)
    if close:
        candidate_key = close[0]
        score = difflib.SequenceMatcher(None, target_sorted, candidate_key).ratio()
        return "possible_name_match_review_only", candidate_keys[candidate_key], round(score, 4)
    return "not_found", "", None


def build_outputs(events: list[dict], database_names: list[str], discovery_stats: dict | None = None) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()
    raw_path = RAW_DIR / "polymarket_us_table_tennis_events.json"
    raw_path.write_text(json.dumps({
        "source": SOURCE_URL, "retrieved_at_utc": retrieved_at, "events": events
    }, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    event_rows: list[dict] = []
    market_rows: list[dict] = []
    parsed_player_names: set[str] = set()
    unparsed_titles: list[str] = []

    for event in events:
        event_title = str(event.get("title") or event.get("name") or "")
        pair = extract_player_pair(event_title)
        markets = event.get("markets") if isinstance(event.get("markets"), list) else []
        market_titles = [
            str(m.get("title") or m.get("question") or "")
            for m in markets if isinstance(m, dict)
        ]
        if pair == (None, None):
            for title in market_titles:
                pair = extract_player_pair(title)
                if pair != (None, None):
                    break
        if pair == (None, None):
            unparsed_titles.append(event_title or str(event.get("slug") or event.get("id") or "untitled"))
            names: list[str] = []
        else:
            names = [pair[0], pair[1]]
            parsed_player_names.update(names)

        tags = event.get("tags") if isinstance(event.get("tags"), list) else []
        competition_tags = [
            str(tag.get("label")) for tag in tags
            if isinstance(tag, dict)
            and str(tag.get("slug", "")).casefold() not in {"sports", "games", "table-tennis"}
        ]
        event_rows.append({
            "event_id": event.get("id", ""),
            "event_slug": event.get("slug", ""),
            "event_title": event_title,
            "competition_tags": ";".join(competition_tags),
            "start_time": event.get("startTime", ""),
            "end_time": event.get("endTime", ""),
            "active": event.get("active", ""),
            "closed": event.get("closed", ""),
            "matched_search_terms": ";".join(event.get("_matched_search_terms", [])),
            "market_count": len(markets),
            "player_a": names[0] if len(names) > 0 else "",
            "player_b": names[1] if len(names) > 1 else "",
        })
        for market in markets:
            if not isinstance(market, dict):
                continue
            market_rows.append({
                "event_id": event.get("id", ""),
                "event_slug": event.get("slug", ""),
                "event_title": event_title,
                "market_id": market.get("id", ""),
                "market_slug": market.get("slug", ""),
                "market_title": market.get("title") or market.get("question") or "",
                "active": market.get("active", ""),
                "closed": market.get("closed", ""),
                "outcome": market.get("outcome", ""),
                "volume": market.get("volume", ""),
                "liquidity": market.get("liquidity", ""),
            })

    coverage_rows = []
    for name in sorted(parsed_player_names, key=str.casefold):
        status, match, score = find_database_match(name, database_names)
        coverage_rows.append({
            "polymarket_player": name,
            "database_status": status,
            "possible_database_name": match,
            "similarity": score if score is not None else "",
            "identity_action": (
                "manual verification required; no automatic identity merge"
                if status != "exact" else
                "same normalized display name; source identity still unverified"
            ),
        })

    def write_csv(path: Path, rows: list[dict]) -> None:
        fields = list(rows[0]) if rows else []
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            if fields:
                writer.writeheader()
                writer.writerows(rows)

    events_csv = OUT_DIR / "polymarket_us_events.csv"
    markets_csv = OUT_DIR / "polymarket_us_markets.csv"
    coverage_csv = OUT_DIR / "polymarket_us_player_coverage.csv"
    write_csv(events_csv, event_rows)
    write_csv(markets_csv, market_rows)
    write_csv(coverage_csv, coverage_rows)

    counts = {
        "events_found": len(events),
        "markets_found": len(market_rows),
        "events_with_parsed_player_pair": sum(bool(r["player_a"] and r["player_b"]) for r in event_rows),
        "events_with_unparsed_title": len(unparsed_titles),
        "distinct_polymarket_players_parsed": len(parsed_player_names),
        "database_player_names_checked": len(database_names),
        "exact_name_matches": sum(
            r["database_status"] in {"exact", "exact_name_match_order_insensitive"}
            for r in coverage_rows
        ),
        "possible_name_matches_for_manual_review": sum(
            r["database_status"] == "possible_name_match_review_only" for r in coverage_rows
        ),
        "players_not_found_in_database": sum(r["database_status"] == "not_found" for r in coverage_rows),
    }
    report = {
        "source": SOURCE_URL,
        "access": "public read-only API; no API key or account credentials",
        "retrieved_at_utc": retrieved_at,
        "search_terms": list(SEARCH_TERMS),
        "discovery_filter_stats": discovery_stats or {},
        "counts": counts,
        "unparsed_event_titles": unparsed_titles,
        "outputs": {
            "raw_events": str(raw_path.relative_to(ROOT)),
            "events_csv": str(events_csv.relative_to(ROOT)),
            "markets_csv": str(markets_csv.relative_to(ROOT)),
            "player_coverage_csv": str(coverage_csv.relative_to(ROOT)),
        },
        "safety": [
            "Only events carrying Polymarket's explicit Table Tennis category/sport tag are retained.",
            "Only active, non-closed events are retained for this current-listings scan.",
            "No account, portfolio, wallet, or order endpoints were accessed.",
            "No orders were placed and no simulator database rows were changed.",
            "Name similarity and initial matches are review hints only; no player identities were merged.",
        ],
    }
    report_path = OUT_DIR / "polymarket_us_scan_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def main() -> None:
    events, discovery_stats = discover_events()
    if not events:
        raise RuntimeError("No active, explicitly tagged Polymarket US table-tennis events found.")
    build_outputs(events, load_database_names(), discovery_stats)


if __name__ == "__main__":
    main()
