# Independent identity evidence audit

The next identity-review stage enriches the manual queue with public-profile evidence and source-specific research hints.

## What is corroborated

The current WTT queue contains three public-name matches with independent profile references:
- Ganghyeon Park: Butterfly Korea player profile.
- Honoka Hashimoto: Japan Table Tennis Association national-team profile.
- Kaho Akae: ITTF player profile.

These sources corroborate that the displayed full names correspond to real table-tennis players. They do **not** contain the DataSportsAPI source-player IDs, so they do not prove that a particular abbreviated database row belongs to that person.

## What remains unverified

Every source-player ID remains unverified and every decision remains `HOLD`. For the other 47 entries, the audit emits a targeted search hint rather than pretending a source was found. Setka Cup searches are directed toward its public participant profiles; Czech Liga Pro searches require an independent official competition record or federation profile.

To approve a source ID, a reviewer must compare independent competition-level evidence such as event date, opponent and result/score. Name similarity, competition membership, H2H counts, or a public biography alone are insufficient. The ambiguous Jan Szotkowski candidates must be separately disambiguated. No script in this phase changes player IDs, merges records, modifies matches, or changes simulator predictions.

Outputs:
- `polymarket_identity_evidence_audit.csv`: per-candidate evidence, source links, targeted search hints, and explicit HOLD status.
- `polymarket_identity_evidence_report.json`: counts and safety summary.

The public references are research leads, not endorsements or proof of a database identity link.


## Match-level corroboration added

The evidence generator now checks researched independent result records against the raw DataSportsAPI snapshots. It requires the same competition date, both source-scoped participant IDs, opponent, and every set score in order. The current research set contains four candidate names (Alesh Bayer, Daniel Tuma, Erik Mares, and Jakub Pilch) and six candidate-perspective match correlations across the two Bayer–Tuma meetings, Mares–Postelt, and Pilch–Mares.

Independent references used for this initial batch:
- Score-Tennis: Bayer–Tuma results on 19 November 2026: https://score-tennis.com/games/alesh-bayer-daniel-tuma-1171995/ and https://score-tennis.com/games/alesh-bayer-daniel-tuma-1171681/
- Score-Tennis: Mares–Postelt result on 19 November 2026: https://score-tennis.com/games/erik-maresh-tomas-postelt-1171068/
- PongData: Pilch match archive: https://pongdata.com/players/pilch-j-10xql5o5bp8/matches?year=2026

These exact match fingerprints are strong corroboration, not final approval. All four candidate IDs remain `unverified` and `HOLD` pending human review. The script does not update player identities or simulator records.
