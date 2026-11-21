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


## Phase 11 — European and official historical source qualification (2026-11-20)

### ITTF historical championships archive — qualified, not yet ingested
- Official ITTF page advertises individual-event World Championships results from 1926 across men's singles, women's singles, men's doubles, women's doubles, and mixed doubles.
- The archive explicitly starts at the Round of 16; it is not a complete draw archive. ITTF also acknowledges missing scores and requests corrections from readers.
- The public page returned HTTP 403 to automated retrieval during this review. The source is therefore documented as a high-value manual/download qualification target, not as an available automated feed.
- Before import: obtain the underlying files through an allowed download route, inspect file formats and per-game score depth, record hashes and retrieval metadata, check reuse/attribution terms, and keep doubles separate from individual singles.

### ITTF Results database — useful player-history validation, not a bulk feed
- ITTF's results platform exposes player profiles and match-history search; ITTF's own 2018 description says results were then available from 2008 onward, with coverage still expanding.
- Public search indexing exposes historical event and winner information, but the player-matches area can require registration/login. Do not automate authenticated scraping or assume a public display grants bulk-reuse rights.
- Use for targeted independent corroboration and player identity review only until a documented bulk export/API and reuse terms are confirmed.

### European Table Tennis Union — strong candidate for a separate event source
- ETTU's official historical announcement documents European Championships results from 2008, European Youth Championships from 2010, U21 events, and Youth Top 10; it describes player results and head-to-head queries.
- The current ETTU past-events archive exposes many recent event result pages. Public visibility is established, but a stable bulk endpoint/export and reuse terms for automated ingestion have not yet been verified.
- Next qualification step: test a small set of official event-result pages manually, identify whether completed singles matches expose set scores and stable match identifiers, then request/confirm permitted reuse before writing an importer.

### Historical European Table Tennis Information System (ETTIS) — discovery only
- ETTIS advertises historical European results from 1926–2006, but it is a community historical database rather than an official governing-body feed. Provenance, completeness, and reuse rights require separate verification.
- It may be used to discover event names and corroborating records; do not ingest into the canonical database until source-level provenance and permissions are documented.

### Phase 11 decision
No new source rows are imported in this phase. The ITTF page's 403 response, partial-round coverage, missing scores, and unresolved reuse conditions make an automated import unsafe. ETTU is the next best target for a bounded manual schema/terms review. Keep all these sources separate from DataSportsAPI and WTT until acceptance checks pass.


## Phase 14 — Free independent-source qualification (2026-11-21)

A fresh source review identified three additional candidates with different coverage profiles:

- **PongIQ:** a no-key, read-only API for published tournaments hosted on its platform. The public developer contract exposes category match lists and per-game score arrays, plus event draws and standings. It is potentially useful for tournament-scoped results and corroboration, but not a global professional feed. Confirm event provenance, historical retention, and reuse conditions before import; respect the provider's caching guidance.
- **Table Tennis API / DeveloperData.net:** free tier offers 50 calls/day and results from December 2024 onward, with match/event/player/result-level information. The provider reserves per-game scores and duration fields for paid tiers. It could independently validate winners and discover coverage but cannot provide the full set-score history needed by the simulator. It requires a user-created free key, so integration is deferred until the user provisions one.
- **U.S. Table Tennis Hall of Fame Archive:** a public historical archive spanning U.S. Opens/Nationals, Olympic Festivals, international results, college, MLTT, Olympic/Paralympic and Pan Am collections. The public landing page highlights finals, champions and career records; match-level completeness, set scores and bulk reuse rights remain collection-specific and unverified. Use only for targeted corroboration until assessed.

### Phase 14 decision
Do not ingest any candidate source yet. Keep the existing free DataSportsAPI feed as the recent results backbone, with its own source-isolated histories and no model promotion until a credible chronological holdout exists. Sample PongIQ next because it is publicly accessible without a key and appears to expose per-game scores; accept only published, completed, singles matches with event/match IDs, source timestamps and adequate score detail. Do not exceed provider caching guidance. Table Tennis API remains optional and requires a user-provisioned free key; do not ask for or store credentials in repository files. The U.S. archive is a targeted history/corroboration source, not assumed to be a complete match dataset.
