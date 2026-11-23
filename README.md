# Table Tennis Sim — Historical Database

A source-aware, reproducible database for table-tennis match results, player records, Elo ratings, and simulation research.

## Project rules

- Keep raw source files unchanged in `data/raw/`.
- Preserve each source's original player IDs. IDs are namespaced by source; never assume IDs from different datasets identify the same person.
- Store identity matches as candidates until verified by multiple independent match records.
- Keep source/license/provenance details with every import.
- Never fabricate missing names, scores, dates, or match results.
- Use a strict PASS / no-bet decision when evidence is weak.

## Current imported data

| Source | Records | Meaning |
|---|---:|---|
| SCORE Setka Cup CSV | 7,851 | Historical match rows |
| WTT men's 2022–2025 | 5,442 | Historical match rows |
| WTT women's 2022–2025 | 4,850 | Historical match rows |
| DataSportsAPI rolling feed | 9,318 | Classified recent-window records; 9,176 clean individual singles after 29 invalid results were excluded |
| Lathise public Elo sample | 2,000 | Pre-match Elo observations, not additional matches |

Latest successful scheduled update #39 (2026-11-23 UTC): 27,461 total database match records, 3,718 source-scoped player records, and 10 retained daily DataSportsAPI snapshots. The DataSportsAPI classification included 9,318 records; 9,205 were eligible for individual-player records, 113 were excluded, and 9,176 clean individual singles remained after invalid-result filtering. Counts are source-scoped; player records from different sources are not automatically merged.

## Automated build and outputs

GitHub Actions rebuilds the SQLite database, imports WTT, runs `scripts/analyze_database.py`, and publishes a 30-day artifact named `table-tennis-database-build`.

The artifact contains:
- `table_tennis.sqlite` — combined database and persistent quality flags
- Original downloaded CSV source files
- `database_quality_report.json` — integrity, coverage, anomalies, and baseline evaluation
- `wtt_pre_match_features.csv` — chronological pre-match Elo features for clean WTT results

## Recent domestic-league coverage

The scheduled build refreshes the latest seven days of DataSportsAPI results using the existing `DATASPORTSAPI_KEY` secret. DataSportsAPI has provided written permission for private retention of lawfully fetched records, derived statistics, internal model training/testing/validation, and display of original derived outputs, including commercial use, with no separate licence for that scope. Raw records must not be redistributed or published in bulk as a substitute feed. Free access is 1,000 requests/day during beta and 100/day afterward. Its player records remain source-isolated. The DataSportsAPI-specific chronological backtest is kept separate and is not promoted: latest holdout accuracy was 55.10% versus 55.56% for its Elo baseline.

The build also compares Polymarket's current table-tennis listings with recent player histories and exports competition-specific records, last-played dates, and historical head-to-head evidence. Initial-only and ambiguous name matches remain manual-review candidates. No player identities are automatically merged.

See [Domestic league coverage](docs/domestic_league_coverage.md) and [Polymarket integration](docs/polymarket_us_integration.md).

## Quality and modeling safeguards

- Source rows are retained; suspicious results are flagged, not silently corrected.
- The WTT files set `best_of=7` on all rows although most results end after three set wins. The audit documents this inconsistency and does not blindly enforce the field.
- The initial WTT Elo baseline uses 1500 starting ratings and K=24, separately by source. All matches on the same date use ratings from before that date to avoid same-day result leakage.
- The current baseline is a research benchmark, not a trained model or a betting recommendation. Its accuracy and Brier score are reported in the generated audit JSON.
- No cross-source identity merging or player-name guesses are performed.

## Repository layout

- `data/raw/` — original source downloads
- `data/processed/` — audit and feature exports
- `sql/schema.sql` — SQLite schema
- `docs/` — data dictionary, identity rules, and acquisition roadmap
- `scripts/` — import, audit, and feature-generation utilities

See [SOURCES.md](SOURCES.md) for source links, licensing, and provenance.
