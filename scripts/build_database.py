#!/usr/bin/env python3
"""
Download the two identified public CSV samples and build a local SQLite database.

Usage:
  python scripts/build_database.py

Requires Python 3.9+ and internet access. Uses only the Python standard library.
The script preserves every source row in raw_import_rows before attempting normalization.
It does not merge player identities across sources.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB_DIR = ROOT / "data" / "database"
DB_PATH = DB_DIR / "table_tennis.sqlite"

SOURCES = [
    {
        "key": "score_setka_2022",
        "name": "SCORE Setka Cup CSV",
        "url": "https://raw.githubusercontent.com/SCOREnetworkorg/sports-data-repository/main/data/table_tennis-sept2022.csv",
        "filename": "table_tennis-sept2022.csv",
        "kind": "named",
    },
    {
        "key": "lathise_elo_sample",
        "name": "Lathise public Elo sample",
        "url": "https://huggingface.co/datasets/lathise/table-tennis-pre-match-elo-ratings/resolve/main/tt_ratings_sample_2000.csv",
        "filename": "tt_ratings_sample_2000.csv",
        "kind": "elo",
    },
]

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS sources (
  source_id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  source_name TEXT NOT NULL,
  source_url TEXT NOT NULL,
  retrieved_at TEXT,
  sha256 TEXT,
  row_count INTEGER,
  notes TEXT
);
CREATE TABLE IF NOT EXISTS players (
  player_pk INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_player_id TEXT NOT NULL,
  display_name TEXT,
  UNIQUE(source_id, source_player_id)
);
CREATE TABLE IF NOT EXISTS matches (
  match_pk INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  source_match_id TEXT,
  match_date TEXT,
  match_time TEXT,
  competition TEXT,
  player_a_pk INTEGER REFERENCES players(player_pk),
  player_b_pk INTEGER REFERENCES players(player_pk),
  sets_a INTEGER,
  sets_b INTEGER,
  winner_player_pk INTEGER REFERENCES players(player_pk),
  raw_row_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS match_games (
  game_pk INTEGER PRIMARY KEY,
  match_pk INTEGER NOT NULL REFERENCES matches(match_pk) ON DELETE CASCADE,
  game_number INTEGER NOT NULL,
  points_a INTEGER,
  points_b INTEGER,
  UNIQUE(match_pk, game_number)
);
CREATE TABLE IF NOT EXISTS elo_observations (
  observation_pk INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  match_id TEXT,
  match_date TEXT,
  competition TEXT,
  player_a_id TEXT,
  player_b_id TEXT,
  elo_a_pre REAL,
  elo_b_pre REAL,
  solidity_a_pre REAL,
  solidity_b_pre REAL,
  model_probability_a REAL,
  winner TEXT,
  sets_a INTEGER,
  sets_b INTEGER,
  raw_row_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS raw_import_rows (
  raw_row_pk INTEGER PRIMARY KEY,
  source_id INTEGER NOT NULL REFERENCES sources(source_id),
  row_number INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  UNIQUE(source_id, row_number)
);
CREATE TABLE IF NOT EXISTS identity_links (
  identity_link_pk INTEGER PRIMARY KEY,
  player_pk_a INTEGER NOT NULL REFERENCES players(player_pk),
  player_pk_b INTEGER NOT NULL REFERENCES players(player_pk),
  proposed_name TEXT,
  status TEXT NOT NULL DEFAULT 'candidate'
    CHECK(status IN ('candidate','verified','rejected')),
  evidence_json TEXT,
  CHECK(player_pk_a <> player_pk_b),
  UNIQUE(player_pk_a, player_pk_b)
);
CREATE TABLE IF NOT EXISTS import_log (
  import_pk INTEGER PRIMARY KEY,
  source_id INTEGER REFERENCES sources(source_id),
  filename TEXT NOT NULL,
  sha256 TEXT,
  imported_at TEXT NOT NULL,
  rows_seen INTEGER,
  rows_loaded INTEGER,
  status TEXT NOT NULL,
  notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
CREATE INDEX IF NOT EXISTS idx_matches_competition ON matches(competition);
CREATE INDEX IF NOT EXISTS idx_elo_date ON elo_observations(match_date);
"""

def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "TableTennisSim-DataImporter/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()

def norm_key(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())

def get(row: dict, *names: str):
    lookup = {norm_key(k): v for k, v in row.items()}
    for name in names:
        value = lookup.get(norm_key(name))
        if value not in (None, ""):
            return value
    return None

def as_int(value):
    try:
        return int(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None

def as_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None

def player_id(conn, source_id, source_player_id, display_name=None):
    if source_player_id in (None, ""):
        return None
    source_player_id = str(source_player_id)
    conn.execute(
        """INSERT INTO players(source_id,source_player_id,display_name)
           VALUES(?,?,?)
           ON CONFLICT(source_id,source_player_id) DO UPDATE SET
             display_name=COALESCE(players.display_name, excluded.display_name)""",
        (source_id, source_player_id, display_name),
    )
    return conn.execute(
        "SELECT player_pk FROM players WHERE source_id=? AND source_player_id=?",
        (source_id, source_player_id),
    ).fetchone()[0]

def load_source(conn, source, raw_bytes):
    digest = hashlib.sha256(raw_bytes).hexdigest()
    retrieved = datetime.now(timezone.utc).isoformat()
    text_data = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text_data))
    rows = list(reader)
    if not reader.fieldnames:
        raise ValueError(f"No CSV header found for {source['filename']}")
    conn.execute(
        """INSERT INTO sources(source_key,source_name,source_url,retrieved_at,sha256,row_count)
           VALUES(?,?,?,?,?,?)
           ON CONFLICT(source_key) DO UPDATE SET
             source_name=excluded.source_name, source_url=excluded.source_url,
             retrieved_at=excluded.retrieved_at, sha256=excluded.sha256,
             row_count=excluded.row_count""",
        (source["key"], source["name"], source["url"], retrieved, digest, len(rows)),
    )
    source_id = conn.execute(
        "SELECT source_id FROM sources WHERE source_key=?", (source["key"],)
    ).fetchone()[0]

    # Rebuild this source's imported rows deterministically on each run.
    conn.execute("DELETE FROM raw_import_rows WHERE source_id=?", (source_id,))
    conn.execute("DELETE FROM matches WHERE source_id=?", (source_id,))
    conn.execute("DELETE FROM elo_observations WHERE source_id=?", (source_id,))
    conn.execute("DELETE FROM players WHERE source_id=? AND player_pk NOT IN "
                 "(SELECT player_pk_a FROM identity_links UNION SELECT player_pk_b FROM identity_links)",
                 (source_id,))

    for number, row in enumerate(rows, start=1):
        payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
        conn.execute(
            "INSERT INTO raw_import_rows(source_id,row_number,payload_json) VALUES(?,?,?)",
            (source_id, number, payload),
        )
        if source["kind"] == "elo":
            conn.execute(
                """INSERT INTO elo_observations(
                    source_id,match_id,match_date,competition,player_a_id,player_b_id,
                    elo_a_pre,elo_b_pre,solidity_a_pre,solidity_b_pre,
                    model_probability_a,winner,sets_a,sets_b,raw_row_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    source_id,
                    get(row, "match_id"),
                    get(row, "date", "match_date"),
                    get(row, "league", "competition"),
                    get(row, "player_a"),
                    get(row, "player_b"),
                    as_float(get(row, "elo_a_pre")),
                    as_float(get(row, "elo_b_pre")),
                    as_float(get(row, "sol_a_pre", "solidity_a_pre")),
                    as_float(get(row, "sol_b_pre", "solidity_b_pre")),
                    as_float(get(row, "p_model", "model_probability_a")),
                    get(row, "winner"),
                    as_int(get(row, "sets_a")),
                    as_int(get(row, "sets_b")),
                    payload,
                ),
            )
        else:
            name_a = get(row, "Player1", "player1", "player_a", "Player A")
            name_b = get(row, "Player2", "player2", "player_b", "Player B")
            # Source row number is used as a source-scoped fallback match key.
            match_id = get(row, "match_id", "id") or str(number)
            pa = player_id(conn, source_id, name_a, name_a)
            pb = player_id(conn, source_id, name_b, name_b)
            sets_a = as_int(get(row, "Sets_P1", "sets_p1", "sets_a", "Player1_sets"))
            sets_b = as_int(get(row, "Sets_P2", "sets_p2", "sets_b", "Player2_sets"))
            winner = None
            if pa is not None and pb is not None and sets_a is not None and sets_b is not None:
                winner = pa if sets_a > sets_b else pb if sets_b > sets_a else None
            match_pk = conn.execute(
                """INSERT INTO matches(
                    source_id,source_match_id,match_date,match_time,competition,
                    player_a_pk,player_b_pk,sets_a,sets_b,winner_player_pk,raw_row_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    source_id, str(match_id),
                    get(row, "Date", "match_date", "date"),
                    get(row, "Time", "match_time", "time"),
                    get(row, "League", "competition", "tournament"),
                    pa, pb, sets_a, sets_b, winner, payload,
                ),
            ).lastrowid
            for game_no in range(1, 6):
                p1 = as_int(get(row, f"P1_G{game_no}", f"Player1_G{game_no}", f"game{game_no}_p1"))
                p2 = as_int(get(row, f"P2_G{game_no}", f"Player2_G{game_no}", f"game{game_no}_p2"))
                if p1 is not None or p2 is not None:
                    conn.execute(
                        "INSERT INTO match_games(match_pk,game_number,points_a,points_b) VALUES(?,?,?,?)",
                        (match_pk, game_no, p1, p2),
                    )

    conn.execute(
        """INSERT INTO import_log(source_id,filename,sha256,imported_at,rows_seen,rows_loaded,status,notes)
           VALUES(?,?,?,?,?,?,?,?)""",
        (source_id, source["filename"], digest, retrieved, len(rows), len(rows), "success",
         "All source rows preserved; normalized fields populated where recognized."),
    )
    return {"source": source["key"], "rows": len(rows), "sha256": digest, "headers": reader.fieldnames}

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA)
        reports = []
        for source in SOURCES:
            path = RAW / source["filename"]
            data = fetch(source["url"])
            path.write_bytes(data)
            reports.append(load_source(conn, source, data))
        conn.commit()
        print(json.dumps({"database": str(DB_PATH), "imports": reports}, indent=2))
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
