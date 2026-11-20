import importlib.util
import json
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_polymarket_identity_candidates.py"
SPEC = importlib.util.spec_from_file_location("review_identity", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class IdentityReviewQueueTests(unittest.TestCase):
    def test_only_non_exact_candidates_enter_manual_queue(self):
        rows = [
            {"polymarket_player":"A Person","database_status":"initial_abbreviation_review","candidate_count":"1","candidate_options":'[{"source_player_id":"12"}]'},
            {"polymarket_player":"B Person","database_status":"ambiguous_candidate","candidate_count":"2","candidate_options":'[{"source_player_id":"21"},{"source_player_id":"22"}]'},
            {"polymarket_player":"C Person","database_status":"exact_name_match"},
            {"polymarket_player":"D Person","database_status":"not_found"},
        ]
        queue = MODULE.build_queue(rows)
        self.assertEqual([r["polymarket_player"] for r in queue], ["B Person","A Person"])
        self.assertEqual(json.loads(queue[0]["candidate_options_json"])[1]["source_player_id"], "22")

    def test_queue_never_preapproves_or_merges(self):
        row = {"polymarket_player":"A Person","database_status":"initial_abbreviation_review","candidate_options":'[{"source_player_id":"12"}]'}
        queued = MODULE.build_queue([row])[0]
        self.assertEqual(queued["decision"], "")
        self.assertEqual(queued["selected_source_player_id"], "")
        self.assertIn("independent", queued["review_rule"])

if __name__ == "__main__":
    unittest.main()
