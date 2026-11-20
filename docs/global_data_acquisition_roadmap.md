# Global data acquisition roadmap

## Goal
Build a broad, multi-competition table-tennis match archive that supports player-level form, head-to-head analysis, set/game scoring, and later calibrated best-of-five simulations.

## Current verified baseline
- SCORE Setka Cup: 7,851 match rows imported.
- Lathise Elo sample: 2,000 pre-match Elo observations imported.
- These are different record types. Do not add them together and describe the sum as unique matches.
- Automated GitHub Actions build is enabled for importer/workflow changes.

## Expansion phases

### Phase 1 — Free downloadable historical datasets
- Obtain and inspect the WTT men/women dataset files advertised by the Racket Sports Multi-Dataset project (2022-2025; README reports 10,292 WTT rows combined).
- Verify actual file availability, schema, dates, duplicates, and CC BY 4.0 attribution requirements before import.
- Add official ITTF World Championships historical results as a distinct source. Preserve missing scores and the source's Round-of-16 coverage limitation.

### Phase 2 — Free account / public archives
- Determine whether 11EDGE permits a free-account export or automated access to its advertised global match history.
- If only manual browsing is available, keep it as a research/reference source; do not scrape at scale without permission.
- Evaluate public named-result archives such as U.S. Table Tennis Results & History.

### Phase 3 — Domestic professional leagues
Prioritize coverage where match-level results and player names are available:
- Setka Cup and Setka Cup Women
- TT Elite Series
- Czech Liga Pro
- TT Cup
- Challenger Series TT
- WTT and national leagues in Europe and Asia
For each competition, document provider, date coverage, score depth, player-name quality, access method, and reuse terms. Paid-only feeds remain out of scope unless the owner explicitly changes the free-only budget.

### Phase 4 — Recent results and supplementary events
- Consider a free recent-results API only within its documented quota and date limits.
- Optional community tournament APIs must be tagged separately from professional competitions.
- Never let a broad event feed silently contaminate the professional-league training set.

## Import acceptance checklist
- Direct download/API endpoint tested successfully.
- Terms/license reviewed and recorded.
- Source file hash and retrieval timestamp stored.
- Raw rows preserved.
- Competition and event type normalized without losing source labels.
- Player IDs remain source-scoped until independently verified.
- Match date, names, winner, set score, and per-game scores checked for completeness.
- Duplicate detection uses source IDs or strong composite evidence.
- Automated build passes before a source is considered integrated.

## Model safeguards
- Separate international WTT, professional domestic leagues, and community events in analysis.
- Track best-of-five vs best-of-seven and team-tie rubbers separately.
- Use chronological train/test splits; never allow future results or pre-match ratings to leak into past predictions.
- Do not produce a confident pick when sample size, player identity, score completeness, or form evidence is weak; mark it PASS.


## Completed engineering steps (2026-11-20)

1. Imported and checksum-verified WTT men's (5,442) and women's (4,850) source rows.
2. Verified SQLite integrity and foreign keys; duplicate source match IDs are checked in the generated audit.
3. Added persistent `match_quality_flags`; source values remain untouched and suspicious rows are excluded from the baseline.
4. Added chronological, source-separated WTT Elo pre-match features. Matches on the same date share prior-date ratings to avoid same-day leakage.
5. Added automated audit and feature exports to the GitHub Actions database artifact.

The current WTT source audit flags four winner-versus-set-score disagreements and three records with fewer than three set wins (six distinct matches; one record meets both conditions). The WTT source's `best_of=7` field conflicts with the common observed 3-win match endings, so it is documented rather than blindly enforced.

The first simple Elo benchmark is a baseline only. It is not a fitted machine-learning model and should not be used as a standalone betting signal. The next modeling phase should compare this benchmark with a strictly chronological holdout, calibration checks, player inactivity/recency, and competition-specific form features before any pick is considered.


## Live-update phase status (2026-11-20)

### Implemented: supplementary source monitoring
- Added `scripts/probe_pongiq.py` to call the documented public PongIQ events endpoint, validate the response envelope and event list, preserve the raw response, and emit a health report.
- Added `.github/workflows/monitor-pongiq.yml`: scheduled every six hours, with manual dispatch and a push-triggered test. The workflow uploads the snapshot and report as a 14-day artifact.
- This is a source-health/discovery monitor, not a live professional-results importer. It does not change player records or feed community matches into the WTT prediction model.
- 11EDGE is not an automated source: its 2026-04-19 terms prohibit scraping, copying, or massive redistribution. No automated extraction is permitted by this project.

### Remaining before true record updates
1. Confirm a stable, permitted feed for professional match results across the target leagues.
2. Validate event and match schema with real completed records, including retirements, walkovers, doubles/team ties, and format variations.
3. Add a separate source-scoped incremental importer with idempotent match keys, immutable raw snapshots, duplicate checks, and rollback on invalid batches.
4. Recompute player records, recent form, head-to-head, shared-opponent history, and Elo strictly as of each match timestamp.
5. Add a freshness status and last-successful-import timestamp to prediction outputs.
6. Enable scheduled imports only after the source adapter passes fixture tests and a live dry-run.

**Current status: monitoring workflow implemented; automatic player-record updates are not yet enabled.** This avoids falsely advertising the database as live or contaminating the professional training set with unverified community events.
