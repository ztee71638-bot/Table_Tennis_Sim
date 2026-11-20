#!/usr/bin/env python3
"""Read-only Polymarket US table-tennis market discovery and database coverage audit.

This script uses only the public Polymarket US API through the official SDK.
It does not access account data, place orders, or modify the simulator database.
"""
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
    "table tennis",
    "ping pong",
    "WTT",
    "Setka Cup",
    "TT Elite",
    "Czech Liga Pro",
    "TT Cup",
)
VS_RE = re.compile(r"^(.+?)\\s+(?:vs?\\.?|versus)\\s+(.+?)\\s*$", re.IGNORECASE)


def norm_name(value: str) -> str:
    """Normalize a display name for conservative comparison, not identity merging."""
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def extract_player_pair(title: str | None) -> tuple[str | None, str | None]:
    """Extract a pair only when a title explicitly uses a vs/versus separator."""
    if not title:
        return None, None
    cleaned = re.sub(r"^(who will win|winner:?)\\s*", "", str(title).strip(), flags=re.I)
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


def discover_events() -> list[dict]:
    """Search several table-tennis phrases and deduplicate by stable event ID/slug."""
    from polymarket_us import PolymarketUS

    client = PolymarketUS()
    found: dict[str, dict] = {}
    try:
        for term in SEARCH_TERMS:
            response = client.search.query({"query": term, "limit": 100, "status": "active"})
            for event in as_list(response, "events"):
                if not isinstance(event, dict):
                    continue
                key = str(event.get("id") or event.get("slug") or json.dumps(event, sort_keys=True))
                event_copy = dict(event)
                event_copy.setdefault("_matched_search_terms", [])
                event_copy["_matched_search_terms"] = sorted(
                    set(event_copy["_matched_search_terms"]) | {term}
                )
                if key in found:
                    event_copy["_matched_search_terms"] = sorted(
                        set(found[key].get("_matched_search_terms", [])) | {term}
                    )
                    # Prefer the response with the most complete event payload.
                    if len(json.dumps(event_copy, default=str)) < len(json.dumps(found[key], default=str)):
                        event_copy = found[key] | {"_matched_search_terms": event_copy["_matched_search_terms"]}
                found[key] = event_copy
    finally:
        client.close()
    return sorted(found.values(), key=lambda e: (str(e.get("startTime") or ""), str(e.get("title") or "")))


def load_database_names() -> list[str]:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Simulator database not found: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            """SELECT DISTINCT TRIM(display_name)
               FROM players
               WHERE display_name IS NOT NULL AND TRIM(display_name) <> ''
               ORDER BY display_name"""
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        conn.close()


def find_database_match(name: str, database_names: list[str]) -> tuple[str, str, float | None]:
    target = norm_name(name)
    exact = {norm_name(candidate): candidate for candidate in database_names}
    if target in exact:
        return "exact", exact[target], 1.0
    close = difflib.get_close_matches(target, list(exact), n=1, cutoff=0.90)
    if close:
        candidate = close[0]
        score = difflib.SequenceMatcher(None, target, candidate).ratio()
        return "possible_name_match_review_only", exact[candidate], round(score, 4)
    return "not_found", "", None


def build_outputs(events: list[dict], database_names: list[str]) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    raw_path = RAW_DIR / "polymarket_us_table_tennis_events.json"
    raw_path.write_text(
        json.dumps(
            {"source": SOURCE_URL, "retrieved_at_utc": retrieved_at, "events": events},
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

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

        event_rows.append({
            "event_id": event.get("id", ""),
            "event_slug": event.get("slug", ""),
            "event_title": event_title,
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
            "identity_action": "none; manual verification required" if status != "exact" else "existing exact-name record; source identity still unverified",
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
        "exact_name_matches": sum(r["database_status"] == "exact" for r in coverage_rows),
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
        "counts": counts,
        "unparsed_event_titles": unparsed_titles,
        "outputs": {
            "raw_events": str(raw_path.relative_to(ROOT)),
            "events_csv": str(events_csv.relative_to(ROOT)),
            "markets_csv": str(markets_csv.relative_to(ROOT)),
            "player_coverage_csv": str(coverage_csv.relative_to(ROOT)),
        },
        "safety": [
            "No account, portfolio, wallet, or order endpoints were accessed.",
            "No orders were placed and no simulator database rows were changed.",
            "Name similarity is a review hint only; no cross-source player identities were merged.",
            "Event titles that do not explicitly identify a player pair are retained for manual review.",
        ],
    }
    report_path = OUT_DIR / "polymarket_us_scan_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def main() -> None:
    events = discover_events()
    if not events:
        raise RuntimeError(
            "Polymarket US search returned no events for the configured table-tennis terms. "
            "The scan is stopped rather than reporting an empty success."
        )
    names = load_database_names()
    build_outputs(events, names)


if __name__ == "__main__":
    main()
