# Player identity resolution

Keep every provider's player ID source-specific. Do not merge IDs based on name resemblance or one coincidental result.

Compare:
1. Competition/league.
2. Match date, accounting for timezone differences.
3. Match start time, if available.
4. Opponent.
5. Set score and game-point scores, if available.
6. Multiple independent matches for the same candidate player.

Statuses:
- candidate: plausible but not established.
- verified: at least two independent records agree, with no contradictory evidence.
- rejected: evidence conflicts or disproves the candidate.

Store the candidate name, both source IDs, evidence records, timezone assumptions, and reviewer/date in identity_links. Never overwrite original IDs or raw source rows.