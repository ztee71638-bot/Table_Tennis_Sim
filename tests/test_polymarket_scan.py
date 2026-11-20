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

    def test_requires_explicit_table_tennis_tag(self):
        self.assertTrue(MODULE.is_table_tennis_event({
            "tags": [{"slug": "table-tennis", "label": "Table Tennis"}]
        }))
        self.assertFalse(MODULE.is_table_tennis_event({
            "tags": [{"slug": "tennis", "label": "Tennis"}]
        }))
        self.assertFalse(MODULE.is_table_tennis_event({
            "tags": [{"slug": "ebattles", "label": "eBattles"}]
        }))

    def test_exact_database_match_ignores_name_order(self):
        self.assertEqual(
            MODULE.find_database_match("Jingkun Liang", ["LIANG Jingkun", "Wang Chuqin"]),
            ("exact_name_match_order_insensitive", "LIANG Jingkun", 1.0),
        )

    def test_initial_abbreviation_is_review_only(self):
        status, candidate, score = MODULE.find_database_match(
            "Dukhovenko Oleksandr", ["Dukhovenko O.", "Wang Chuqin"]
        )
        self.assertEqual(status, "possible_name_match_review_only")
        self.assertEqual(candidate, "Dukhovenko O.")
        self.assertGreaterEqual(score, 0.90)

    def test_typo_is_review_only(self):
        status, candidate, score = MODULE.find_database_match(
            "Fan Zhendongg", ["Fan Zhendong", "Wang Chuqin"]
        )
        self.assertEqual(status, "possible_name_match_review_only")
        self.assertEqual(candidate, "Fan Zhendong")
        self.assertGreaterEqual(score, 0.90)


if __name__ == "__main__":
    unittest.main()
