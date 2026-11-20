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
- Download archive: https://osf.io/download/3f6ak/
- Imported by `scripts/import_wtt.py` as two separate source tables.
- Men's CSV: 5,442 match rows; women's CSV: 4,850 match rows; 2022-2025.
- Data license: CC BY 4.0; code license: CC0 1.0. Attribute the dataset to the Racket Sports Multi-Dataset project and DOI.
- OSF archive SHA-256 is checked before extraction. Expected row counts are checked before import.
- Source-native player IDs are retained separately for men and women; no cross-source identity merging is performed.
- Rankings/ranking points and several auxiliary fields are blank in the supplied CSVs. Match scores are parsed into set and game-point fields; the complete original row is preserved.
- GitHub Actions builds the database and imports these WTT rows into SQLite on each manual build.

### ITTF World Championships historical results
- Landing page: https://www.ittf.com/history/documents/past-world-championships-results/
- Official historical event results from 1926; the page says only matches from the Round of 16 onward are included and some scores are missing.
- Candidate for a separate historical international dataset after the files and reuse terms are checked. Not yet imported.

### 11EDGE
- https://11edge.io/
- Site advertises 109,000+ matches since 2017, 5,000+ players, and 180+ competitions, including WTT and national leagues.
- Terms of service (updated 2026-04-19): read access is public, but scraping, copying, or massively redistributing content is prohibited; raw sports data remains owned by third parties. This project therefore does not scrape, bulk-copy, or automate extraction from 11EDGE.
- It may be used for manual research and source discovery only. No export or redistribution rights are assumed.

### PongIQ public API (supplementary, not assumed professional)
- Developer documentation: https://www.pongiq.app/developers
- Free, read-only API; no API key required at the time checked. Published events, categories, match scores, and rankings are documented.
- Coverage depends on organisers using PongIQ; it is not a comprehensive professional-league feed. Example data includes local/community events and demonstration match payloads.
- The repository now runs a source-health probe every six hours and on manual dispatch. It saves a raw events snapshot and health report as a short-retention GitHub Actions artifact.
- The probe does not import these records into the professional WTT database. Event authenticity, category, match score schema, and reuse terms must be independently checked before a separate supplementary import is approved.
- Respect the provider's caching guidance and future rate limits.

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
