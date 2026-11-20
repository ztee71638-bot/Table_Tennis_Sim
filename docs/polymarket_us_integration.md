# Polymarket US table-tennis discovery

## Purpose

Use Polymarket US public listings as a discovery source for table-tennis players, opponents, competitions, event schedules, and market structures. This is a research feed for identifying gaps in the simulator's sports-data coverage; it is not an odds-driven prediction model.

## Access and safety

- Uses the official Polymarket US Python SDK and public API only.
- No API key, profile access, account credentials, portfolio permissions, wallet connection, or trading permission is needed.
- The scanner does not call authenticated endpoints and cannot place orders.
- Polymarket events and markets are stored as source snapshots. They are not inserted into the historical match database.
- Similar player names are only review suggestions. No cross-source player identity is automatically merged.

## How it runs

The scanner is called during the existing database build after the source imports and database audit:

```bash
python -m pip install polymarket-us
python scripts/scan_polymarket_table_tennis.py
```

It searches public listings for table tennis, ping pong, WTT, Setka Cup, TT Elite, Czech Liga Pro, and TT Cup. Results are deduplicated by event ID or slug.

## Outputs

- `data/raw/polymarket_us_table_tennis_events.json`: full raw event payloads and retrieval timestamp.
- `data/processed/polymarket_us_events.csv`: event schedule, status, search terms, and parsed player pair where explicit.
- `data/processed/polymarket_us_markets.csv`: market identifiers, titles, status, volume, and liquidity where supplied.
- `data/processed/polymarket_us_player_coverage.csv`: exact name matches, possible spelling matches for manual review, and players not found in the current database.
- `data/processed/polymarket_us_scan_report.json`: counts, unparsed titles, and safety notes.

## Domestic-league player reconciliation

The main database build also imports the rolling DataSportsAPI results when the existing `DATASPORTSAPI_KEY` secret is configured. The reconciliation step compares each Polymarket player against source-scoped DataSportsAPI player IDs, prioritizing the event's competition tag.

It produces:
- `data/processed/polymarket_datasportsapi_player_coverage.csv`
- `data/processed/polymarket_datasportsapi_matchup_evidence.csv`
- `data/processed/polymarket_datasportsapi_reconciliation_report.json`

The report includes each candidate's match volume, competition-specific W-L record, last recorded match date, and same-competition historical H2H evidence where both candidates are unique. Initial-only and ambiguous matches remain review-only. No identity links are created and no simulator results or predictions are changed. If the API secret is absent, the report clearly marks the source as not loaded.

See `docs/domestic_league_coverage.md` for league counts, date coverage, and free-data limits.

## Interpretation limits

- Search results may omit listings or return false positives; only active, non-closed events with Polymarket's explicit Table Tennis category/sport tag are retained. The report counts excluded search noise.
- Player-pair parsing is attempted only when a title explicitly contains a `vs` or `versus` separator.
- A Polymarket market listing is not proof that a player is active in a particular professional league.
- Name comparison ignores token order and can flag initial-abbreviation or close spelling matches for manual review. Even exact display-name matches do not prove two source records are the same person.
- This first integration is a one-time scan per database-build run. It does not yet stream live prices or automatically alter simulator predictions.
