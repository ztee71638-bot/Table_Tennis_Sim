#!/usr/bin/env python3
"""Build an evidence-led audit for unresolved Polymarket player identities.

Public profiles can corroborate a displayed name, but do not by themselves prove
that a DataSportsAPI source_player_id belongs to that person. No links are approved.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/polymarket_identity_review_queue.csv"
OUTPUT = ROOT / "data/processed/polymarket_identity_evidence_audit.csv"
REPORT = ROOT / "data/processed/polymarket_identity_evidence_report.json"

# Independent public biographies for the three WTT names in the current queue.
# These confirm the public player's name only; they do not expose DataSportsAPI IDs.
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

FIELDS = [
    "polymarket_player", "competition_scope", "database_status",
    "candidate_count", "candidate_options_json", "independent_evidence_status",
    "evidence_source", "evidence_type", "evidence_url", "evidence_scope",
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


def build_audit(rows: list[dict]) -> list[dict]:
    audit = []
    for row in rows:
        name = row.get("polymarket_player", "").strip()
        scope = row.get("competition_scope", "").strip()
        evidence = PUBLIC_PROFILE_EVIDENCE.get(name.casefold())
        hint = preferred_search_hint(name, scope)
        if evidence:
            status = "public_profile_name_corroborated"
            source, kind, url = evidence["source"], evidence["type"], evidence["url"]
            evidence_scope, notes = evidence["scope"], evidence["note"]
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
            "source_player_id_link_status": "unverified",
            "decision": "HOLD",
            "reviewer_action_required": "Compare candidate match dates, opponents and scores against an independent official competition result before linking this source ID.",
            "search_hint": hint,
            "search_url": "https://www.google.com/search?q=" + quote_plus(hint),
            "verification_rule": "A profile/name match is not sufficient to approve a source ID. Require independent competition-result linkage; ambiguous candidates require disambiguation.",
            "evidence_notes": notes,
        })
    return sorted(audit, key=lambda r: (r["competition_scope"].casefold(), r["polymarket_player"].casefold()))


def main() -> None:
    if not INPUT.exists():
        raise FileNotFoundError(f"Identity review queue missing: {INPUT}")
    with INPUT.open(newline="", encoding="utf-8-sig") as handle:
        queue = list(csv.DictReader(handle))
    rows = build_audit(queue)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(row["independent_evidence_status"] for row in rows)
    report = {
        "review_queue_rows": len(rows),
        "public_profile_name_corroborated": counts["public_profile_name_corroborated"],
        "not_yet_checked": counts["not_yet_checked"],
        "source_player_id_links_verified": 0,
        "approved_identities": 0,
        "automatic_identity_merges": 0,
        "policy": "Public biographies corroborate names only. Every source_player_id remains unverified and every decision remains HOLD until independent match-level evidence is reviewed.",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
