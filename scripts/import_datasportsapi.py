#!/usr/bin/env python3
"""Incrementally import recent DataSportsAPI table-tennis results.

The key is read only from DATASPORTSAPI_KEY. Daily raw snapshots are committed
to the repository so results older than the provider's seven-day API window
remain available on subsequent ephemeral GitHub runners.
"""
import hashlib
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/database/table_tennis.sqlite"
RAW = ROOT / "data/raw/datasportsapi"
BASE = "https://api.datasportsapi.com/v2/fixtures"
SOURCE_KEY = "datasportsapi_table_tennis"
SOURCE_NAME = "DataSportsAPI table-tennis fixtures and results"
SOURCE_URL = "https://datasportsapi.com/sports/table-tennis/"
API_KEY = os.environ.get("DATASPORTSAPI_KEY", "").strip()


def request_page(date, page):
    query = urllib.parse.urlencode({"date": date, "sport": "table-tennis", "page": page})
    req = urllib.request.Request(
        f"{BASE}?{query}",
        headers={"Authorization": f"Bearer {API_KEY}", "Accept": "application/json",
                 "User-Agent": "TableTennisSim/1.0"},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                body = response.read()
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError(f"Unexpected API response envelope for {date} page {page}")
            return payload, hashlib.sha256(body).hexdigest()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            if exc.code in (401, 403):
                raise RuntimeError(f"API authentication/permission error HTTP {exc.code}: {detail}") from exc
            if exc.code == 429 or exc.code >= 500:
                if attempt == 3:
                    raise RuntimeError(f"API request failed HTTP {exc.code}: {detail}") from exc
                time.sleep(10 * (attempt + 1))
            else:
                raise RuntimeError(f"API request failed HTTP {exc.code}: {detail}") from exc
        except (TimeoutError, OSError, json.JSONDecodeError) as exc:
            if attempt == 3:
                raise RuntimeError(f"API request failed after retries: {exc}") from exc
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("Unreachable request retry state")


def table_columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def get_player(conn, source_id, participant):
    if not isinstance(participant, dict) or participant.get("id") is None or not participant.get("name"):
        raise ValueError("Missing provider-native participant id/name")
    source_player_id = str(participant["id"])
    conn.execute(
        """INSERT INTO players(source_id,source_player_id,display_name)
           VALUES(?,?,?) ON CONFLICT(source_id,source_player_id)
           DO UPDATE SET display_name=excluded.display_name""",
        (source_id, source_player_id, participant["name"]),
    )
    return conn.execute(
        "SELECT player_pk FROM players WHERE source_id=? AND source_player_id=?",
        (source_id, source_player_id),
    ).fetchone()[0]


def import_fixture(conn, source_id, fixture):
    if fixture.get("sport") != "table-tennis" or (fixture.get("status") or {}).get("type") != "finished":
        return "skip"
    home, away = fixture.get("home"), fixture.get("away")
    if not home or not away:
        raise ValueError("Finished fixture has unresolved participant")
    hs, aws = fixture.get("homeScore") or {}, fixture.get("awayScore") or {}
    sets_a, sets_b = hs.get("current"), aws.get("current")
    if not isinstance(sets_a, (int, float)) or not isinstance(sets_b, (int, float)):
        raise ValueError("Finished fixture is missing numeric set totals")
    sets_a, sets_b = int(sets_a), int(sets_b)
    if sets_a == sets_b or min(sets_a, sets_b) < 0:
        raise ValueError("Finished fixture has invalid tied/negative set totals")
    winner_side = fixture.get("winner")
    if winner_side not in ("home", "away"):
        winner_side = "home" if sets_a > sets_b else "away"
    if (winner_side == "home") != (sets_a > sets_b):
        raise ValueError("Winner conflicts with final set totals")
    player_a, player_b = get_player(conn, source_id, home), get_player(conn, source_id, away)
    start = fixture.get("startTime")
    if not isinstance(start, str) or len(start) < 10:
        raise ValueError("Finished fixture missing ISO startTime")
    match_date = start[:10]
    match_time = start[11:19] if len(start) >= 19 else None
    competition = (fixture.get("league") or {}).get("name") or "Unknown competition"
    match_id = str(fixture["id"])
    raw = json.dumps(fixture, ensure_ascii=False, sort_keys=True)
    existing = conn.execute(
        "SELECT match_pk FROM matches WHERE source_id=? AND source_match_id=?",
        (source_id, match_id),
    ).fetchone()
    if existing:
        match_pk = existing[0]
        conn.execute(
            """UPDATE matches SET match_date=?,match_time=?,competition=?,player_a_pk=?,
               player_b_pk=?,sets_a=?,sets_b=?,winner_player_pk=?,raw_row_json=?,imported_at=CURRENT_TIMESTAMP
               WHERE match_pk=?""",
            (match_date, match_time, competition, player_a, player_b, sets_a, sets_b,
             player_a if winner_side == "home" else player_b,
             raw, match_pk),
        )
        conn.execute("DELETE FROM match_games WHERE match_pk=?", (match_pk,))
        outcome = "updated"
    else:
        cur = conn.execute(
            """INSERT INTO matches(source_id,source_match_id,match_date,match_time,competition,
               player_a_pk,player_b_pk,sets_a,sets_b,winner_player_pk,raw_row_json)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (source_id, match_id, match_date, match_time, competition, player_a, player_b,
             sets_a, sets_b, player_a if winner_side == "home" else player_b, raw),
        )
        match_pk, outcome = cur.lastrowid, "inserted"
    periods_a, periods_b = hs.get("periods") or {}, aws.get("periods") or {}
    keys = sorted(set(periods_a) & set(periods_b),
                  key=lambda k: int(k[6:]) if k.startswith("period") and k[6:].isdigit() else 999)
    for index, key in enumerate(keys, 1):
        pa, pb = periods_a[key], periods_b[key]
        if isinstance(pa, (int, float)) and isinstance(pb, (int, float)):
            conn.execute(
                "INSERT INTO match_games(match_pk,game_number,points_a,points_b) VALUES(?,?,?,?)",
                (match_pk, index, int(pa), int(pb)),
            )
    return outcome


def main():
    if not API_KEY:
        raise SystemExit("DATASPORTSAPI_KEY secret is missing; no API request was made.")
    if not DB.exists():
        raise SystemExit(f"Database not found at {DB}; run the historical database build first.")
    RAW.mkdir(parents=True, exist_ok=True)
    today = datetime.now(timezone.utc).date()
    dates = [(today - timedelta(days=i)).isoformat() for i in reversed(range(7))]
    calls = 0
    for date in dates:
        pages, page = [], 0
        while True:
            payload, digest = request_page(date, page)
            calls += 1
            pages.append({"page": page, "sha256": digest, "payload": payload})
            meta = payload.get("meta") or {}
            if meta.get("complete") is False:
                raise RuntimeError(f"Provider marked {date} page {page} incomplete; refusing partial import.")
            if not meta.get("hasNextPage", False):
                break
            page += 1
            if page > 99:
                raise RuntimeError(f"Pagination exceeded documented page limit for {date}.")
            time.sleep(6)
        snapshot = {"date": date, "retrieved_at": datetime.now(timezone.utc).isoformat(), "pages": pages}
        path = RAW / f"fixtures_{date}.json"
        path.write_text(json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if date != dates[-1]:
            time.sleep(6)

    # Rebuild from every retained daily snapshot, not just the latest seven-day
    # API window. The workflow commits these files so history survives runners.
    fixtures_by_id = {}
    for path in sorted(RAW.glob("fixtures_????-??-??.json")):
        snapshot = json.loads(path.read_text(encoding="utf-8"))
        for page in snapshot.get("pages", []):
            payload = page.get("payload", {})
            if not isinstance(payload.get("data"), list):
                raise ValueError(f"Malformed retained snapshot: {path}")
            for fixture in payload["data"]:
                if isinstance(fixture, dict) and fixture.get("id") is not None:
                    fixtures_by_id[str(fixture["id"])] = fixture

    snapshot_hashes = []
    for path in sorted(RAW.glob("fixtures_????-??-??.json")):
        snapshot_hashes.append(hashlib.sha256(path.read_bytes()).hexdigest())
    combined_hash = hashlib.sha256("".join(snapshot_hashes).encode()).hexdigest()

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        source_cols = table_columns(conn, "sources")
        source_values = {
            "source_key": SOURCE_KEY, "source_name": SOURCE_NAME, "source_url": SOURCE_URL,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "sha256": combined_hash, "row_count": len(fixtures_by_id),
            "notes": "Free DataSportsAPI plan; provider-native fixture and competitor IDs; daily raw JSON snapshots retained in repository. Terms permit own analysis/products but prohibit raw data redistribution.",
            "license_notes": "DataSportsAPI Terms of Service (2026-11-16): data may be used in own apps/products/analysis; raw data feed resale/redistribution prohibited.",
            "access_notes": "Free plan; 7-day API history; 1,000 requests/day during beta, then 100/day; 10 requests/minute. API key stored in GitHub Actions secret.",
        }
        values = {k: v for k, v in source_values.items() if k in source_cols}
        columns = list(values)
        conn.execute(
            f"INSERT INTO sources({','.join(columns)}) VALUES({','.join('?' for _ in columns)}) "
            f"ON CONFLICT(source_key) DO UPDATE SET " +
            ",".join(f"{k}=excluded.{k}" for k in columns if k != "source_key"),
            [values[k] for k in columns],
        )
        source_id = conn.execute("SELECT source_id FROM sources WHERE source_key=?", (SOURCE_KEY,)).fetchone()[0]
        inserted = updated = skipped = rejected = 0
        for fixture in fixtures_by_id.values():
            try:
                outcome = import_fixture(conn, source_id, fixture)
                if outcome == "inserted": inserted += 1
                elif outcome == "updated": updated += 1
                else: skipped += 1
            except (ValueError, KeyError, TypeError) as exc:
                rejected += 1
                print(f"QUARANTINED fixture {fixture.get('id')}: {exc}")
        if rejected:
            raise RuntimeError(f"{rejected} malformed finished fixture(s); transaction rolled back for review.")
        log_cols = table_columns(conn, "import_log")
        log_values = {
            "source_id": source_id, "filename": f"DataSportsAPI {len(dates)}-day refresh",
            "sha256": combined_hash, "file_sha256": combined_hash,
            "imported_at": datetime.now(timezone.utc).isoformat(),
            "rows_seen": len(fixtures_by_id), "rows_loaded": inserted + updated,
            "status": "success", "notes": f"{calls} API calls; {len(snapshot_hashes)} retained daily snapshots; {inserted} inserted; {updated} updated; {skipped} non-finished/other-sport rows skipped; {rejected} quarantined.",
        }
        lv = {k: v for k, v in log_values.items() if k in log_cols}
        lc = list(lv)
        conn.execute(f"INSERT INTO import_log({','.join(lc)}) VALUES({','.join('?' for _ in lc)})",
                     [lv[k] for k in lc])
        conn.commit()
        print(json.dumps({"provider": SOURCE_KEY, "dates_refreshed": dates, "api_calls": calls,
                          "retained_daily_snapshots": len(snapshot_hashes), "fixtures_seen": len(fixtures_by_id),
                          "inserted": inserted, "updated": updated, "skipped": skipped, "rejected": rejected,
                          "database_integrity": conn.execute("PRAGMA integrity_check").fetchone()[0]},
                         indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
