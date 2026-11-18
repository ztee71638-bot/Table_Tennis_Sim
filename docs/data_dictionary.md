# Data dictionary

- sources: provenance, source URL, license, and access notes.
- players: one record per source-native player identifier. A human may have multiple rows across sources until identity is verified.
- matches: match date/time, competition, players, sets, winner, and original row payload.
- match_games: per-game point scores linked to a match.
- player_stats_snapshots: dated ratings/statistics such as Elo and solidity.
- identity_links: candidate, verified, or rejected links between source-specific player records.
- import_log: file hash, row counts, import status, and notes.

Preserve source date/time values and document timezone assumptions. Missing values remain NULL; never fill them with guesses.