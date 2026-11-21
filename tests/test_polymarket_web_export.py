import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_polymarket_web_data.py"
SPEC = importlib.util.spec_from_file_location("export_polymarket_web_data", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def match(a_id="101", a_name="Erik Mares", a_pk=1, b_id="202", b_name="Jakub Pilch", b_pk=2,
          date="2026-11-19", winner=1):
    return {
        "a_id": a_id, "a_name": a_name, "a_pk": a_pk,
        "b_id": b_id, "b_name": b_name, "b_pk": b_pk,
        "competition": "Czech Liga Pro", "match_date": date, "match_time": "12:00:00",
        "winner_player_pk": winner, "sets_a": 3, "sets_b": 1,
    }


class PolymarketWebExportTests(unittest.TestCase):
    def test_wtt_model_lookup_matches_reordered_full_name_tokens(self):
        pools = {"wtt_mens_singles": {"123": {
            "display_name": "Chen Yuanyu", "matches": 24, "last_date": "2026-11-20",
            "recent_form_last10": [1, 1, 0, 1],
        }}}
        result = MODULE.wtt_model_record("Yuanyu Chen", pools, "WTT")
        self.assertEqual(result["status"], "wtt_model_record_identity_unverified")
        self.assertEqual(result["source_player_id"], "123")
        self.assertEqual(result["matches"], 24)

    def test_wtt_model_lookup_is_not_used_for_domestic_competitions(self):
        pools = {"wtt_mens_singles": {"123": {"display_name": "Chen Yuanyu"}}}
        self.assertEqual(MODULE.wtt_model_record("Yuanyu Chen", pools, "Setka Cup")["status"], "not_applicable")

    def test_ambiguous_wtt_model_name_candidates_are_withheld(self):
        pools = {
            "wtt_mens_singles": {"123": {"display_name": "Chen Yuanyu"}},
            "wtt_womens_singles": {"456": {"display_name": "Yuanyu Chen"}},
        }
        self.assertEqual(MODULE.wtt_model_record("Yuanyu Chen", pools, "WTT")["status"], "ambiguous")

    def test_tabletennisapi_profile_attaches_exact_name_profile(self):
        profile = {"status": "exact_name_match_identity_unverified", "source_player_id": "pl_aaaa1111"}
        result = MODULE.tabletennisapi_profile("Yuanyu Chen", "WTT", {"chen yuanyu": profile})
        self.assertEqual(result["source_player_id"], "pl_aaaa1111")

    def test_tabletennisapi_profile_does_not_apply_to_domestic_competitions(self):
        result = MODULE.tabletennisapi_profile("Yuanyu Chen", "Setka Cup", {})
        self.assertEqual(result["status"], "not_applicable")

    def test_unchecked_wtt_player_is_queued(self):
        result = MODULE.tabletennisapi_profile("Yuanyu Chen", "WTT", {})
        self.assertEqual(result["status"], "queued_not_checked")
        self.assertFalse(result["model_eligible"])

    def test_exact_unique_candidate_exposes_source_scoped_recent_history(self):
        result = MODULE.player_history("Erik Mares", [match()], "Czech Liga Pro")
        self.assertEqual(result["status"], "exact_name_match_identity_unverified")
        self.assertEqual(result["matches_count"], 1)
        self.assertEqual((result["wins"], result["losses"]), (1, 0))
        self.assertEqual(result["recent_matches"][0]["opponent"], "Jakub Pilch")
        self.assertIn("not independently verified", result["identity_note"])

    def test_unique_initial_candidate_is_exposed_as_review_only(self):
        result = MODULE.player_history("Erik Mares", [match(a_name="Mares E.")], "Czech Liga Pro")
        self.assertEqual(result["status"], "name_initial_match_review_only")
        self.assertEqual(result["matches_count"], 1)
        self.assertIn("not a confirmed identity", result["identity_note"])

    def test_ambiguous_same_name_candidates_withhold_history(self):
        history = [
            match(a_id="101", a_pk=1, b_id="202", b_pk=2),
            match(a_id="303", a_pk=3, b_id="404", b_pk=4, date="2026-11-20"),
        ]
        result = MODULE.player_history("Erik Mares", history, "Czech Liga Pro")
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["matches"], [])

    def test_different_competition_candidate_does_not_attach_history(self):
        result = MODULE.player_history("Erik Mares", [match()], "Setka Cup")
        self.assertEqual(result["status"], "other_competition_only")
        self.assertEqual(result["matches"], [])


if __name__ == "__main__":
    unittest.main()
