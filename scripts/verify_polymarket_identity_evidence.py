#!/usr/bin/env python3
"""Build an evidence-led audit for unresolved Polymarket player identities.

Independent result feeds can corroborate a candidate only when date, opponent,
and every recorded set score match a DataSportsAPI fixture. Corroboration is
never auto-approved: every source ID remains unverified until human review.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/polymarket_identity_review_queue.csv"
RAW = ROOT / "data/raw/datasportsapi"
OUTPUT = ROOT / "data/processed/polymarket_identity_evidence_audit.csv"
REPORT = ROOT / "data/processed/polymarket_identity_evidence_report.json"

PUBLIC_PROFILE_EVIDENCE = {
    "ganghyeon park": {
        "url": "https://www.butterfly-korea.co.kr/sponsoring/detail/park-ganghyeon.html",
        "source": "Butterfly Korea player/sponsor profile",
        "type": "player_biography",
        "scope": "public_name_only",
        "note": "Profile identifies Park Ganghyeon; it does not reference the DataSportsAPI source_player_id.",
    },
    "honoka hashimoto": {
        "url": "https://jtta.or.jp/national-player-w5",
        "source": "Japan Table Tennis Association national-team profile",
        "type": "national_federation_profile",
        "scope": "public_name_only",
        "note": "Federation profile identifies HASHIMOTO, Honoka; it does not reference the DataSportsAPI source_player_id.",
    },
    "kaho akae": {
        "url": "https://results.ittf.link/index.php/player-profile/details/59/34343",
        "source": "International Table Tennis Federation player profile",
        "type": "international_federation_profile",
        "scope": "public_name_only",
        "note": "ITTF profile identifies AKAE Kaho; it does not reference the DataSportsAPI source_player_id.",
    },
}

# Each record is a manually researched, independent public match result.
# "sets" is ordered from the candidate player's perspective (their points first).
# The script requires an exact date/opponent/set-score match in the raw API snapshots.
MATCH_LEVEL_EVIDENCE = [
    {
        "candidate": "Alesh Bayer", "source_player_id": "115022",
        "opponent": "Daniel Tuma", "opponent_source_player_id": "69500",
        "date": "2026-11-19",
        "sets": [(4, 11), (11, 9), (13, 11), (11, 5)],
        "source": "Score-Tennis independent match result",
        "url": "https://score-tennis.com/games/alesh-bayer-daniel-tuma-1171995/",
    },
    {
        "candidate": "Alesh Bayer", "source_player_id": "115022",
        "opponent": "Daniel Tuma", "opponent_source_player_id": "69500",
        "date": "2026-11-19",
        "sets": [(11, 8), (11, 13), (11, 6), (12, 14), (11, 7)],
        "source": "Score-Tennis independent match result",
        "url": "https://score-tennis.com/games/alesh-bayer-daniel-tuma-1171681/",
    },
    {
        "candidate": "Daniel Tuma", "source_player_id": "69500",
        "opponent": "Alesh Bayer", "opponent_source_player_id": "115022",
        "date": "2026-11-19",
        "sets": [(8, 11), (10, 12), (11, 8), (8, 11)],
        "source": "Score-Tennis independent head-to-head results",
        "url": "https://www.aiscore.com/head-to-head/table-tennis/alesh-bayer-vs-daniel-tuma",
    },
    {
        "candidate": "Erik Mares", "source_player_id": "632210",
        "opponent": "Tomas Postelt", "opponent_source_player_id": "176",
        "date": "2026-11-19",
        "sets": [(7, 11), (11, 7), (9, 11), (12, 10), (9, 11)],
        "source": "Score-Tennis independent match result",
        "url": "https://score-tennis.com/games/erik-maresh-tomas-postelt-1171068/",
    },
    {
        "candidate": "Jakub Pilch", "source_player_id": "625247",
        "opponent": "Erik Mares", "opponent_source_player_id": "632210",
        "date": "2026-11-19",
        "sets": [(5, 11), (11, 9), (12, 10), (17, 15)],
        "source": "PongData independent match archive",
        "url": "https://pongdata.com/players/pilch-j-10xql5o5bp8/matches?year=2026",
    },
]

FIELDS = [
    "polymarket_player", "competition_scope", "database_status",
    "candidate_count", "candidate_options_json", "independent_evidence_status",
    "evidence_source", "evidence_type", "evidence_url", "evidence_scope",
    "matched_fixture_ids", "matched_independent_result_count",
    "source_player_id_link_status", "decision", "reviewer_action_required",
    "search_hint", "search_url", "verification_rule", "evidence_notes",
]


def preferred_search_hint(name: str, competition: str) -> str:
    if competition == "Setka Cup":
        return f'"{name}" site:tabletennis.setkacup.com/en/participants'
    if competition == "Czech Liga Pro":
        return f'"{name}" table tennis Czech Liga Pro official player profile'
    if competition == "WTT":
        return f'"{name}" site:ittf.com OR site:worldtabletennis.com player profile'
    return f'"{name}" table tennis official player profile'


def _period_values(score: dict) -> list[int]:
    periods = (score or {}).get("periods") or {}
    values = []
    for key in sorted(periods, key=lambda k: int(k.replace("period", "")) if k.startswith("period") else 999):
        value = periods[key]
        if isinstance(value, (int, float)):
            values.append(int(value))
    return values


def load_fixtures(raw_dir: Path) -> list[dict]:
    fixtures = []
    if not raw_dir.exists():
        return fixtures
    for path in sorted(raw_dir.glob("fixtures_*.json")):
        try:
            snapshot = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        for page in snapshot.get("pages", []):
            payload = page.get("payload") or {}
            for fixture in payload.get("data", []):
                item = dict(fixture)
                item["_snapshot_date"] = snapshot.get("date") or path.stem.removeprefix("fixtures_")
                fixtures.append(item)
    return fixtures


def _exact_fixture_match(evidence: dict, fixture: dict) -> bool:
    if (fixture.get("league") or {}).get("name") != "Czech Liga Pro":
        return False
    if fixture.get("_snapshot_date") != evidence["date"]:
        return False
    home, away = fixture.get("home") or {}, fixture.get("away") or {}
    home_id, away_id = str(home.get("id", "")), str(away.get("id", ""))
    candidate_id = evidence["source_player_id"]
    opponent_id = evidence["opponent_source_player_id"]
    if home_id == candidate_id and away_id == opponent_id:
        first, second = _period_values(fixture.get("homeScore")), _period_values(fixture.get("awayScore"))
    elif away_id == candidate_id and home_id == opponent_id:
        first, second = _period_values(fixture.get("awayScore")), _period_values(fixture.get("homeScore"))
    else:
        return False
    if not first or len(first) != len(second):
        return False
    return list(zip(first, second)) == list(evidence["sets"])


def find_match_level_evidence(name: str, candidate_options_json: str, fixtures: list[dict]) -> list[dict]:
    try:
        candidates = json.loads(candidate_options_json or "[]")
    except json.JSONDecodeError:
        candidates = []
    candidate_ids = {str(c.get("source_player_id")) for c in candidates if c.get("source_player_id") is not None}
    found = []
    for evidence in MATCH_LEVEL_EVIDENCE:
        if evidence["candidate"].casefold() != name.casefold():
            continue
        if evidence["source_player_id"] not in candidate_ids:
            continue
        for fixture in fixtures:
            if _exact_fixture_match(evidence, fixture):
                found.append({
                    "fixture_id": str(fixture.get("id", "")),
                    "source": evidence["source"],
                    "url": evidence["url"],
                    "candidate_source_player_id": evidence["source_player_id"],
                    "opponent": evidence["opponent"],
                    "date": evidence["date"],
                })
                break
    return found


def build_audit(rows: list[dict], fixtures: list[dict] | None = None) -> list[dict]:
    fixtures = fixtures or []
    audit = []
    for row in rows:
        name = row.get("polymarket_player", "").strip()
        scope = row.get("competition_scope", "").strip()
        profile = PUBLIC_PROFILE_EVIDENCE.get(name.casefold())
        matches = find_match_level_evidence(name, row.get("candidate_options_json", "[]"), fixtures)
        hint = preferred_search_hint(name, scope)
        if matches:
            status = "match_level_records_correlated"
            source = "; ".join(sorted({m["source"] for m in matches}))
            kind = "independent_match_results"
            url = "; ".join(sorted({m["url"] for m in matches}))
            evidence_scope = "date_opponent_and_all_set_scores_match"
            notes = "Exact date, opponent, and every set score matched an independent public result to a raw DataSportsAPI fixture. Human review is still required."
        elif profile:
            status = "public_profile_name_corroborated"
            source, kind, url = profile["source"], profile["type"], profile["url"]
            evidence_scope, notes = profile["scope"], profile["note"]
        else:
            status = "not_yet_checked"
            source = kind = url = evidence_scope = notes = ""
        audit.append({
            "polymarket_player": name,
            "competition_scope": scope,
            "database_status": row.get("database_status", ""),
            "candidate_count": row.get("candidate_count", ""),
            "candidate_options_json": row.get("candidate_options_json", "[]"),
            "independent_evidence_status": status,
            "evidence_source": source,
            "evidence_type": kind,
            "evidence_url": url,
            "evidence_scope": evidence_scope,
            "matched_fixture_ids": ";".join(sorted({m["fixture_id"] for m in matches})),
            "matched_independent_result_count": len(matches),
            "source_player_id_link_status": "unverified",
            "decision": "HOLD",
            "reviewer_action_required": "Review the linked independent result and exact DataSportsAPI fixture before any manual identity approval.",
            "search_hint": hint,
            "search_url": "https://www.google.com/search?q=" + quote_plus(hint),
            "verification_rule": "Require exact date, opponent and all set scores from an independent result feed. A match-level correlation is evidence for human review, not automatic approval; ambiguous candidates must be disambiguated.",
            "evidence_notes": notes,
        })
    return sorted(audit, key=lambda r: (r["competition_scope"].casefold(), r["polymarket_player"].casefold()))


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Identity review queue missing: {INPUT}")
    with INPUT.open(newline="", encoding="utf-8-sig") as handle:
        queue = list(csv.DictReader(handle))
    fixtures = load_fixtures(RAW)
    rows = build_audit(queue, fixtures)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(row["independent_evidence_status"] for row in rows)
    report = {
        "review_queue_rows": len(rows),
        "match_level_records_correlated": counts["match_level_records_correlated"],
        "public_profile_name_corroborated": counts["public_profile_name_corroborated"],
        "not_yet_checked": counts["not_yet_checked"],
        "source_player_id_links_verified": 0,
        "approved_identities": 0,
        "automatic_identity_merges": 0,
        "matched_independent_result_count": sum(int(row["matched_independent_result_count"]) for row in rows),
        "policy": "Exact independent match-result correlations are surfaced for human review only. Every source_player_id remains unverified and every decision remains HOLD; no identities are automatically approved or merged.",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
