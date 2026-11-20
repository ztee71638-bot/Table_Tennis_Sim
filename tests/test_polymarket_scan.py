import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "scan_polymarket_table_tennis.py"
SPEC = importlib.util.spec_from_file_location("polymarket_scan", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PolymarketScanTests(unittest.TestCase):
    def test_normalizes_names(self):
        self.assertEqual(MODULE.norm_name("  Wang, Chuqin  "), "wang chuqin")

    def test_extracts_player_pair(self):
        self.assertEqual(
            MODULE.extract_player_pair("Wang Chuqin vs. Fan Zhendong"),
            ("Wang Chuqin", "Fan Zhendong"),
        )

    def test_does_not_guess_pair_without_separator(self):
        self.assertEqual(MODULE.extract_player_pair("WTT Champions Men's Singles"), (None, None))

    def test_exact_database_match(self):
        self.assertEqual(
            MODULE.find_database_match("Fan Zhendong", ["Fan Zhendong", "Wang Chuqin"]),
            ("exact", "Fan Zhendong", 1.0),
        )

    def test_near_match_is_review_only(self):
        status, candidate, score = MODULE.find_database_match(
            "Fan Zhendongg", ["Fan Zhendong", "Wang Chuqin"]
        )
        self.assertEqual(status, "possible_name_match_review_only")
        self.assertEqual(candidate, "Fan Zhendong")
        self.assertGreaterEqual(score, 0.90)


if __name__ == "__main__":
    unittest.main()
