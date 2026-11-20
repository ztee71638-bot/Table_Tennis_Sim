#!/usr/bin/env python3
"""Import the licensed WTT men's and women's CSVs into the shared SQLite schema."""
import csv, hashlib, io, json, sqlite3, urllib.request, zipfile
from datetime import datetime, timezone
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw"
DB = ROOT / "data/database/table_tennis.sqlite"
URL = "https://osf.io/download/3f6ak/"
EXPECTED_ARCHIVE_SHA256 = "5246b5fe1ba5d1d71edcef0e23ef0ee93d7289508dd0545fc124ed569f991409"


def download_archive(url, attempts=4):
    """Download the OSF archive with a long timeout and bounded retries."""
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "TableTennisSim/1.0",
                "Accept": "application/zip, application/octet-stream, */*",
            })
            with urllib.request.urlopen(req, timeout=300) as response:
                data = response.read()
            if not data:
                raise IOError("OSF returned an empty archive")
            actual = hashlib.sha256(data).hexdigest()
            if actual != EXPECTED_ARCHIVE_SHA256:
                raise ValueError(f"OSF archive checksum mismatch: {actual}")
            return data
        except (TimeoutError, OSError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = min(15 * (2 ** (attempt - 1)), 120)
            print(f"OSF download attempt {attempt}/{attempts} failed: {exc}; retrying in {delay}s", flush=True)
            time.sleep(delay)
    raise RuntimeError(f"Could not download verified OSF archive after {attempts} attempts: {last_error}")
FILES = {
    "wtt_men_2022_2025": ("table_tennis_wtt_men_std.csv", "WTT men's matches 2022-2025"),
    "wtt_women_2022_2025": ("table_tennis_wtt_women_std.csv", "WTT women's matches 2022-2025"),
}

def get_player(c, sid, pid, name):
    c.execute("""INSERT INTO players(source_id,source_player_id,display_name)
                 VALUES(?,?,?) ON CONFLICT(source_id,source_player_id)
                 DO UPDATE SET display_name=excluded.display_name""", (sid, str(pid), name))
    return c.execute("SELECT player_pk FROM players WHERE source_id=? AND source_player_id=?",
                     (sid, str(pid))).fetchone()[0]

def player_source_id(row, side, filename):
    # Men have source-provided IDs. The women's file has no ID columns, so
    # use a deterministic source-local key from the displayed name + country.
    raw_id_col = "a_id_raw" if side == 1 else "x_id_raw"
    name_col = "player1_name" if side == 1 else "player2_name"
    country_col = "player1_country" if side == 1 else "player2_country"
    if raw_id_col in row and row[raw_id_col].strip():
        return row[raw_id_col].strip()
    name = row[name_col].strip()
    country = row[country_col].strip()
    if not name or not country:
        raise ValueError(f"Cannot construct source-local player key for {name_col}/{country_col}")
    return f"name:{name}|country:{country}"

def main():
    RAW.mkdir(parents=True, exist_ok=True)
    DB.parent.mkdir(parents=True, exist_ok=True)
    archive = download_archive(URL)
    z = zipfile.ZipFile(io.BytesIO(archive))
    c = sqlite3.connect(DB)
    c.execute("PRAGMA foreign_keys=ON")
    try:
        for key, (filename, label) in FILES.items():
            data = z.read(filename)
            (RAW / filename).write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            rows = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
            expected_rows = 5442 if "_men_" in filename else 4850
            if len(rows) != expected_rows:
                raise ValueError(f"{filename}: expected {expected_rows}, got {len(rows)}")
            notes = ("CC BY 4.0; OSF DOI 10.17605/OSF.IO/PJUW8; men's source-native IDs retained."
                     if "_men_" in filename else
                     "CC BY 4.0; OSF DOI 10.17605/OSF.IO/PJUW8; women's file has no player ID columns; deterministic source-local keys use displayed name + country. No cross-source identity merging.")
            c.execute("""INSERT INTO sources(source_key,source_name,source_url,retrieved_at,sha256,row_count,notes)
              VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_key) DO UPDATE SET source_name=excluded.source_name,
              source_url=excluded.source_url,retrieved_at=excluded.retrieved_at,sha256=excluded.sha256,
              row_count=excluded.row_count,notes=excluded.notes""",
              (key, label, URL, datetime.now(timezone.utc).isoformat(), digest, len(rows), notes))
            sid = c.execute("SELECT source_id FROM sources WHERE source_key=?", (key,)).fetchone()[0]
            c.execute("DELETE FROM raw_import_rows WHERE source_id=?", (sid,))
            c.execute("DELETE FROM matches WHERE source_id=?", (sid,))
            c.execute("""DELETE FROM players WHERE source_id=?
                         AND player_pk NOT IN
                         (SELECT player_pk_a FROM identity_links UNION SELECT player_pk_b FROM identity_links)""",
                      (sid,))
            source_player_ids = set()
            for n, row in enumerate(rows, 1):
                payload = json.dumps(row, ensure_ascii=False, sort_keys=True)
                c.execute("INSERT INTO raw_import_rows(source_id,row_number,payload_json) VALUES(?,?,?)",
                          (sid, n, payload))
                aid = player_source_id(row, 1, filename)
                bid = player_source_id(row, 2, filename)
                source_player_ids.update((aid, bid))
                a = get_player(c, sid, aid, row["player1_name"])
                b = get_player(c, sid, bid, row["player2_name"])
                games = []
                for part in row["score"].split(","):
                    bits = part.strip().split("-")
                    if len(bits) == 2:
                        try:
                            games.append((int(bits[0]), int(bits[1])))
                        except ValueError:
                            pass
                sa = sum(x > y for x, y in games)
                sb = sum(y > x for x, y in games)
                winner = a if row["winner"] == "1" else b if row["winner"] == "2" else None
                mid = row["match_id"]
                c.execute("""INSERT INTO matches(source_id,source_match_id,match_date,competition,
                  player_a_pk,player_b_pk,sets_a,sets_b,winner_player_pk,raw_row_json)
                  VALUES(?,?,?,?,?,?,?,?,?,?)""",
                  (sid, mid, row["event_date"], row["event_name"], a, b, sa, sb, winner, payload))
                mpk = c.execute("SELECT last_insert_rowid()").fetchone()[0]
                for i, (pa, pb) in enumerate(games, 1):
                    c.execute("INSERT INTO match_games(match_pk,game_number,points_a,points_b) VALUES(?,?,?,?)",
                              (mpk, i, pa, pb))
            c.execute("""INSERT INTO import_log(source_id,filename,sha256,imported_at,rows_seen,rows_loaded,status,notes)
              VALUES(?,?,?,?,?,?,?,?)""",
              (sid, filename, digest, datetime.now(timezone.utc).isoformat(), len(rows), len(rows),
               "success", "Rows preserved; set and game scores parsed from score field."))
            print(f"{key}: {len(rows)} matches loaded; {len(source_player_ids)} source player IDs")
        c.commit()
    except:
        c.rollback()
        raise
    finally:
        c.close()

if __name__ == "__main__":
    main()
