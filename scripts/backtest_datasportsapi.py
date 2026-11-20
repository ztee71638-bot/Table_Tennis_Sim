#!/usr/bin/env python3
"""Leakage-safe DataSportsAPI singles validation and chronological backtest."""
import json, math, sqlite3, statistics
from collections import defaultdict
from datetime import date
from itertools import groupby
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/"data/database/table_tennis.sqlite"
OUT=ROOT/"data/processed"
SOURCE="datasportsapi_table_tennis"
FEATURES=("elo_diff","form_diff","h2h_diff","competition_form_diff","inactivity_diff","common_opponent_diff")

def sigmoid(z):
    return 1/(1+math.exp(-max(-30,min(30,z))))
def avg(x):
    return sum(x)/len(x) if x else 0.0
def brier(rows, fn):
    return avg([(fn(r)-r["y"])**2 for r in rows])
def main():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
    matches=c.execute("""
      SELECT m.match_pk,m.match_date,m.competition,m.player_a_pk,m.player_b_pk,
             m.sets_a,m.sets_b,m.winner_player_pk,
             a.source_player_id aid,b.source_player_id bid
      FROM matches m JOIN sources s USING(source_id)
      JOIN players a ON a.player_pk=m.player_a_pk
      JOIN players b ON b.player_pk=m.player_b_pk
      JOIN datasportsapi_match_classification d ON d.match_pk=m.match_pk
      WHERE s.source_key=? AND d.match_type='singles'
        AND m.winner_player_pk IS NOT NULL AND m.match_date IS NOT NULL
      ORDER BY m.match_date,m.match_pk
    """,(SOURCE,)).fetchall()
    states={}; rows=[]; excluded=0
    for day, group in groupby(matches,key=lambda r:r["match_date"]):
      pending=[]; deltas=defaultdict(float)
      for m in group:
        sa,sb=m["sets_a"] or 0,m["sets_b"] or 0
        if sa==sb or max(sa,sb)<3 or m["winner_player_pk"] not in (m["player_a_pk"],m["player_b_pk"]) or ((m["winner_player_pk"]==m["player_a_pk"]) != (sa>sb)):
          excluded+=1; continue
        comp=m["competition"] or "UNKNOWN"; a_id,b_id=m["aid"],m["bid"]
        a=states.setdefault(a_id,{"elo":1500.,"form":[],"h2h":defaultdict(list),"comp":defaultdict(list),"vs":defaultdict(lambda:[0,0]),"last":None,"n":0})
        b=states.setdefault(b_id,{"elo":1500.,"form":[],"h2h":defaultdict(list),"comp":defaultdict(list),"vs":defaultdict(lambda:[0,0]),"last":None,"n":0})
        y=int(m["winner_player_pk"]==m["player_a_pk"])
        da=(date.fromisoformat(day)-date.fromisoformat(a["last"])).days if a["last"] else 365
        db=(date.fromisoformat(day)-date.fromisoformat(b["last"])).days if b["last"] else 365
        common=set(a["vs"])&set(b["vs"])
        diffs=[(a["vs"][o][0]/sum(a["vs"][o]))-(b["vs"][o][0]/sum(b["vs"][o])) for o in common if sum(a["vs"][o]) and sum(b["vs"][o])]
        row={"date":day,"y":y,"elo_diff":(a["elo"]-b["elo"])/400,
          "form_diff":avg(a["form"][-10:])-avg(b["form"][-10:]),
          "h2h_diff":2*avg(a["h2h"][b_id][-10:])-1 if a["h2h"][b_id] else 0,
          "competition_form_diff":avg(a["comp"][comp][-10:])-avg(b["comp"][comp][-10:]),
          "inactivity_diff":max(-1,min(1,(db-da)/30)),
          "common_opponent_diff":avg(diffs),"common_opponents":len(diffs),
          "prior_a":a["n"],"prior_b":b["n"]}
        rows.append(row); pending.append((a_id,b_id,comp,y))
        p=sigmoid((a["elo"]-b["elo"])*math.log(10)/400)
        deltas[a_id]+=24*(y-p); deltas[b_id]+=24*((1-y)-(1-p))
      # Same-day matches all use prior-day features; update only after day complete.
      for a_id,b_id,comp,y in pending:
        a,b=states[a_id],states[b_id]
        a["form"]=(a["form"]+[y])[-50:]; b["form"]=(b["form"]+[1-y])[-50:]
        a["h2h"][b_id]=(a["h2h"][b_id]+[y])[-50:]; b["h2h"][a_id]=(b["h2h"][a_id]+[1-y])[-50:]
        a["comp"][comp]=(a["comp"][comp]+[y])[-50:]; b["comp"][comp]=(b["comp"][comp]+[1-y])[-50:]
        a["vs"][b_id][0 if y else 1]+=1; b["vs"][a_id][0 if not y else 1]+=1
        a["n"]+=1;b["n"]+=1;a["last"]=day;b["last"]=day
      for pid,delta in deltas.items(): states[pid]["elo"]+=delta
    dates=sorted({r["date"] for r in rows})
    report={"source":SOURCE,"singles_rows_considered":len(matches),"clean_matches":len(rows),"excluded_invalid_results":excluded,
      "unique_competitors":len(states),"dates": {"first":dates[0] if dates else None,"last":dates[-1] if dates else None},
      "classification":[{"match_type":r[0],"confidence":r[1],"count":r[2]} for r in c.execute("SELECT match_type,confidence,COUNT(*) FROM datasportsapi_match_classification GROUP BY match_type,confidence").fetchall()],
      "database_integrity":c.execute("PRAGMA integrity_check").fetchone()[0]}
    if len(rows)>=500 and len(dates)>=10:
      cut=dates[max(1,min(len(dates)-1,int(len(dates)*.75)))]
      train=[r for r in rows if r["date"]<cut]; test=[r for r in rows if r["date"]>=cut]
      if len(test)>=100 and len(train)>=100:
        means={f:avg([r[f] for r in train]) for f in FEATURES}
        scales={f:(statistics.pstdev([r[f] for r in train]) or 1) for f in FEATURES}
        weights=[0.]*(len(FEATURES)+1)
        for _ in range(350):
          grad=[0.] * len(weights)
          for r in train:
            x=[1.]+[(r[f]-means[f])/scales[f] for f in FEATURES]; p=sigmoid(sum(w*v for w,v in zip(weights,x)))
            for i,v in enumerate(x): grad[i]+=(p-r["y"])*v
          for i in range(len(weights)): weights[i]-=.06*(grad[i]/len(train)+(.002*weights[i] if i else 0))
        def enhanced(r): return sigmoid(weights[0]+sum(weights[i+1]*(r[f]-means[f])/scales[f] for i,f in enumerate(FEATURES)))
        elo=lambda r:sigmoid(r["elo_diff"]*math.log(10))
        report["chronological_backtest"]={"split":"75% earlier dates train / 25% later dates holdout","holdout_start":cut,"holdout_end":dates[-1],"train_matches":len(train),"holdout_matches":len(test),
          "elo_brier":round(brier(test,elo),6),"enhanced_brier":round(brier(test,enhanced),6),
          "elo_accuracy":round(avg([int((elo(r)>=.5)==bool(r["y"])) for r in test]),4),
          "enhanced_accuracy":round(avg([int((enhanced(r)>=.5)==bool(r["y"])) for r in test]),4),
          "beats_elo_brier":brier(test,enhanced)<brier(test,elo),
          "features":list(FEATURES),"same_day_results_excluded":True}
      else: report["chronological_backtest"]={"status":"insufficient train/holdout sample"}
    else: report["chronological_backtest"]={"status":"insufficient history for credible chronological backtest"}
    report["promotion_status"]="NOT_PROMOTED"
    report["promotion_reason"]="Separate source-specific backtest only; model promotion requires adequate holdout, lower Brier than Elo, and review of classification quality."
    OUT.mkdir(exist_ok=True,parents=True)
    (OUT/"datasportsapi_quality_backtest.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2)); c.close()
    if report["database_integrity"]!="ok": raise SystemExit("SQLite integrity failure")
if __name__=="__main__": main()
