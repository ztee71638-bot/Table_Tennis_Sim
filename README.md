# Table Tennis Sim — Historical Database

A source-aware, reproducible database for table-tennis match results, player records, Elo ratings, and simulation research.

## Project rules

- Keep raw source files unchanged in `data/raw/`.
- Preserve each source's original player IDs. IDs are namespaced by source; never assume IDs from different datasets identify the same person.
- Store identity matches as candidates until verified by multiple independent match records (date, competition, opponents, score, and time where available).
- Keep source/license/provenance details with every import.
- Never fabricate missing names, scores, dates, or match results.
- Use a strict PASS / no-bet decision when evidence is weak.

## Known data sources

See [SOURCES.md](SOURCES.md) for source links, known coverage, licensing/access notes, and limitations.

| Source | Known content | Limitation |
|---|---|---|
| SCORE Setka Cup CSV | 7,851 named matches reported | CSV dates previously observed as 2022-06-10 to 2022-07-08; verify before use |
| Lathise public Elo sample | 2,000 pre-match Elo rows, opaque IDs | Sample only; full dataset separately licensed |
| PongData | Public named-player profiles/results | No confirmed bulk export |
| TT Data Lab | Named profiles and historical archive | Bulk access must be requested/confirmed |
| Table Tennis API | Named records and recent matches | Free tier limited; archive may be paid |
| TT Lossbeater | League/player API and training data | Account/API access; free bulk access unconfirmed |

## Repository layout

- `data/raw/` — original source downloads, unchanged
- `data/processed/` — normalized exports
- `sql/schema.sql` — SQLite schema
- `docs/` — data dictionary and identity review rules
- `scripts/` — import and validation utilities

## Important current status

This repository currently contains the project structure, source register, and database schema. **It does not yet contain the actual match CSV datasets or a populated SQLite database.** Those must be acquired and imported separately.

## Identity policy

A name-to-ID link is not verified because one name and one match score look similar. Require at least two independent matching records, ideally including date, league, opponents, score, and time. Keep uncertain matches in a review queue.

## Licensing

This repository's code and documentation do not grant rights to redistribute third-party datasets. Follow each dataset's license and terms.