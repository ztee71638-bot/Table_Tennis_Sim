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

### DataSportsAPI table-tennis results (rolling recent window)
- Landing page: https://datasportsapi.com/sports/table-tennis/
- API endpoint: `https://api.datasportsapi.com/v2/fixtures`
- Imported by `scripts/import_datasportsapi.py`; the scheduled workflow refreshes the latest seven days and retains daily raw JSON snapshots.
- The free plan is used with the existing `DATASPORTSAPI_KEY` GitHub Actions secret. No paid plan is assumed.
- Terms checked 2026-11-16: data may be used in the project's own apps/products/analysis; raw feed resale or redistribution is prohibited.
- The 2026-11-14 through 2026-11-20 saved update contained 6,337 singles results across Czech Liga Pro (940), Setka Cup (1,526), TT Elite Series (2,023), TT Cup (1,119), and Liga Pro (729). These are recent-window counts, not full historical totals.
- Singles/doubles/team/unknown classifications are stored separately. Only completed individual singles are used for individual-player form and H2H; ambiguous/team/doubles records are excluded from those calculations.
- The main database build now replays the rolling recent import when the secret is configured, then reconciles Polymarket player listings against the matching competition. See `docs/domestic_league_coverage.md`.

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


### Polymarket US public listings (discovery only)
- Public API: https://gateway.polymarket.us
- Official Python SDK: https://github.com/Polymarket/polymarket-us-python
- Integrated by `scripts/scan_polymarket_table_tennis.py` during the database build.
- Searches public event listings for table-tennis terms and compares explicitly named players with source-scoped player display names.
- No API key or account permissions are required. No account, wallet, portfolio, or trading endpoints are used.
- Event/market snapshots are retained as raw discovery data; they are not imported as historical match results. Possible name matches are review-only and never auto-merged.
- See `docs/polymarket_us_integration.md` for output files and limitations.

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


## Newly qualified historical research candidates (reviewed 2026-11-20)

### ITTF Past World Championships Results
- Official landing page: https://www.ittf.com/history/documents/past-world-championships-results/
- Advertises individual-event results from 1926 for men's singles, women's singles, men's doubles, women's doubles, and mixed doubles.
- Coverage is limited to matches from the Round of 16 onward; ITTF explicitly notes missing scores.
- Automated retrieval returned HTTP 403 during this review. No files have been downloaded or imported. Reassess only through a permitted manual download or an authorized export, and preserve the coverage/missing-score limitations.

### ITTF Results database / player profiles
- Player search and profiles: https://results.ittf.link/players-profiles
- ITTF's 2018 description reported player/tournament statistics and results coverage from 2008 at that time: https://www.ittf.com/2018/01/09/statistics-page-now-available/
- Useful for targeted independent corroboration and identity review. The player-matches area may require registration; no automated login, scraping, or bulk reuse is assumed.

### European Table Tennis Union (ETTU) results archive
- Official past-events archive: https://www.ettu.org/past-events/
- ETTU's 2017 announcement documented European Championships results from 2008, European Youth Championships from 2010, U21 and Youth Top 10 events, plus player and head-to-head queries: https://www.ettu.org/en-n-news-2017-june-new-statistic-data-section-available-on-ettu-web-page/
- Public event pages are a promising source for a separate European event collection. Stable bulk export/API access, per-match set-score availability, and automated reuse permissions have not yet been verified. Manual qualification only; no importer enabled.
- Privacy/policy page: https://www.ettu.org/privacy-policy/ . Public publication of sporting results is described, but that alone is not treated as a bulk data license.

### European Table Tennis Union (ETTU) — current past-events archive and legacy statistics platform
- Official current archive: https://www.ettu.org/past-events/ . It lists competitions and result links across 2022–2026, including European Championships, youth events, club competitions, and Europe Top 16. Many result links lead to ETTU.tv or third-party competition-management hosts; match-level score completeness and stable export formats vary by event.
- ETTU's privacy and policy page states that it publishes results, rankings, statistics, reports, and historical records, and that some results and sporting records may be licensed, distributed, or otherwise used. This is not a blanket bulk-reuse licence for our private database or model training; obtain written permission for any systematic collection or reuse beyond manual research.
- ETTU's 2017 announcement described a legacy results/statistics platform at https://results.ettu.site, with European Championships results from 2008, Youth Championships from 2010, U21, Europe Top 10, player queries, and head-to-head search. The legacy host was not accessible during this review, so current availability and downloadable match-level completeness remain unverified.
- Qualification: useful official event discovery and targeted result corroboration. Do not scrape, bulk-download, or import until stable permitted access, score coverage, and reuse rights are confirmed.

### European Table Tennis Information System (ETTIS)
- https://ettis.info/
- Community historical database advertises European results from 1926–2006. Use for discovery and targeted corroboration only; source provenance, completeness, and reuse terms remain unverified.


## Additional free independent-source candidates (reviewed 2026-11-21)

### PongIQ public API — free, read-only, tournament-scoped
- Developer documentation: https://www.pongiq.app/developers
- Public endpoints include published events, event categories, locked knockout draws/results, group standings, category match lists with scores, individual match details, and public ratings.
- No API key is currently required. The provider asks clients to cache responses and avoid polling faster than the data changes; published events only are exposed.
- Coverage appears to be tournaments using the PongIQ platform, not a comprehensive global professional circuit feed. Sample payloads include per-game scores, but completed historical coverage, stable long-term retention, terms for bulk reuse, and event/player provenance need verification before ingestion.
- Qualification: good candidate for a separately scoped tournament feed and independent match corroboration. No importer or automatic identity links authorized.

### Table Tennis API (DeveloperData.net) — free tier, account key required
- Official service: https://tabletennisapi.com/
- Published free tier: 50 calls/day, no payment card; date-filtered matches/results, events, player lookup, world rankings, and individual match retrieval. Coverage is advertised from December 2024 for professional events across senior, youth, and para disciplines.
- Free tier does not include full per-game scores/durations (these are advertised for paid tiers); its match records include event, date, discipline, round, status, best-of, sides, match score, and winner.
- This could support independent winner/result cross-checks, event coverage discovery, and opponent history, but is not a substitute for set-by-set scores. It requires a separate free account/key and 50-call daily budget. Do not request or store the key until user explicitly provisions it.
- Qualification: no integration until an account key is provided and a small sample is inspected. Keep source-specific IDs and all links isolated.

### U.S. Table Tennis Hall of Fame — The Archive
- Official project page: https://results.ustthof.org/
- Public archive covers U.S. Open/Nationals, U.S. Olympic Festival, international results, college champions, MLTT, Olympic/Paralympic and Pan Am history, and player/finalist profiles.
- It is a valuable discovery and identity-corroboration source for historical U.S. players and major events. The public overview emphasizes finals, champions, and career results; completeness of individual match rows, set scores, bulk downloads, and reuse terms must be assessed on a collection-by-collection basis.
- Qualification: targeted historical corroboration only; do not treat title/finalist records as a complete match-history dataset or bulk-scrape the site.

### Free-source prioritization
1. Existing DataSportsAPI free daily feed remains the primary recent result feed; maintain the separate classification and chronological backtest gate.
2. PongIQ is the strongest no-key candidate to sample for platform tournament match-level scores, but should remain a distinct source and be used only for tournaments with clear provenance.
3. Table Tennis API can offer independent result-level validation if the user provisions a free key; the free plan lacks full game-score detail and is limited to 50 calls/day.
4. The U.S. Hall of Fame archive is best suited to targeted historical U.S. identity/event corroboration, not a universal results importer.

No data from these three candidates was imported in this qualification pass. No paid plan, API key, scraping, or cross-source identity merge was used.


### Table Tennis API — binding reuse restriction review (2026-11-21)
- Terms: https://tabletennisapi.com/terms (last updated 2026-10-27).
- The terms allow use of API data in one's own apps/sites, but prohibit reselling, redistributing or republishing the data itself, downloading it in bulk to rebuild a database, or using it to build a competing product. They direct users to request a licence for uses beyond those permissions.
- Therefore the free key is **not** approval to bulk-import historical results, build our own replicated match database, or train a model from a bulk export. Do not wire it into the database ingestion workflow or persist bulk response data unless DeveloperData provides explicit written permission covering the proposed private research database and model training.
- The user's non-commercial research-access request is awaiting a substantive response; the automated acknowledgement is not permission. A free account/key by itself does not override the terms.
- Until written permission is received, keep this source as documentation-only. Do not place the key in GitHub Secrets or call bulk endpoints for the project. Never put a key in source control, logs, or chat.
