# Data source register

Access, coverage, and licensing must be rechecked before bulk downloading or redistribution.

## SCORE Setka Cup CSV
- Landing page: https://data.scorenetwork.org/table_tennis/table_tennis_sept2022.html
- Raw CSV previously identified: https://raw.githubusercontent.com/SCOREnetworkorg/sports-data-repository/main/data/table_tennis-sept2022.csv
- Reported: 7,851 matches and 18 columns, including named players, dates/times, set scores, game-point scores, and winner.
- Date discrepancy: despite the page title, previously inspected rows showed dates 2022-06-10 through 2022-07-08. Verify before analysis.
- Check the source repository license before publishing a copy.

## Lathise public Elo sample
- GitHub: https://github.com/lathise2025/table-tennis-elo-dataset
- Hugging Face: https://huggingface.co/datasets/lathise/table-tennis-pre-match-elo-ratings
- Sample: data/tt_ratings_sample_2000.csv; 2,000 rows with pre-match Elo/solidity and opaque player IDs.
- Sample license identified as CC BY 4.0. The full dataset is separately licensed; do not assume the sample license applies to it.
- No verified real-name mapping is included in the sample.

## Other named-data sources
- PongData: https://pongdata.com/ — public player profiles, rankings, results and H2H pages; no confirmed bulk export.
- TT Data Lab: https://ttdatalab.com/ — named profiles and historical match archive; bulk access may require a request/account.
- Table Tennis API: https://tabletennisapi.com/ — named records and recent matches; free tier is limited and archive access may be paid.
- TT Lossbeater docs: https://docs.ttlossbeater.com/ — league/player API and training data; account/API access required, free bulk access unconfirmed.
- U.S. Table Tennis Results: https://results.ustthof.org/ — named U.S. event history.
- Sportradar: https://developer.sportradar.com/ — authenticated/commercial sports data.

## Acquisition log
For each downloaded file, record source, exact URL, retrieval date (UTC), original filename, SHA-256, license/terms, date coverage, and import notes.