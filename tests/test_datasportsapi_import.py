import importlib.util
import sqlite3
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_datasportsapi.py"
SPEC = importlib.util.spec_from_file_location("datasportsapi_import", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_database():
    conn = sqlite3.connect(":memory:")
    conn.executescript("""
        CREATE TABLE sources (source_id INTEGER PRIMARY KEY, source_key TEXT UNIQUE);
        INSERT INTO sources(source_id, source_key) VALUES (1, 'datasportsapi_table_tennis');
        CREATE TABLE players (
            player_pk INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            source_player_id TEXT NOT NULL,
            display_name TEXT NOT NULL,
            UNIQUE(source_id, source_player_id)
        );
        CREATE TABLE matches (
            match_pk INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL,
            source_match_id TEXT NOT NULL,
            match_date TEXT,
            match_time TEXT,
            competition TEXT,
            player_a_pk INTEGER,
            player_b_pk INTEGER,
            sets_a INTEGER,
            sets_b INTEGER,
            winner_player_pk INTEGER,
            raw_row_json TEXT,
            imported_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_id, source_match_id)
        );
        CREATE TABLE match_games (
            match_pk INTEGER NOT NULL,
            game_number INTEGER NOT NULL,
            points_a INTEGER,
            points_b INTEGER,
            UNIQUE(match_pk, game_number)
        );
    """)
    return conn


def fixture(**overrides):
    value = {
        "id": 901,
        "sport": "table-tennis",
        "status": {"type": "finished"},
        "home": {"id": 101, "name": "Player Alpha"},
        "away": {"id": 202, "name": "Player Beta"},
        "homeScore": {"current": 3, "periods": {
            "period1": 11, "period2": 8, "period3": 11, "period4": 11
        }},
        "awayScore": {"current": 1, "periods": {
            "period1": 7, "period2": 11, "period3": 9, "period4": 6
        }},
        "winner": "home",
        "startTime": "2026-11-19T10:30:00Z",
        "league": {"name": "Czech Liga Pro"},
    }
    value.update(overrides)
    return value


class DataSportsAPIImportTests(unittest.TestCase):
    def test_normalizes_copy_paste_transport_artifacts(self):
        self.assertEqual(MODULE.normalize_api_key('\ufeff  “abc123”  '), "abc123")
        self.assertEqual(MODULE.normalize_api_key("  abc123  "), "abc123")

    def test_imports_completed_fixture_and_game_scores(self):
        conn = make_database()
        outcome = MODULE.import_fixture(conn, 1, fixture())
        self.assertEqual(outcome, "inserted")
        match = conn.execute(
            "SELECT match_date, match_time, competition, sets_a, sets_b, winner_player_pk "
            "FROM matches"
        ).fetchone()
        self.assertEqual(match[:5], ("2026-11-19", "10:30:00", "Czech Liga Pro", 3, 1))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM players").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM match_games").fetchone()[0], 4)
        conn.close()

    def test_reimport_updates_existing_fixture_without_duplicate(self):
        conn = make_database()
        self.assertEqual(MODULE.import_fixture(conn, 1, fixture()), "inserted")
        changed = fixture(
            homeScore={"current": 3, "periods": {
                "period1": 11, "period2": 8, "period3": 11, "period4": 7, "period5": 11
            }},
            awayScore={"current": 2, "periods": {
                "period1": 7, "period2": 11, "period3": 9, "period4": 11, "period5": 6
            }},
        )
        self.assertEqual(MODULE.import_fixture(conn, 1, changed), "updated")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT sets_a, sets_b FROM matches").fetchone(), (3, 2))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM match_games").fetchone()[0], 5)
        conn.close()

    def test_skips_unfinished_or_other_sport_fixture(self):
        conn = make_database()
        self.assertEqual(
            MODULE.import_fixture(conn, 1, fixture(status={"type": "inprogress"})),
            "skip",
        )
        self.assertEqual(
            MODULE.import_fixture(conn, 1, fixture(sport="football")),
            "skip",
        )
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0], 0)
        conn.close()

    def test_rejects_winner_conflicting_with_set_totals(self):
        conn = make_database()
        with self.assertRaisesRegex(ValueError, "Winner conflicts"):
            MODULE.import_fixture(conn, 1, fixture(winner="away"))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0], 0)
        conn.close()

    def test_rejects_tied_final_set_totals(self):
        conn = make_database()
        with self.assertRaisesRegex(ValueError, "invalid tied"):
            MODULE.import_fixture(conn, 1, fixture(
                homeScore={"current": 2, "periods": {}},
                awayScore={"current": 2, "periods": {}},
            ))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM matches").fetchone()[0], 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
