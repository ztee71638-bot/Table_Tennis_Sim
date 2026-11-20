import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_polymarket_identity_evidence.py"
SPEC = importlib.util.spec_from_file_location("verify_identity_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class IdentityEvidenceAuditTests(unittest.TestCase):
    def test_wtt_public_profiles_only_corroborate_names(self):
        rows = [
            {"polymarket_player": "Ganghyeon Park", "competition_scope": "WTT",
             "database_status": "initial_abbreviation_review", "candidate_count": "1",
             "candidate_options_json": '[{"source_player_id":"1111389"}]'},
            {"polymarket_player": "Honoka Hashimoto", "competition_scope": "WTT",
             "database_status": "initial_abbreviation_review", "candidate_count": "1",
             "candidate_options_json": '[{"source_player_id":"1011828"}]'},
            {"polymarket_player": "Kaho Akae", "competition_scope": "WTT",
             "database_status": "initial_abbreviation_review", "candidate_count": "1",
             "candidate_options_json": '[{"source_player_id":"302076"}]'},
        ]
        audit = MODULE.build_audit(rows)
        self.assertEqual(len(audit), 3)
        self.assertTrue(all(r["independent_evidence_status"] == "public_profile_name_corroborated" for r in audit))
        self.assertTrue(all(r["source_player_id_link_status"] == "unverified" for r in audit))
        self.assertTrue(all(r["decision"] == "HOLD" for r in audit))
        self.assertTrue(all(r["evidence_url"].startswith("https://") for r in audit))

    def test_unchecked_candidates_get_search_hints_not_fake_evidence(self):
        row = {"polymarket_player": "Alesh Bayer", "competition_scope": "Czech Liga Pro",
               "database_status": "initial_abbreviation_review", "candidate_count": "1",
               "candidate_options_json": '[{"source_player_id":"115022"}]'}
        result = MODULE.build_audit([row])[0]
        self.assertEqual(result["independent_evidence_status"], "not_yet_checked")
        self.assertEqual(result["evidence_url"], "")
        self.assertIn("site:", result["search_hint"])
        self.assertEqual(result["decision"], "HOLD")

    def test_ambiguous_identity_is_never_automatically_selected(self):
        row = {"polymarket_player": "Jan Szotkowski", "competition_scope": "Czech Liga Pro",
               "database_status": "ambiguous_candidate", "candidate_count": "2",
               "candidate_options_json": '[{"source_player_id":"629357"},{"source_player_id":"633703"}]'}
        result = MODULE.build_audit([row])[0]
        self.assertEqual(result["candidate_count"], "2")
        self.assertEqual(result["source_player_id_link_status"], "unverified")
        self.assertEqual(result["decision"], "HOLD")


if __name__ == "__main__":
    unittest.main()
