#!/usr/bin/env python3
"""100,000-run best-of-five simulator using exported model/state artifacts."""
import argparse,json,math,random
from datetime import date
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; P=ROOT/"data/processed"
FEATURES=["elo_diff_400","form_diff_10","competition_form_diff_10","h2h_diff_10","inactivity_diff_30"]
def sig(z): return 1/(1+math.exp(-max(-30,min(30,z))))
def mean(x): return sum(x)/len(x) if x else 0.0
def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--source-key",required=True); ap.add_argument("--player-a",required=True,help="Exact source player ID or unique exact display name")
 ap.add_argument("--player-b",required=True); ap.add_argument("--competition",default="UNKNOWN")
 ap.add_argument("--simulations",type=int,default=100000); ap.add_argument("--as-of",default=date.today().isoformat())
 a=ap.parse_args()
 if a.simulations<1000 or a.simulations>1000000: raise SystemExit("simulations must be between 1,000 and 1,000,000")
 model=json.loads((P/"prediction_model.json").read_text()); states=json.loads((P/"current_player_states.json").read_text())
 pool=states.get(a.source_key)
 if pool is None: raise SystemExit("Unknown source key; player identities are source-specific.")
 def resolve(value):
  if value in pool: return value
  found=[pid for pid,s in pool.items() if s.get("display_name")==value]
  if len(found)!=1: raise SystemExit(f"Player '{value}' matched {len(found)} records; use exact source player ID.")
  return found[0]
 aid,bid=resolve(a.player_a),resolve(a.player_b)
 if aid==bid: raise SystemExit("Select two different players.")
 x,y=pool[aid],pool[bid]
 def days(s): return (date.fromisoformat(a.as_of)-date.fromisoformat(s["last_date"])).days if s["last_date"] else 365
 comp=a.competition
 feats={"elo_diff_400":(x["elo"]-y["elo"])/400,
  "form_diff_10":mean(x["recent_form_last10"])-mean(y["recent_form_last10"]),
  "competition_form_diff_10":mean(x["competition_form"].get(comp,[]))-mean(y["competition_form"].get(comp,[])),
  "h2h_diff_10":2*mean(x["h2h_last10"].get(bid,[]))-1 if x["h2h_last10"].get(bid) else 0,
  "inactivity_diff_30":max(-1,min(1,(days(y)-days(x))/30))}
 z=model["intercept"]+sum(model["weights"][f]*(feats[f]-model["means"][f])/model["scales"][f] for f in FEATURES)
 p=1/(1+math.exp(-max(-30,min(30,z))))
 elo_p=1/(1+10**((y["elo"]-x["elo"])/400))
 qlo,qhi=0.000001,.999999
 for _ in range(70):
  q=(qlo+qhi)/2
  if 10*q**3-15*q**4+6*q**5<p: qlo=q
  else: qhi=q
 q=(qlo+qhi)/2
 rng=random.Random(20261120); wins=0; score_a=score_b=0
 for _ in range(a.simulations):
  sa=sb=0
  while sa<3 and sb<3:
   if rng.random()<q: sa+=1
   else: sb+=1
  if sa>sb: wins+=1; score_a+=1
  else: score_b+=1
 sim=wins/a.simulations; se=math.sqrt(sim*(1-sim)/a.simulations)
 improved=model["holdout_metrics"]["enhanced"]["brier"]<model["holdout_metrics"]["elo"]["brier"]
 eligible=x["matches"]>=10 and y["matches"]>=10 and improved and max(p,1-p)>=.65
 result="PASS"
 if eligible: result="MODEL LEAN: "+(x["display_name"] or aid) if p>=.5 else "MODEL LEAN: "+(y["display_name"] or bid)
 print(json.dumps({"decision":result,"source_key":a.source_key,"player_a":{"id":aid,"name":x["display_name"],"prior_matches":x["matches"],"elo":x["elo"]},"player_b":{"id":bid,"name":y["display_name"],"prior_matches":y["matches"],"elo":y["elo"]},"competition":comp,"model_probability_a":round(p,5),"elo_probability_a":round(elo_p,5),"best_of":5,"simulations":a.simulations,"simulated_win_rate_a":round(sim,5),"monte_carlo_95pct_interval":[round(max(0,sim-1.96*se),5),round(min(1,sim+1.96*se),5)],"features":feats,"holdout_brier_enhanced":model["holdout_metrics"]["enhanced"]["brier"],"holdout_brier_elo":model["holdout_metrics"]["elo"]["brier"],"guardrail":"PASS unless both players have at least 10 prior matches, enhanced model beats Elo holdout Brier, and model probability is at least 65% for the selected side. Interval reflects simulation noise only, not model uncertainty."},indent=2))
if __name__=="__main__": main()
