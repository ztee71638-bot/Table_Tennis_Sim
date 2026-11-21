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


## Ambiguous Jan Szotkowski candidate: additional independent result correlations

The PongData player page and its 2026 match archive list four 19 November results for Jan Szotkowski that match DataSportsAPI fixture records exactly by date, opponent source ID, and every set score: Tadeas Zika (fixture 1140596), Ondrej Paril (1140589), Radovan Polasek (1140575), and Michael Sedlacek (1140604). All four map to candidate source ID 633703 (displayed as “Szotkowski J.”); the other candidate ID 629357 (“Jan S.”) does not match these four fingerprints. Reference: https://pongdata.com/players/szotkowski-j-98geod1q0w/matches?year=2026

This is materially stronger evidence for candidate 633703, but the profile does not publish the DataSportsAPI ID. Because the Polymarket name still has two candidate rows and the source ID namespaces are separate, the automated audit deliberately leaves both candidates unverified and the decision HOLD. A reviewer must make the final identity decision; no source ID or simulator record is changed by this evidence.


## Extending match-level checks across competitions

The match fingerprint validator now reads the competition name from each independently researched record rather than assuming every result belongs to Czech Liga Pro. This enables safe source-isolated checks for Setka Cup as well.

Additional evidence added in this phase:
- Michal Regner: one 19 November 2026 match against Sebastian Kasnik, exact date/opponent/set scores correlated to DataSportsAPI fixture 1140674. Independent record: https://pongdata.com/players/regner-m-lvnv22cdhn/matches?year=2026
- Kozachuk Ivan: two 19 November 2026 Setka Cup results, against Denys Shcherbak and Denys Pesternikov, exact date/opponent/all set scores correlated to fixtures 1141253 and 1141267. Independent record: https://24live.com/page/sport/participant/table-tennis-22/1006413

The Setka Cup results demonstrate that the evidence validator now checks the candidate's own competition scope, rather than applying a Czech-only restriction. All three new result correlations remain human-review evidence only; no ID is verified, approved, or merged.


## Additional Setka Cup candidate: Kovalchuk Nazarii

Bettrails' public player archive lists Kovalchuk Nazarii's 19 November 2026 Setka Cup match against Rak Serhii as a 1–3 loss, with candidate-perspective set scores 11–9, 5–11, 4–11, 6–11. Those details correlate exactly with DataSportsAPI fixture 1141249 for source player ID 58534 against opponent ID 274477. Independent reference: https://bettrails.com/tenis-de-mesa/jugador/kovalchuk-nazarii?lang=en

The evidence is recorded as a match-level correlation for human review only. The DataSportsAPI source ID remains unverified and the identity decision remains HOLD; this evidence does not authorize a merge or alter simulator records.


## Additional Czech Liga Pro candidate: Martin Stefek

PongData's public Martin Stefek match archive lists the 19 November 2026 result against Tomas Andrle with Stefek-perspective set scores 11–7, 4–11, 11–6, 13–11. These details correlate exactly with DataSportsAPI fixture 1140672 for source player ID 625477 against opponent ID 630794. Independent reference: https://pongdata.com/players/stefek-m-k9gqp5qvz3

This match-level correlation is surfaced for human review only. Source player ID 625477 remains unverified and the identity decision remains HOLD.
