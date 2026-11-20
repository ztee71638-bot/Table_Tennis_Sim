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
| SCORE Setka Cup CSV | 7,851 | Match rows |
| WTT men's 2022–2025 | 5,442 | Match rows |
| WTT women's 2022–2025 | 4,850 | Match rows |
| Lathise public Elo sample | 2,000 | Pre-match Elo observations, not additional matches |

Total: 18,143 match rows plus 2,000 Elo observations. The database has 1,942 source-scoped player records. Player records from different sources are not automatically merged.

## Automated build and outputs

GitHub Actions rebuilds the SQLite database, imports WTT, runs `scripts/analyze_database.py`, and publishes a 30-day artifact named `table-tennis-database-build`.

The artifact contains:
- `table_tennis.sqlite` — combined database and persistent quality flags
- Original downloaded CSV source files
- `database_quality_report.json` — integrity, coverage, anomalies, and baseline evaluation
- `wtt_pre_match_features.csv` — chronological pre-match Elo features for clean WTT results

## Recent domestic-league coverage

The main build now also refreshes the latest seven days of DataSportsAPI results when the existing `DATASPORTSAPI_KEY` secret is configured. The feed covers Czech Liga Pro, Setka Cup, TT Elite Series, TT Cup, and Liga Pro, among other competitions. Its player records remain source-isolated and descriptive; the WTT prediction model is not silently retrained on these leagues.

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
