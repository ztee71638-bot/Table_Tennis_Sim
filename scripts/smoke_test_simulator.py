#!/usr/bin/env python3
"""CI smoke test: exercise the exported-model CLI with 100,000 BO5 simulations."""
import json,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
states=json.loads((root/"data/processed/current_player_states.json").read_text())
choice=None
for source,pool in sorted(states.items()):
    eligible=[pid for pid,p in sorted(pool.items()) if p.get("matches",0)>=10]
    if len(eligible)>=2:
        choice=(source,eligible[0],eligible[1]); break
if not choice: raise SystemExit("No pair with at least 10 prior matches each; simulator smoke test cannot proceed")
source,a,b=choice
run=subprocess.run([sys.executable,str(root/"scripts/simulate_match.py"),"--source-key",source,
    "--player-a",a,"--player-b",b,"--simulations","100000"],capture_output=True,text=True,check=True)
result=json.loads(run.stdout)
assert result["simulations"]==100000
assert result["best_of"]==5
assert 0<=result["simulated_win_rate_a"]<=1
assert result["decision"] in ("PASS",) or result["decision"].startswith("MODEL LEAN:")
assert result["player_a"]["prior_matches"]>=10 and result["player_b"]["prior_matches"]>=10
print(json.dumps({"smoke_test":"passed","source_key":source,"simulations":100000,
 "decision":result["decision"],"simulated_win_rate_a":result["simulated_win_rate_a"]},indent=2))
