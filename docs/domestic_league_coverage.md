# Domestic league coverage and Polymarket player reconciliation

## Existing recent-result source

The project has an automated, read-only DataSportsAPI integration. The provider's human written reply on 2026-11-21 expressly permits retrieval within the seven-day Free-plan window, private retention of fetched records without a stated retention period, derived statistics/H2H/ratings, internal model training/testing/validation, and display of original derived outputs, including commercial use. No separate licence is required for that described scope. Raw records may not be resold, sublicensed, redistributed as a feed/API, or published in bulk as a substitute for the provider's service. The provider appreciates but does not require attribution. The Free plan allows 1,000 requests/day during beta and 100/day afterward.

Latest scheduled update #39 (2026-11-23 UTC) retained 10 daily snapshots and classified 9,318 records; 9,205 were eligible individual singles, 113 were excluded from individual-player records, and 9,176 clean singles remained after 29 invalid results were excluded. These are cumulative rolling-feed/import counts, not full historical coverage. The older dated breakdown below is retained as a historical snapshot, not the latest total:

| Competition | Matches |
|---|---:|
| Setka Cup | 1,526 |
| TT Elite Series | 2,023 |
| TT Cup | 1,119 |
| Czech Liga Pro | 940 |
| Liga Pro | 729 |
| **Total** | **6,337** |

These are a seven-day recent-results window, not a complete historical archive. Daily JSON snapshots are retained in `data/raw/datasportsapi/` so a later rebuild can replay the saved period. The separate SCORE Setka Cup dataset adds 7,851 historical rows dated 2022-06-10 through 2022-07-08; it is not interchangeable with the recent feed.

The latest source classification audit reports 9,318 classified records, with 9,205 eligible for individual-player records and 113 excluded as non-individual/ambiguous. After validation, 9,176 clean individual singles remain; 29 invalid results were excluded. Only clean singles are used in individual player form and matchup evidence.

## Build integration

The main database build now attempts to import the latest DataSportsAPI window when the existing `DATASPORTSAPI_KEY` GitHub Actions secret is configured. It then:

1. Classifies singles, doubles, team, and ambiguous fixtures.
2. Audits classification counts and representative examples.
3. Builds source-isolated player form and opponent records.
4. Runs the existing DataSportsAPI quality/backtest checks.
5. Compares current Polymarket table-tennis listings with DataSportsAPI players in the matching competition.

If the key is not configured, the build warns and emits `source_not_loaded` statuses rather than claiming those players are absent.

## Reconciliation outputs

- `polymarket_datasportsapi_player_coverage.csv`: candidate player IDs, competition-specific match counts, W-L record, and latest recorded date.
- `polymarket_datasportsapi_matchup_evidence.csv`: each listed Polymarket matchup, competition scope, both candidate records, and same-competition historical head-to-head count/date.
- `polymarket_datasportsapi_reconciliation_report.json`: source availability and summary counts.
- `polymarket_identity_review_queue.csv`: unresolved initial/ambiguous name candidates, all candidate source IDs, and blank reviewer decision fields.

Names are normalized for accents and order, and a surname-plus-initial candidate is allowed only when all name tokens align. Candidates are scoped to the listed competition where possible. Exact names are preferred over initial-only candidates. Multiple possible IDs remain ambiguous.

A candidate match or historical head-to-head record is supporting evidence, not proof of identity. The reconciliation script does not insert identity links, merge players, alter match records, or change model predictions. Human review and independent evidence are required before any identity link is verified.

## Free-data boundaries

- DataSportsAPI's Free plan is used for the rolling recent-results import. Written permission received 2026-11-21 explicitly covers private retention, derived statistics, internal model training/testing/validation, and display of original derived outputs, including commercial use. No separate licence is needed for that scope. Raw-feed resale, redistribution, and bulk raw publication that substitutes for its service remain prohibited. The API key stays in GitHub Actions Secrets. The source-specific chronological holdout is 55.10% versus 55.56% Elo, so this model is not promoted.
- TT Data Lab advertises deeper historical CSV/JSON data across Czech Liga Pro, Setka Cup, TT Elite Series, and other circuits, but pricing is on request. No paid access or bulk export has been assumed.
- TipManager's terms restrict portal content to personal, non-commercial use and prohibit reproducing or passing on its data without prior authorization. It is therefore not scraped or imported.
- Table Tennis API's free plan is useful for professional event discovery and recent results, but its full archive is paid and its published coverage does not establish coverage of Czech Liga Pro or Setka Cup.

## Validation

The reconciliation tests cover:
- Order-independent names and initial abbreviations.
- Avoiding false matches based on a shared first initial alone.
- Ignoring birth-year suffixes in displayed names.
- Competition scoping for Setka Cup variants.
- Aggregating a player's complete available match history.
- Attaching H2H evidence without auto-merging identities.
- Explicitly reporting when the DataSportsAPI source was not loaded.


## Identity review phase

The build emits a manual review queue for initial-abbreviation and ambiguous candidates. Each row includes the full candidate option list, source-scoped player IDs, competition scope, and blank fields for the reviewer to record independent evidence, a decision, and reviewer details. The queue never preselects or approves an identity. Name similarity and head-to-head history alone are not sufficient evidence. No player links or match rows are modified.
