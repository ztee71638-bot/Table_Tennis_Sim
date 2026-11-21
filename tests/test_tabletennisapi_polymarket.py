import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "enrich_polymarket_tabletennisapi.py"
SPEC = importlib.util.spec_from_file_location("tabletennisapi_polymarket", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TableTennisApiDiscoveryTests(unittest.TestCase):
    def test_full_name_tokens_match_in_either_order(self):
        self.assertEqual(MODULE.name_match_type("Yuanyu Chen", "Chen Yuanyu"), "exact")

    def test_provider_search_uses_a_distinctive_name_token(self):
        self.assertEqual(MODULE.search_term("Yuanyu Chen"), "yuanyu")

    def test_accents_are_normalized(self):
        self.assertEqual(MODULE.name_match_type("Felix Lebrun", "Félix Lebrun"), "exact")

    def test_unique_initial_is_review_only(self):
        self.assertEqual(MODULE.name_match_type("Erik Mares", "Mares E."), "initial")

    def test_ambiguous_exact_candidates_are_not_selected(self):
        status, candidate, possible = MODULE.select_candidate(
            "Yuanyu Chen",
            [{"id": "pl_aaaa1111", "name": "Chen Yuanyu"},
             {"id": "pl_bbbb2222", "name": "Yuanyu Chen"}],
        )
        self.assertEqual(status, "ambiguous")
        self.assertIsNone(candidate)
        self.assertEqual(len(possible), 2)

    def test_unique_exact_candidate_selected(self):
        status, candidate, _ = MODULE.select_candidate(
            "Yuanyu Chen", [{"id": "pl_aaaa1111", "name": "Chen Yuanyu", "country": "CHN"}]
        )
        self.assertEqual(status, "exact_unique")
        self.assertEqual(candidate["id"], "pl_aaaa1111")

    def test_profile_summary_contains_aggregate_records_only(self):
        result = MODULE.profile_summary(
            "Yuanyu Chen",
            {"id": "pl_aaaa1111", "name": "Chen Yuanyu", "country": "CHN"},
            {
                "id": "pl_aaaa1111", "name": "Chen Yuanyu", "country": "CHN",
                "born": "2000-01-01", "hand": "right", "height_cm": 180,
                "record": [{"discipline": "MS", "played": 30, "won": 22, "lost": 8,
                            "first": "2025-01-01", "last": "2026-11-20"}],
                "world_ranks": [{"discipline": "MS", "list": "senior", "rank": 9,
                                 "points": 1200, "week": "2026-46"}],
            },
            "2026-11-20T12:00:00+00:00",
        )
        self.assertEqual(result["records_by_discipline"][0]["won"], 22)
        self.assertEqual(result["world_ranks"][0]["rank"], 9)
        self.assertNotIn("born", result)
        self.assertNotIn("hand", result)
        self.assertNotIn("height_cm", result)
        self.assertFalse(result["model_eligible"])

    def test_temporary_rate_limit_is_not_cached_as_fresh(self):
        record = {"status": "provider_rate_limited", "looked_up_at_utc": "2026-11-20T12:00:00+00:00"}
        self.assertFalse(MODULE.is_fresh(record, datetime(2026, 11, 20, 13, tzinfo=timezone.utc)))


if __name__ == "__main__":
    unittest.main()
