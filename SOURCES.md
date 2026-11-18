# Data source register

This project is free-only. A source is not automatically imported just because it is publicly viewable. Before ingestion, verify that the data can be downloaded, that the terms permit the intended use, and that the fields are useful for match-level analysis.

## Imported and currently automated

### SCORE Setka Cup CSV
- Landing page: https://data.scorenetwork.org/table_tennis/table_tennis_sept2022.html
- Raw CSV: https://raw.githubusercontent.com/SCOREnetworkorg/sports-data-repository/main/data/table_tennis-sept2022.csv
- Imported by `scripts/build_database.py`.
- Reported/imported: 7,851 named match rows with dates/times, set scores, and game-point scores.
- Date discrepancy: despite the page title, inspected rows showed dates 2022-06-10 through 2022-07-08. Verify before analysis.
- Check the source repository license before redistribution.

### Lathise public Elo sample
- GitHub: https://github.com/lathise2025/table-tennis-elo-dataset
- Hugging Face: https://huggingface.co/datasets/lathise/table-tennis-pre-match-elo-ratings
- Imported by `scripts/build_database.py`.
- Public sample: 2,000 pre-match Elo observations with opaque player IDs, league, date, result, and set score.
- Sample license identified as CC BY 4.0. The full dataset is separately licensed; do not assume the sample license applies to it.
- No verified real-name mapping is included in the sample.

## High-priority free expansion candidates

### Racket Sports Multi-Dataset (WTT men and women)
- Repository: https://github.com/Li02003121/racket-sports-dataset
- Dataset DOI: https://doi.org/10.17605/OSF.IO/PJUW8
- The project README reports 5,442 men's and 4,850 women's WTT match records for 2022-2025.
- README states data license CC BY 4.0 and code license CC0 1.0.
- Important limitation: the GitHub repository currently contains documentation/scripts, not the advertised match CSV files. Locate and verify the OSF downloadable files and metadata before automating import. Do not treat this as imported yet.

### ITTF World Championships historical results
- Landing page: https://www.ittf.com/history/documents/past-world-championships-results/
- Official historical event results from 1926; the page says only matches from the Round of 16 onward are included and some scores are missing.
- Candidate for a separate historical international dataset after the files and reuse terms are checked. Not yet imported.

### 11EDGE
- https://11edge.io/
- Site advertises 109,000+ matches since 2017, 5,000+ players, and 180+ competitions, including WTT and national leagues; full history is available with a free account.
- Free bulk export, automation permission, and reuse terms are not yet verified. Do not scrape or bulk-download until confirmed.

### PongIQ public API (supplementary, not assumed professional)
- Developer documentation: https://www.pongiq.app/developers
- Free, read-only API with no key currently required; exposes published events, categories, match scores, and rankings.
- Coverage depends on events using PongIQ; it is not a comprehensive professional-league feed. Keep any imported records tagged as community/tournament data unless competition status is independently verified.
- Respect caching guidance and future rate limits.

## Useful for discovery, but not free historical bulk feeds

### Table Tennis API
- https://tabletennisapi.com/
- Free key: 50 calls/day and yesterday-to-future results; historical archive since December 2024 is paid.
- Could be considered later for recent match coverage, but do not make paid calls or subscribe.

### TT Data Lab
- https://tt-data-lab.onrender.com/data-api.html
- Historical match history with set/point scores is offered as CSV/JSON; API pricing is on request. Public stats begin in 2022 and include Setka Cup, TT Elite Series, Czech Liga Pro, TT Cup, Masters, WTT, and Challenger.
- Request a no-cost sample/export only if available; no paid access authorized.

### TT Lossbeater
- https://docs.ttlossbeater.com/
- API/training examples cover Setka Cup, Czech Liga Pro, TT Cup, TT Elite Series, Setka Cup Women, and Challenger Series TT.
- Account/API key required; free bulk access is unconfirmed. No credentials or paid plan assumed.

### U.S. Table Tennis Results & History
- https://results.ustthof.org/
- Named U.S. event archive, including U.S. Open and Nationals. Candidate for a separate U.S. historical collection after downloadable files and terms are verified.

### Sportradar / SportsAPI
- https://developer.sportradar.com/
- https://sportsapi.app/sports/table-tennis
- Broad competition coverage is advertised, but full historical access is commercial or plan-limited. Not in the free acquisition path.

## Acquisition and quality-control rules
For every downloaded file/API feed, record source, exact URL/endpoint, retrieval date (UTC), original filename, SHA-256, license/terms, date coverage, competition coverage, row count, and import notes.

Keep separate source-scoped player IDs. Never merge players across providers based on a name alone. Preserve raw source rows. Record missing scores and incomplete dates rather than filling them with guesses. Deduplicate only with stable source IDs or strong multi-field evidence.

## Expansion order
1. Verify and obtain the advertised WTT 2022-2025 OSF dataset files.
2. Add official ITTF World Championships historical files where scores are available.
3. Investigate 11EDGE free account export and permitted use.
4. Evaluate no-cost recent-result APIs and supplementary tournament feeds.
5. Expand professional domestic leagues one provider/source at a time, with coverage and licensing documented.
