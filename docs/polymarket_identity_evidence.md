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
