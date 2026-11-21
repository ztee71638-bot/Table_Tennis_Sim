#!/usr/bin/env python3
"""Publish current Polymarket table-tennis events and source-scoped player histories."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reconcile_polymarket_players as reconciliation
import enrich_polymarket_tabletennisapi as tabletennisapi_discovery

RAW_EVENTS = ROOT / "data/raw/polymarket_us_table_tennis_events.json"
TABLETENNISAPI_OUT = ROOT / "data/processed/tabletennisapi_polymarket_players.json"
PROFILE_OUT = ROOT / "site/data/tabletennisapi_profiles.json"
PROFILE_DATA_START = "<!-- TABLETENNISAPI_PROFILE_DATA_START -->"
PROFILE_DATA_END = "<!-- TABLETENNISAPI_PROFILE_DATA_END -->"
DB_PATH = ROOT / "data/database/table_tennis.sqlite"
OUT = ROOT / "site/data/polymarket_active.json"


def player_history(name: str, history: list[dict], scope: str) -> dict:
    candidates = reconciliation.player_candidates(name, history, scope)
    exact = [c for c in candidates if c["match_type"] == "exact"]
    # Initial-based matches are useful discovery leads (for example, "Erik Mares"
    # versus "Mares E."), but are deliberately kept review-only and never promoted
    # to a verified identity or a model-eligible player.
    usable = exact if exact else [c for c in candidates if c["match_type"] == "initial"]
    if len(usable) != 1:
        return {
            "status": "ambiguous" if len(usable) > 1 or len(candidates) > 1 else "not_found",
            "candidate_count": len(candidates),
            "identity_note": "No unique source-scoped player candidate; history is not attached.",
            "matches": [],
        }
    candidate = usable[0]
    if not candidate["scope_match"] and scope:
        return {
            "status": "other_competition_only",
            "identity_note": "A same-name record exists, but no match in this event's competition was found.",
            "matches": [],
        }
    pid = candidate["source_player_id"]
    rows = []
    wins = 0
    for m in sorted(candidate["matches"], key=lambda x: (x.get("match_date") or "", x.get("match_time") or ""), reverse=True):
        own_a = m["a_id"] == pid
        won = m["winner_player_pk"] == (m["a_pk"] if own_a else m["b_pk"])
        wins += int(won)
        rows.append({
            "date": m.get("match_date") or "",
            "time": m.get("match_time") or "",
            "competition": m.get("competition") or "",
            "opponent": m.get("b_name") if own_a else m.get("a_name"),
            "result": "W" if won else "L",
            "score": f'{m.get("sets_a")}-{m.get("sets_b")}' if own_a else f'{m.get("sets_b")}-{m.get("sets_a")}',
        })
    initial_only = candidate["match_type"] == "initial"
    return {
        "status": "name_initial_match_review_only" if initial_only else "exact_name_match_identity_unverified",
        "display_name": candidate["display_name"],
        "source_player_id": pid,
        "matches_count": len(rows),
        "wins": wins,
        "losses": len(rows) - wins,
        "last_match_date": rows[0]["date"] if rows else "",
        "competition_matches": len(candidate["relevant_matches"]),
        "recent_matches": rows[:20],
        "identity_note": (
            "Initial/surname-format candidate in DataSportsAPI. Review the source ID and competition before relying on this history; it is not a confirmed identity."
            if initial_only else
            "Exact name match in DataSportsAPI, but cross-source identity is not independently verified. Treat this history as a candidate, not a confirmed identity."
        ),
    }



def wtt_model_record(name: str, model_pools: dict, scope: str) -> dict:
    """Find a WTT model record by full token-set name; never fuzzy-merge identities."""
    if scope != "WTT" or not isinstance(model_pools, dict):
        return {"status": "not_applicable", "identity_note": "WTT model lookup is only used for WTT listings."}
    candidates = []
    for source, pool in model_pools.items():
        if not isinstance(pool, dict):
            continue
        for player_id, record in pool.items():
            if not isinstance(record, dict):
                continue
            if reconciliation.normalized_tokens_match(name, record.get("display_name") or "") == "exact":
                candidates.append((source, str(player_id), record))
    if len(candidates) != 1:
        return {
            "status": "ambiguous" if len(candidates) > 1 else "not_found",
            "candidate_count": len(candidates),
            "identity_note": "No unique full-token WTT model record; no model match is assumed.",
        }
    source, player_id, record = candidates[0]
    return {
        "status": "wtt_model_record_identity_unverified",
        "source": source,
        "source_player_id": player_id,
        "display_name": record.get("display_name") or "",
        "matches": int(record.get("matches") or 0),
        "last_match_date": record.get("last_date") or "",
        "recent_form_last10": list(record.get("recent_form_last10") or [])[-10:],
        "identity_note": "Unique full-token name candidate in the WTT-trained pool. Cross-source athlete identity is not independently verified; this record is evidence only.",
    }



def tabletennisapi_profile(name: str, scope: str, players: dict) -> dict:
    if scope != "WTT":
        return {"status": "not_applicable", "model_eligible": False}
    cached = players.get(tabletennisapi_discovery.normalized_name(name))
    if isinstance(cached, dict):
        return cached
    return {
        "status": "queued_not_checked",
        "source": "Table Tennis API (DeveloperData)",
        "identity_note": "Queued for a budgeted free-tier player-directory lookup.",
        "model_eligible": False,
    }


def main() -> None:
    if not RAW_EVENTS.exists():
        raise SystemExit("Polymarket event snapshot is missing; run the public read-only scanner first.")
    payload = json.loads(RAW_EVENTS.read_text(encoding="utf-8"))
    events = payload.get("events", [])
    tabletennisapi_data = {}
    tabletennisapi_source = {"available": False, "source": "Table Tennis API (DeveloperData)"}
    if TABLETENNISAPI_OUT.exists():
        try:
            tabletennisapi_data = json.loads(TABLETENNISAPI_OUT.read_text(encoding="utf-8"))
            tabletennisapi_source = {
                "available": True,
                "source": tabletennisapi_data.get("source") or "Table Tennis API (DeveloperData)",
                "retrieved_at_utc": tabletennisapi_data.get("retrieved_at_utc") or "",
                "names_checked": int(tabletennisapi_data.get("names_checked") or 0),
                "players_checked_today": int(tabletennisapi_data.get("players_checked_today") or 0),
                "calls_today": int(tabletennisapi_data.get("calls_today") or 0),
                "daily_safety_budget": int(tabletennisapi_data.get("daily_safety_budget") or 40),
            }
        except (ValueError, OSError):
            tabletennisapi_data = {}
    tabletennisapi_players = tabletennisapi_data.get("players", {}) if isinstance(tabletennisapi_data, dict) else {}
    if not isinstance(tabletennisapi_players, dict):
        tabletennisapi_players = {}
    # Deploy-only rebuilds do not call the provider. Preserve the last app-page
    # summaries instead of replacing them with empty queued states.
    if not tabletennisapi_players and INDEX_PATH.exists():
        existing_html = INDEX_PATH.read_text(encoding="utf-8")
        match = re.search(
            r'<script id="tabletennisapi-profile-data" type="application/json">(.*?)</script>',
            existing_html, re.DOTALL,
        )
        if match:
            try:
                embedded = json.loads(match.group(1))
                profiles = embedded.get("profiles", {})
                if isinstance(profiles, dict):
                    tabletennisapi_players = profiles
            except ValueError:
                pass
        if OUT.exists():
            try:
                previous_output = json.loads(OUT.read_text(encoding="utf-8"))
                previous_source = previous_output.get("tabletennisapi_source")
                if isinstance(previous_source, dict):
                    tabletennisapi_source = previous_source
            except (ValueError, OSError):
                pass

    previous_players = {}
    if OUT.exists():
        try:
            previous = json.loads(OUT.read_text(encoding="utf-8"))
            previous_players = {
                str(p.get("name", "")).casefold(): p.get("history", {})
                for p in previous.get("players", [])
                if p.get("name")
            }
        except (ValueError, OSError):
            previous_players = {}
    history: list[dict] = []
    source_info = {"available": False, "reason": "Database unavailable"}
    model_pools = {}
    model_path = ROOT / "data/processed/current_player_states.json"
    if model_path.exists():
        try:
            model_pools = json.loads(model_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            model_pools = {}
    if DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            history, source_info = reconciliation.load_source_history(conn)
        finally:
            conn.close()

    output_events = []
    player_index: dict[str, dict] = {}
    provider_profiles: dict[str, dict] = {}
    for event in events:
        title = str(event.get("title") or event.get("name") or "")
        a, b = reconciliation.event_pair(event)
        if not a or not b:
            continue
        scope = reconciliation.event_competition(event)
        def resolve_history(name: str) -> dict:
            if source_info.get("available"):
                return player_history(name, history, scope)
            cached = previous_players.get(name.casefold(), {})
            if cached.get("status") in {"exact_name_match_identity_unverified", "name_initial_match_review_only"}:
                return cached
            return {
                "status": "source_not_loaded",
                "identity_note": "Recent source history is unavailable in this refresh.",
                "matches": [],
            }

        pa = resolve_history(a)
        pb = resolve_history(b)
        ma = wtt_model_record(a, model_pools, scope)
        mb = wtt_model_record(b, model_pools, scope)
        ta = tabletennisapi_profile(a, scope, tabletennisapi_players)
        tb = tabletennisapi_profile(b, scope, tabletennisapi_players)
        if scope == "WTT":
            provider_profiles[tabletennisapi_discovery.normalized_name(a)] = ta
            provider_profiles[tabletennisapi_discovery.normalized_name(b)] = tb
        slug = event.get("slug") or ""
        event_row = {
            "event_id": str(event.get("id") or ""),
            "slug": slug,
            "title": title,
            "competition": scope or "Table Tennis",
            "start_time_utc": event.get("startTime") or "",
            "end_time_utc": event.get("endTime") or "",
            "active": event.get("active") is not False,
            "closed": event.get("closed") is True,
            "url": f"https://polymarket.us/event/{slug}" if slug else "https://polymarket.us",
            "player_a": {"name": a, "history": pa, "model_record": ma},
            "player_b": {"name": b, "history": pb, "model_record": mb},
        }
        output_events.append(event_row)
        for name, details in ((a, pa), (b, pb)):
            key = name.casefold()
            if key not in player_index:
                model_details = ma if name == a else mb
                player_index[key] = {"name": name, "events": [], "history": details, "model_record": model_details}
            player_index[key]["events"].append({"title": title, "competition": scope, "url": event_row["url"]})

    output = {
        "source": "Polymarket US public read-only listings",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "events_count": len(output_events),
        "players_count": len(player_index),
        "history_source": source_info,
        "tabletennisapi_source": tabletennisapi_source,
        "events": output_events,
        "players": sorted(player_index.values(), key=lambda p: p["name"].casefold()),
        "limitations": [
            "Listings are current discovery data, not confirmation of an athlete's real-world activity.",
            "DataSportsAPI histories are source-scoped and exact-name candidates only; identity is not independently verified.",
            "No automatic identity merges or model promotion are performed.",
            "DataSportsAPI recent histories are descriptive evidence only; its unpromoted model is not used to issue picks.",
            "Table Tennis API free-tier player profiles are on-demand discovery evidence only; individual player match-history and head-to-head endpoints are not called, and profiles are not used for model training or automatic identity merges."
        ]
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Publish provider profile summaries as a separate static asset. This avoids
    # having scheduled data refreshes rewrite site/index.html while UI deployments
    # or feature branches may be updating that page.
    PROFILE_OUT.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_OUT.write_text(
        json.dumps({"profiles": provider_profiles}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUT.relative_to(ROOT)), "events": len(output_events), "players": len(player_index), "history_source": source_info}, indent=2))


if __name__ == "__main__":
    main()
