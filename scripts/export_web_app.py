#!/usr/bin/env python3
"""Prepare static JSON assets for the GitHub Pages match simulator."""
import json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"site"/"data"
PROCESSED=ROOT/"data"/"processed"
OUT.mkdir(parents=True,exist_ok=True)
for name in ("current_player_states.json","prediction_model.json"):
    src=PROCESSED/name
    if not src.exists(): raise SystemExit(f"Missing required model artifact: {src}")
    shutil.copy2(src,OUT/name)
    print(f"Published {name}: {src.stat().st_size:,} bytes")
