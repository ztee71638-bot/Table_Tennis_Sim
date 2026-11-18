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
