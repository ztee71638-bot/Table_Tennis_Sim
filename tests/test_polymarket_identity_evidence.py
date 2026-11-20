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
        self.assertTrue(all(r["independent_evidence_status"] == "public_profile_name_corroborated" for r in audit))
        self.assertTrue(all(r["source_player_id_link_status"] == "unverified" for r in audit))
        self.assertTrue(all(r["decision"] == "HOLD" for r in audit))

    def test_exact_match_results_correlate_four_candidates_but_never_approve(self):
        fixtures = [
            {"id": 1140607, "_snapshot_date": "2026-11-19",
             "league": {"name": "Czech Liga Pro"},
             "home": {"id": 115022, "name": "Bayer A."}, "away": {"id": 69500, "name": "Tuma D."},
             "homeScore": {"periods": {"period1": 4, "period2": 11, "period3": 13, "period4": 11}},
             "awayScore": {"periods": {"period1": 11, "period2": 9, "period3": 11, "period4": 5}}},
            {"id": 1169149, "_snapshot_date": "2026-11-19",
             "league": {"name": "Czech Liga Pro"},
             "home": {"id": 115022, "name": "Bayer A."}, "away": {"id": 69500, "name": "Tuma D."},
             "homeScore": {"periods": {"period1": 11, "period2": 11, "period3": 11, "period4": 12, "period5": 11}},
             "awayScore": {"periods": {"period1": 8, "period2": 13, "period3": 6, "period4": 14, "period5": 7}}},
            {"id": 1140540, "_snapshot_date": "2026-11-19",
             "league": {"name": "Czech Liga Pro"},
             "home": {"id": 632210, "name": "Mares E."}, "away": {"id": 176, "name": "Postelt T."},
             "homeScore": {"periods": {"period1": 7, "period2": 11, "period3": 9, "period4": 12, "period5": 9}},
             "awayScore": {"periods": {"period1": 11, "period2": 7, "period3": 11, "period4": 10, "period5": 11}}},
            {"id": 1175375, "_snapshot_date": "2026-11-19",
             "league": {"name": "Czech Liga Pro"},
             "home": {"id": 625247, "name": "Pilch J."}, "away": {"id": 632210, "name": "Mares E."},
             "homeScore": {"periods": {"period1": 5, "period2": 11, "period3": 12, "period4": 17}},
             "awayScore": {"periods": {"period1": 11, "period2": 9, "period3": 10, "period4": 15}}},
        ]
        rows = [
            {"polymarket_player": "Alesh Bayer", "competition_scope": "Czech Liga Pro",
             "candidate_options_json": '[{"source_player_id":"115022"}]'},
            {"polymarket_player": "Daniel Tuma", "competition_scope": "Czech Liga Pro",
             "candidate_options_json": '[{"source_player_id":"69500"}]'},
            {"polymarket_player": "Erik Mares", "competition_scope": "Czech Liga Pro",
             "candidate_options_json": '[{"source_player_id":"632210"}]'},
            {"polymarket_player": "Jakub Pilch", "competition_scope": "Czech Liga Pro",
             "candidate_options_json": '[{"source_player_id":"625247"}]'},
        ]
        audit = MODULE.build_audit(rows, fixtures)
        self.assertTrue(all(r["independent_evidence_status"] == "match_level_records_correlated" for r in audit))
        self.assertTrue(all(r["source_player_id_link_status"] == "unverified" for r in audit))
        self.assertTrue(all(r["decision"] == "HOLD" for r in audit))
        self.assertEqual(sum(int(r["matched_independent_result_count"]) for r in audit), 6)

    def test_szotkowski_profile_correlates_four_exact_results_but_keeps_ambiguous_ids_on_hold(self):
        fixtures = [
            {"id": 1140596, "_snapshot_date": "2026-11-19", "league": {"name": "Czech Liga Pro"},
             "home": {"id": 168877}, "away": {"id": 633703},
             "homeScore": {"periods": {"period1": 8, "period2": 2, "period3": 8}},
             "awayScore": {"periods": {"period1": 11, "period2": 11, "period3": 11}}},
            {"id": 1140589, "_snapshot_date": "2026-11-19", "league": {"name": "Czech Liga Pro"},
             "home": {"id": 633703}, "away": {"id": 51742},
             "homeScore": {"periods": {"period1": 11, "period2": 10, "period3": 11, "period4": 11}},
             "awayScore": {"periods": {"period1": 4, "period2": 12, "period3": 6, "period4": 4}}},
            {"id": 1140575, "_snapshot_date": "2026-11-19", "league": {"name": "Czech Liga Pro"},
             "home": {"id": 51741}, "away": {"id": 633703},
             "homeScore": {"periods": {"period1": 9, "period2": 6, "period3": 7}},
             "awayScore": {"periods": {"period1": 11, "period2": 11, "period3": 11}}},
            {"id": 1140604, "_snapshot_date": "2026-11-19", "league": {"name": "Czech Liga Pro"},
             "home": {"id": 760418}, "away": {"id": 633703},
             "homeScore": {"periods": {"period1": 8, "period2": 5, "period3": 6}},
             "awayScore": {"periods": {"period1": 11, "period2": 11, "period3": 11}}},
        ]
        row = {"polymarket_player": "Jan Szotkowski", "competition_scope": "Czech Liga Pro",
               "database_status": "ambiguous_candidate", "candidate_count": "2",
               "candidate_options_json": '[{"source_player_id":"629357"},{"source_player_id":"633703"}]'}
        result = MODULE.build_audit([row], fixtures)[0]
        self.assertEqual(result["independent_evidence_status"], "match_level_records_correlated")
        self.assertEqual(result["matched_fixture_ids"], "1140575;1140589;1140596;1140604")
        self.assertEqual(result["matched_independent_result_count"], 4)
        self.assertEqual(result["source_player_id_link_status"], "unverified")
        self.assertEqual(result["decision"], "HOLD")

    def test_wrong_score_does_not_correlate(self):
        evidence = MODULE.MATCH_LEVEL_EVIDENCE[0]
        fixture = {"id": 1, "_snapshot_date": "2026-11-19",
                   "league": {"name": "Czech Liga Pro"},
                   "home": {"id": 115022}, "away": {"id": 69500},
                   "homeScore": {"periods": {"period1": 4, "period2": 11, "period3": 13, "period4": 10}},
                   "awayScore": {"periods": {"period1": 11, "period2": 9, "period3": 11, "period4": 5}}}
        self.assertFalse(MODULE._exact_fixture_match(evidence, fixture))

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
