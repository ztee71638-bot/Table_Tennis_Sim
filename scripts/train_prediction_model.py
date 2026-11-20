#!/usr/bin/env python3
"""Leakage-safe chronological form model, holdout evaluation, and state export."""
import csv,json,math,sqlite3,statistics
from collections import defaultdict
from datetime import date
from itertools import groupby
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; DB=ROOT/"data/database/table_tennis.sqlite"; OUT=ROOT/"data/processed"
FEATURES=["elo_diff_400","form_diff_10","competition_form_diff_10","h2h_diff_10","inactivity_diff_30"]
def sig(z): return 1/(1+math.exp(-max(-30,min(30,z))))
def avg(x): return sum(x)/len(x) if x else 0.0
def ll(y,p): p=max(1e-9,min(1-1e-9,p)); return -(y*math.log(p)+(1-y)*math.log(1-p))
def fit(rows,cut):
 t=[r for r in rows if r["date"]<cut]
 if len(t)<100: raise ValueError("Insufficient chronological training rows")
 mu={f:avg([r[f] for r in t]) for f in FEATURES}
 sd={f:(statistics.pstdev([r[f] for r in t]) or 1) for f in FEATURES}
 X=[[1]+[(r[f]-mu[f])/sd[f] for f in FEATURES] for r in t]; Y=[r["y"] for r in t]; w=[0.0]*6
 for _ in range(500):
  g=[0.0]*6
  for x,y in zip(X,Y):
   p=sig(sum(a*b for a,b in zip(w,x)))
   for j in range(6): g[j]+=(p-y)*x[j]
  for j in range(6): w[j]-=.08*(g[j]/len(Y)+(.002*w[j] if j else 0))
 return {"intercept":w[0],"weights":dict(zip(FEATURES,w[1:])),"means":mu,"scales":sd,"training_matches":len(t)}
def pred(m,r):
 return sig(m["intercept"]+sum(m["weights"][f]*(r[f]-m["means"][f])/m["scales"][f] for f in FEATURES))
def main():
 OUT.mkdir(parents=True,exist_ok=True); c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
 matches=c.execute("""SELECT m.match_pk,m.source_match_id,m.match_date,m.competition,m.player_a_pk,m.player_b_pk,m.sets_a,m.sets_b,m.raw_row_json,s.source_key,pa.source_player_id aid,pa.display_name aname,pb.source_player_id bid,pb.display_name bname FROM matches m JOIN sources s USING(source_id) JOIN players pa ON pa.player_pk=m.player_a_pk JOIN players pb ON pb.player_pk=m.player_b_pk WHERE s.source_key LIKE 'wtt_%' AND m.match_date IS NOT NULL ORDER BY m.match_date,m.match_pk""").fetchall()
 states={}; rows=[]; excluded=0
 for day,grp in groupby(matches,key=lambda x:x["match_date"]):
  pending=[]; elo_delta=defaultdict(float)
  for m in grp:
   raw=json.loads(m["raw_row_json"] or "{}")
   try: winner=int(raw.get("winner",""))
   except (ValueError,TypeError): excluded+=1; continue
   sa,sb=m["sets_a"] or 0,m["sets_b"] or 0
   implied=1 if sa>sb else 2 if sb>sa else 0
   if winner not in (1,2) or winner!=implied or max(sa,sb)<3: excluded+=1; continue
   source=m["source_key"]; comp=m["competition"] or "UNKNOWN"; st=states.setdefault(source,{})
   aid,bid=str(m["aid"]),str(m["bid"])
   a=st.setdefault(aid,{"elo":1500.0,"form":[],"comp":{},"h2h":{},"last":None,"n":0})
   b=st.setdefault(bid,{"elo":1500.0,"form":[],"comp":{},"h2h":{},"last":None,"n":0})
   da=(date.fromisoformat(day)-date.fromisoformat(a["last"])).days if a["last"] else 365
   db=(date.fromisoformat(day)-date.fromisoformat(b["last"])).days if b["last"] else 365
   y=1 if winner==1 else 0; pe=sig((a["elo"]-b["elo"])*math.log(10)/400)
   h=a["h2h"].get(bid,[]); ac=a["comp"].get(comp,[]); bc=b["comp"].get(comp,[])
   row={"date":day,"source_key":source,"source_match_id":m["source_match_id"],"player_a_id":aid,"player_b_id":bid,"player_a":m["aname"],"player_b":m["bname"],"competition":comp,
    "elo_diff_400":(a["elo"]-b["elo"])/400,"form_diff_10":avg(a["form"][-10:])-avg(b["form"][-10:]),
    "competition_form_diff_10":avg(ac[-10:])-avg(bc[-10:]),"h2h_diff_10":2*avg(h[-10:])-1 if h else 0,
    "inactivity_diff_30":max(-1,min(1,(db-da)/30)),"elo_prob_a":pe,"y":y,"prior_a":a["n"],"prior_b":b["n"]}
   rows.append(row); pending.append((source,aid,bid,comp,y,pe))
   elo_delta[(source,aid)]+=24*(y-pe); elo_delta[(source,bid)]+=24*((1-y)-(1-pe))
  # All matches on the date use pre-date features/ratings; update histories only afterwards.
  for source,aid,bid,comp,y,pe in pending:
   st=states[source]; a=st[aid]; b=st[bid]
   a["form"]=(a["form"]+[y])[-50:]; b["form"]=(b["form"]+[1-y])[-50:]
   a["comp"][comp]=(a["comp"].get(comp,[])+[y])[-50:]; b["comp"][comp]=(b["comp"].get(comp,[])+[1-y])[-50:]
   a["h2h"][bid]=(a["h2h"].get(bid,[])+[y])[-50:]; b["h2h"][aid]=(b["h2h"].get(aid,[])+[1-y])[-50:]
   a["n"]+=1; b["n"]+=1; a["last"]=day; b["last"]=day
  for (source,pid),delta in elo_delta.items(): states[source][pid]["elo"]+=delta
 if len(rows)<500: raise ValueError(f"Too few clean matches: {len(rows)}")
 dates=sorted({r["date"] for r in rows}); cut=dates[max(1,min(len(dates)-1,int(len(dates)*.75)))]
 model=fit(rows,cut); test=[r for r in rows if r["date"]>=cut]
 if len(test)<100: raise ValueError("Chronological holdout has fewer than 100 matches")
 metrics={}
 for name,fn in [("elo",lambda r:r["elo_prob_a"]),("enhanced",lambda r:pred(model,r))]:
  ps=[fn(r) for r in test]; ys=[r["y"] for r in test]
  metrics[name]={"n":len(test),"accuracy":avg([int((p>=.5)==bool(y)) for p,y in zip(ps,ys)]),"brier":avg([(p-y)**2 for p,y in zip(ps,ys)]),"log_loss":avg([ll(y,p) for y,p in zip(ys,ps)])}
 model.update({"features":FEATURES,"best_of":5,"holdout_start":cut,"holdout_end":dates[-1],"holdout_metrics":metrics,"method":"Chronological 75/25 split by date; pre-date Elo, recent form, competition form, head-to-head and inactivity features; same-day results applied only after feature creation."})
 names=c.execute("SELECT s.source_key,p.source_player_id,p.display_name FROM players p JOIN sources s USING(source_id) WHERE s.source_key LIKE 'wtt_%'").fetchall()
 export={}
 for source,ps in states.items():
  export[source]={pid:{"display_name":None,"elo":round(s["elo"],3),"matches":s["n"],"last_date":s["last"],"recent_form_last10":s["form"][-10:],"competition_form":{k:v[-10:] for k,v in s["comp"].items()},"h2h_last10":{k:v[-10:] for k,v in s["h2h"].items()}} for pid,s in ps.items()}
 for n in names:
  p=export.get(n["source_key"],{}).get(n["source_player_id"])
  if p: p["display_name"]=n["display_name"]
 (OUT/"prediction_model.json").write_text(json.dumps(model,indent=2))
 (OUT/"current_player_states.json").write_text(json.dumps(export,indent=2,ensure_ascii=False))
 with (OUT/"wtt_enhanced_features.csv").open("w",newline="",encoding="utf-8") as f:
  fields=list(rows[0]); w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
 report={"clean_matches":len(rows),"excluded_matches":excluded,"train_matches":model["training_matches"],"holdout_start":cut,"holdout_matches":len(test),"metrics":metrics,"features":FEATURES,"best_of":5,"decision_rules":["PASS if either player has fewer than 10 prior matches.","PASS if enhanced model does not beat Elo on chronological holdout Brier score.","PASS if predicted win probability is below 65% for the selected side.","No cross-source identity merging; no guarantee of future performance."]}
 (OUT/"prediction_backtest_report.json").write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2)); c.close()
if __name__=="__main__": main()
