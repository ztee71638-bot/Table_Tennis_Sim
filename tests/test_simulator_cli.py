import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "simulate_match.py"
SPEC = importlib.util.spec_from_file_location("simulate_match", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def make_artifacts(root, duplicate_names=False):
    out = Path(root)
    out.mkdir(parents=True, exist_ok=True)
    model = {
        "intercept": 0.0,
        "weights": {name: 0.0 for name in MODULE.FEATURES},
        "means": {name: 0.0 for name in MODULE.FEATURES},
        "scales": {name: 1.0 for name in MODULE.FEATURES},
        "holdout_metrics": {"enhanced": {"brier": 0.19}, "elo": {"brier": 0.21}},
    }
    names = ["Duplicate Name", "Duplicate Name"] if duplicate_names else ["Player Alpha", "Player Beta"]
    states = {"test_source": {
        "101": {
            "display_name": names[0], "elo": 1500, "matches": 15,
            "last_date": "2026-11-19", "recent_form_last10": [1, 0, 1],
            "competition_form": {"Test League": [1, 0]},
            "h2h_last10": {"202": [1, 0]},
            "opponent_records": {},
        },
        "202": {
            "display_name": names[1], "elo": 1500, "matches": 15,
            "last_date": "2026-11-19", "recent_form_last10": [0, 1, 0],
            "competition_form": {"Test League": [0, 1]},
            "h2h_last10": {"101": [0, 1]},
            "opponent_records": {},
        },
    }}
    (out / "prediction_model.json").write_text(json.dumps(model), encoding="utf-8")
    (out / "current_player_states.json").write_text(json.dumps(states), encoding="utf-8")


class SimulatorCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        make_artifacts(self.temp.name)
        self.old_path = MODULE.P
        MODULE.P = Path(self.temp.name)

    def tearDown(self):
        MODULE.P = self.old_path
        self.temp.cleanup()

    def run_cli(self, a="101", b="202", source="test_source", as_of="2026-11-20", simulations="1000"):
        args = [
            "simulate_match.py", "--source-key", source,
            "--player-a", a, "--player-b", b,
            "--competition", "Test League", "--as-of", as_of,
            "--simulations", simulations,
        ]
        output = io.StringIO()
        with patch.object(sys, "argv", args), contextlib.redirect_stdout(output):
            MODULE.main()
        return json.loads(output.getvalue())

    def test_emits_valid_result_and_reproducible_simulation(self):
        first = self.run_cli()
        second = self.run_cli()
        self.assertEqual(first["simulations"], 1000)
        self.assertEqual(first["best_of"], 5)
        self.assertEqual(first["decision"], "PASS")
        self.assertEqual(first["simulated_win_rate_a"], second["simulated_win_rate_a"])
        self.assertEqual(first["monte_carlo_95pct_interval"], second["monte_carlo_95pct_interval"])

    def test_rejects_same_player(self):
        with self.assertRaisesRegex(SystemExit, "two different players"):
            self.run_cli(b="101")

    def test_rejects_unknown_source_key(self):
        with self.assertRaisesRegex(SystemExit, "Unknown source key"):
            self.run_cli(source="unverified_source")

    def test_rejects_as_of_before_latest_recorded_match(self):
        with self.assertRaisesRegex(SystemExit, "predates"):
            self.run_cli(as_of="2026-11-18")

    def test_rejects_duplicate_display_names(self):
        make_artifacts(self.temp.name, duplicate_names=True)
        with self.assertRaisesRegex(SystemExit, "matched 2 records"):
            self.run_cli(a="Duplicate Name")

    def test_rejects_simulation_count_below_minimum(self):
        with self.assertRaisesRegex(SystemExit, "between 1,000 and 1,000,000"):
            self.run_cli(simulations="999")


if __name__ == "__main__":
    unittest.main()
