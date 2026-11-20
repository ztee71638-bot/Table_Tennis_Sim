# New provider import readiness checklist

This document is the required gate before a new table-tennis provider is connected to the database.

## Current state

- Existing licensed/imported sources continue to build through `.github/workflows/build-database.yml`.
- WTT men and women use `scripts/import_wtt.py`; archive checksum and exact row counts are validated.
- The supplementary PongIQ probe is monitoring/discovery only. It does not write matches into the professional training database.
- The Table Tennis API free tier requires a provider-issued API key and exposes recent results (yesterday onward); no key is stored in this repository yet.
- 11EDGE bulk copying/scraping is prohibited by the terms currently documented in `SOURCES.md`; do not create an automated scraper.

## Required provider information

Before writing an adapter, obtain and record:
1. Official API/export documentation and exact endpoint or file location.
2. Written licence/permission covering private storage, derived statistics, and model training.
3. Free-tier limits, authentication requirements, rate limits, and retention conditions.
4. Event coverage, date range, disciplines, competition types, and refresh schedule.
5. Real sample payloads for completed matches, walkovers, retirements, doubles, team ties, and missing scores.

## Import contract

Every adapter must:
- Use a separate `sources.source_key` for the provider; never merge provider-native player IDs.
- Preserve every original response/page as raw JSON or a source snapshot with retrieval timestamp and SHA-256.
- Use provider match IDs as idempotent keys within that source.
- Validate date, event, player sides, winner, set score, and game-score shape before a transaction is committed.
- Reject or quarantine malformed rows; never infer missing names, IDs, winners, or scores.
- Record import counts, duplicates, rejected rows, and a clear success/partial/failure status.
- Handle pagination and free-tier quotas conservatively; never poll faster than the documented limit.
- Separate professional, domestic, youth, para, doubles, team, and community event classes.
- Roll back a batch if structural validation fails.
- Run a dry-run against saved fixtures before enabling scheduled ingestion.

## Player identity and deduplication

- Keep provider IDs source-scoped.
- Do not join identities on name alone.
- Candidate identity links require corroborating evidence such as country, date of birth where lawfully available, competition history, and overlapping results.
- Exact provider match IDs are the primary duplicate key. Cross-source duplicate candidates need date, event, player sides, and score agreement; retain both raw source records and record the linkage evidence.
- Do not collapse records with conflicting scores or uncertain player identities.

## Freshness and model safety

- Store last successful retrieval/import timestamp and source health separately from match date.
- A source outage must not be mistaken for zero matches.
- Update player records only from validated completed matches.
- Compute every historical feature strictly as of the prediction timestamp; never use same-day/future outcomes.
- Prediction output must show data freshness and warn or PASS when coverage is stale or incomplete.

## Activation gate

A new adapter may be enabled only after:
- Written use permission/licence is recorded.
- Free access is confirmed and no payment is required.
- A sample payload is inspected and fixtures pass.
- Database integrity, duplicate, and identity checks pass.
- A successful dry-run is reviewed.
