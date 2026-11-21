#!/usr/bin/env python3
"""Budgeted, on-demand WTT player discovery through the free Table Tennis API tier.

Only searches names appearing in active WTT Polymarket listings. It retrieves a
profile only after one unique full-token name candidate is found. It does not
download player match histories, retain raw API responses, train models, or
merge athlete identities.
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_EVENTS = ROOT / "data/raw/polymarket_us_table_tennis_events.json"
STATE_PATH = ROOT / "data/processed/tabletennisapi_polymarket_lookup_state.json"
OUT_PATH = ROOT / "data/processed/tabletennisapi_polymarket_players.json"
BASE_URL = "https://api.tabletennisapi.com/v1"
SOURCE_NAME = "Table Tennis API (DeveloperData)"
MAX_PLAYERS_PER_RUN = 5
MAX_CALLS_PER_UTC_DAY = 40  # leaves headroom below the free plan's 50/day
REFRESH_DAYS = 7
API_KEY = os.environ.get("TABLETENNISAPI_KEY", "").strip()
LAST_API_CALL_MONOTONIC: float | None = None


def tokens(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.findall(r"[a-z0-9]+", normalized.casefold())


def normalized_name(value: str) -> str:
    return " ".join(sorted(tokens(value)))


def name_match_type(query_name: str, candidate_name: str) -> str | None:
    left, right = tokens(query_name), tokens(candidate_name)
    if not left or len(left) != len(right):
        return None
    remaining = list(right)
    used_initial = False
    for token in sorted(left, key=len, reverse=True):
        index = next((i for i, item in enumerate(remaining) if item == token), None)
        if index is not None:
            remaining.pop(index)
            continue
        index = next((i for i, item in enumerate(remaining)
                      if (len(item) == 1 and token.startswith(item))
                      or (len(token) == 1 and item.startswith(token))), None)
        if index is None:
            return None
        used_initial = True
        remaining.pop(index)
    return "initial" if used_initial else "exact"


def select_candidate(query_name: str, candidates: list[dict]) -> tuple[str, dict | None, list[dict]]:
    exact = [p for p in candidates if isinstance(p, dict)
             and name_match_type(query_name, p.get("name", "")) == "exact"]
    if len(exact) == 1:
        return "exact_unique", exact[0], exact
    if len(exact) > 1:
        return "ambiguous", None, exact
    initials = [p for p in candidates if isinstance(p, dict)
                and name_match_type(query_name, p.get("name", "")) == "initial"]
    if len(initials) == 1:
        return "initial_review_only", initials[0], initials
    if len(initials) > 1 or len(candidates) > 1:
        return "ambiguous", None, initials or candidates
    return "not_found", None, []


def profile_summary(query_name: str, candidate: dict, profile: dict, looked_up_at: str) -> dict:
    records = []
    for row in profile.get("record", []) if isinstance(profile.get("record"), list) else []:
        if not isinstance(row, dict):
            continue
        records.append({
            "discipline": str(row.get("discipline") or ""),
            "played": int(row.get("played") or 0),
            "won": int(row.get("won") or 0),
            "lost": int(row.get("lost") or 0),
            "first_match": str(row.get("first") or ""),
            "last_match": str(row.get("last") or ""),
        })
    ranks = []
    for row in profile.get("world_ranks", []) if isinstance(profile.get("world_ranks"), list) else []:
        if not isinstance(row, dict):
            continue
        ranks.append({
            "discipline": str(row.get("discipline") or ""),
            "list": str(row.get("list") or ""),
            "rank": int(row.get("rank") or 0),
            "points": int(row.get("points") or 0),
            "week": str(row.get("week") or ""),
        })
    return {
        "status": "exact_name_match_identity_unverified",
        "source": SOURCE_NAME,
        "source_player_id": str(candidate.get("id") or ""),
        "display_name": str(profile.get("name") or candidate.get("name") or ""),
        "country": profile.get("country") or candidate.get("country"),
        "records_by_discipline": records,
        "record_window_note": "Free plan visibility window only (yesterday through upcoming dates); not a career-total record.",
        "world_ranks": ranks,
        "looked_up_at_utc": looked_up_at,
        "identity_note": (
            "Unique full-token name candidate in Table Tennis API. The name match is not "
            "independent proof that this is the same athlete as the Polymarket listing."
        ),
        "model_eligible": False,
    }


def api_get(path: str, params: dict | None = None) -> dict:
    global LAST_API_CALL_MONOTONIC
    if LAST_API_CALL_MONOTONIC is not None:
        elapsed = time.monotonic() - LAST_API_CALL_MONOTONIC
        if elapsed < 6.2:
            time.sleep(6.2 - elapsed)
    LAST_API_CALL_MONOTONIC = time.monotonic()
    query = urllib.parse.urlencode(params or {})
    url = f"{BASE_URL}{path}" + (f"?{query}" if query else "")
    request = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json",
                 "User-Agent": "TableTennisSim/1.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or "data" not in payload:
        raise ValueError(f"Unexpected Table Tennis API response for {path}")
    return payload


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def event_players() -> list[tuple[str, str]]:
    if not RAW_EVENTS.exists():
        return []
    try:
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import reconcile_polymarket_players as reconciliation
        payload = json.loads(RAW_EVENTS.read_text(encoding="utf-8"))
    except (OSError, ValueError, ImportError):
        return []
    found: dict[str, tuple[str, str]] = {}
    for event in payload.get("events", []):
        if not isinstance(event, dict) or event.get("active") is False or event.get("closed") is True:
            continue
        scope = reconciliation.event_competition(event)
        # This API is professional-tour coverage; do not use it as evidence for
        # domestic Setka/Czech/TT Elite competitions.
        if scope != "WTT":
            continue
        a, b = reconciliation.event_pair(event)
        for name in (a, b):
            if name and len(tokens(name)) >= 2:
                found.setdefault(normalized_name(name), (name, scope))
    return list(found.values())


def is_fresh(record: dict, now: datetime) -> bool:
    if record.get("status") in {"provider_rate_limited", "provider_error"}:
        return False
    stamp = record.get("looked_up_at_utc")
    if not stamp:
        return False
    try:
        looked = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        return now - looked < timedelta(days=REFRESH_DAYS)
    except (ValueError, TypeError):
        return False


def lookup_one(name: str, state: dict, calls: int) -> tuple[dict, int]:
    key = normalized_name(name)
    looked_at = datetime.now(timezone.utc).isoformat()
    try:
        payload = api_get("/players", {"q": name, "per_page": 50})
        calls += 1
        candidates = payload.get("data") if isinstance(payload.get("data"), list) else []
        status, candidate, possible = select_candidate(name, candidates)
        if status == "not_found":
            return ({
                "status": "not_found", "source": SOURCE_NAME, "candidate_count": 0,
                "looked_up_at_utc": looked_at,
                "identity_note": "No exact full-name candidate was found in the provider player directory.",
                "model_eligible": False,
            }, calls)
        if status == "ambiguous":
            return ({
                "status": "ambiguous", "source": SOURCE_NAME,
                "candidate_count": len(possible),
                "candidate_names": [str(p.get("name") or "") for p in possible[:8]],
                "looked_up_at_utc": looked_at,
                "identity_note": "Multiple possible provider players; no profile attached.",
                "model_eligible": False,
            }, calls)
        if status == "initial_review_only":
            return ({
                "status": "name_initial_match_review_only", "source": SOURCE_NAME,
                "source_player_id": str(candidate.get("id") or ""),
                "display_name": str(candidate.get("name") or ""),
                "country": candidate.get("country"),
                "looked_up_at_utc": looked_at,
                "identity_note": "Only an initial/surname-format match was found; profile withheld for identity review.",
                "model_eligible": False,
            }, calls)
        player_id = str(candidate.get("id") or "")
        if not re.fullmatch(r"pl_[0-9a-z]{8}", player_id):
            return ({
                "status": "invalid_provider_record", "source": SOURCE_NAME,
                "looked_up_at_utc": looked_at,
                "identity_note": "Provider returned a player candidate without a valid stable player ID.",
                "model_eligible": False,
            }, calls)
        detail = api_get(f"/players/{player_id}")
        calls += 1
        profile = detail.get("data") if isinstance(detail.get("data"), dict) else {}
        if str(profile.get("id") or "") != player_id:
            raise ValueError("Provider player detail ID did not match the requested player ID")
        return (profile_summary(name, candidate, profile, looked_at), calls)
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            return ({
                "status": "provider_rate_limited", "source": SOURCE_NAME,
                "looked_up_at_utc": looked_at,
                "identity_note": "Provider free-tier rate limit reached; this player will be retried later.",
                "model_eligible": False,
            }, calls)
        if exc.code in (401, 403):
            raise RuntimeError(
                f"Table Tennis API authentication/plan error HTTP {exc.code}; "
                "check TABLETENNISAPI_KEY and the free-plan endpoint access."
            ) from exc
        raise RuntimeError(f"Table Tennis API request failed HTTP {exc.code}") from exc


def main() -> None:
    if not API_KEY:
        print("TABLETENNISAPI_KEY is not configured; skipping optional WTT player discovery.")
        return
    now = datetime.now(timezone.utc)
    day = now.date().isoformat()
    state = load_json(STATE_PATH, {"utc_day": day, "calls_today": 0, "players": {}})
    if state.get("utc_day") != day:
        state["utc_day"] = day
        state["calls_today"] = 0
    state.setdefault("players", {})
    calls = int(state.get("calls_today") or 0)
    if calls >= MAX_CALLS_PER_UTC_DAY:
        print(f"Daily provider safety budget reached ({calls}/{MAX_CALLS_PER_UTC_DAY}); no calls made.")
        return

    active = event_players()
    queue = []
    for name, _scope in active:
        key = normalized_name(name)
        cached = state["players"].get(key, {})
        if not is_fresh(cached, now):
            queue.append(name)
    remaining = min(MAX_PLAYERS_PER_RUN, (MAX_CALLS_PER_UTC_DAY - calls) // 2)
    selected = queue[:remaining]
    print(f"Active WTT player names: {len(active)}; due for lookup: {len(queue)}; selected this run: {len(selected)}.")
    for name in selected:
        result, calls = lookup_one(name, state, calls)
        state["players"][normalized_name(name)] = {"query_name": name, **result}
        if result.get("status") == "provider_rate_limited":
            break
    state["calls_today"] = calls
    state["last_run_at_utc"] = datetime.now(timezone.utc).isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    # This is an app-facing profile summary, not a raw API mirror or training set.
    # It contains only name-match status, aggregate discipline records and ranking
    # summaries permitted for display in the user's own app.
    OUT_PATH.write_text(json.dumps({
        "source": SOURCE_NAME,
        "source_terms": "https://tabletennisapi.com/terms",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "players_cached": len(state["players"]),
        "players_checked_today": sum(
            1 for item in state["players"].values()
            if str(item.get("looked_up_at_utc") or "").startswith(day)
        ),
        "calls_today": calls,
        "daily_safety_budget": MAX_CALLS_PER_UTC_DAY,
        "players": state["players"],
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Table Tennis API lookup complete. Calls today: {calls}/{MAX_CALLS_PER_UTC_DAY}; cached names: {len(state['players'])}.")


if __name__ == "__main__":
    main()
