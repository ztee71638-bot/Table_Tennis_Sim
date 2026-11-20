import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reconcile_polymarket_players.py"
SPEC = importlib.util.spec_from_file_location("reconcile_polymarket", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReconcilePolymarketTests(unittest.TestCase):
    def test_name_order_and_initial_match(self):
        self.assertEqual(MODULE.normalized_tokens_match("Erik Mares", "Mares E."), "initial")
        self.assertEqual(MODULE.normalized_tokens_match("Ganghyeon Park", "PARK Ganghyeon"), "exact")

    def test_initial_match_requires_same_surname_token(self):
        self.assertIsNone(MODULE.normalized_tokens_match("Patrik Pycha", "Peter P."))
        self.assertIsNone(MODULE.normalized_tokens_match("Daniel Tuma", "Tuma J."))

    def test_numeric_birth_year_does_not_block_name_match(self):
        self.assertEqual(
            MODULE.normalized_tokens_match("Jaroslav (1964) Strnad", "Strnad J."),
            "initial",
        )

    def test_competition_scope_maps_setka_variant(self):
        event = {
            "tags": [
                {"label": "Table Tennis", "slug": "table-tennis"},
                {"label": "Setka Cup Moldova Men", "league": {"name": "Setka Cup Moldova Men"}},
            ]
        }
        self.assertEqual(MODULE.event_competition(event), "Setka Cup")

    def test_player_history_is_aggregated_not_last_match_only(self):
        history = [
            {"a_id": "1", "a_name": "Mares E.", "b_id": "2", "b_name": "Pilch J.",
             "competition": "Czech Liga Pro", "match_date": "2026-11-18",
             "winner_player_pk": 1, "a_pk": 1, "b_pk": 2},
            {"a_id": "1", "a_name": "Mares E.", "b_id": "3", "b_name": "Franek T.",
             "competition": "Czech Liga Pro", "match_date": "2026-11-19",
             "winner_player_pk": 3, "a_pk": 1, "b_pk": 3},
        ]
        candidates = MODULE.player_candidates("Erik Mares", history, "Czech Liga Pro")
        self.assertEqual(len(candidates), 1)
        self.assertEqual(len(candidates[0]["matches"]), 2)
        self.assertEqual(len(candidates[0]["relevant_matches"]), 2)

    def test_matchup_report_adds_h2h_evidence_without_auto_merge(self):
        history = [{
            "a_id": "1", "a_name": "Mares E.", "b_id": "2", "b_name": "Pilch J.",
            "competition": "Czech Liga Pro", "match_date": "2026-11-18",
            "match_time": "12:00:00", "source_match_id": "m1",
            "sets_a": 3, "sets_b": 1, "winner_player_pk": 1, "a_pk": 1, "b_pk": 2,
        }]
        events = [{
            "id": "e1", "title": "Erik Mares vs. Jakub Pilch",
            "startTime": "2026-11-20T22:00:00Z",
            "tags": [{"label": "Czech Liga Pro", "league": {"name": "Czech Liga Pro"}}],
        }]
        players, matchups, counts = MODULE.reconcile(events, history, {"available": True})
        self.assertEqual(counts["matchups_with_historical_h2h"], 1)
        self.assertEqual(matchups[0]["historical_h2h_matches_in_competition"], 1)
        self.assertIn("no automatic", matchups[0]["identity_decision"])
        self.assertEqual(len(players), 2)

    def test_missing_source_does_not_claim_not_found(self):
        events = [{"title": "Erik Mares vs. Jakub Pilch"}]
        _, matchups, _ = MODULE.reconcile(events, [], {"available": False})
        self.assertEqual(matchups[0]["player_a_status"], "source_not_loaded")


if __name__ == "__main__":
    unittest.main()
