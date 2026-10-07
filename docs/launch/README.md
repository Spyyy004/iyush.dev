# Launch kit (M9) — drafts for M10

Drafts only — nothing here has been posted. Every number is checked against `~/dev/weather_football/findings/` (see the fact sheet at the bottom); change wording freely, not numbers.

| File | Channel | Entry point |
|---|---|---|
| [flagship-bruno.md](./flagship-bruno.md) | blog / LinkedIn article | the Bruno story, end to end |
| [reddit.md](./reddit.md) | r/FantasyPL-style football subs, r/soccer analytics threads, r/footballstrategy, r/datascience | Bruno → similarity vs prediction |
| [linkedin.md](./linkedin.md) | LinkedIn post | Manchester United case study |
| [x-thread.md](./x-thread.md) | X thread | Bruno → the surprising failure |
| [outreach.md](./outreach.md) | DMs / email to analysts | one finding + one link |

## Deep links (the site is the destination of each post)

| Hook | Link |
|---|---|
| Bruno → Serie A | https://iyush.dev/football/tools/similarity?player=bruno-fernandes&league=serie-a&seasons=3 |
| Manchester United 2024 | https://iyush.dev/football/case-studies/manchester-united-2024 |
| Similarity ≠ prediction | https://iyush.dev/football/research/transferability |
| "Big-game players" | https://iyush.dev/football/research/opposition |
| Home specialists | https://iyush.dev/football/research/home-advantage |
| Does it still hold? | https://iyush.dev/football/live |
| How we know | https://iyush.dev/football/methodology |

Add `?utm_source=reddit|linkedin|x|outreach&utm_medium=social&utm_campaign=launch` to see referral sources in GA4 (the pages keep working with extra query params).

## Funnel the site is wired for

- **Fan:** finding (homepage) → study → tool
- **Analyst:** study → methodology → tool
- **Recruiter:** case study → transfer calculator → methodology
- **Technical:** methodology → GitHub (`football/README.md`) → research
- **Employer:** research → tools → case study → About

GA4 events at each decision point: `study_open`, `study_complete`, `similarity_started` / `_completed` / `_compare` / `_shared`, `transfer_started` / `_completed` / `_shared`, `case_study_open`, `methodology_open`, `glossary_open`, `share_click` (channel), `github_click`, `linkedin_click`. Suggested GA4 setup in M10: mark `similarity_completed`, `transfer_completed`, `study_complete` and `share_click` as key events; build a funnel exploration `study_open → study_complete → similarity_completed | transfer_completed → share_click`.

## Fact sheet (verified)

- Data: 5 leagues, 2015/16–2024/25, 18,011 matches (18,008 analysed), 8,348 players, 525,328 player-matches.
- Home: same player +27% xG per minute at home; 0 of 4,665 players with a reliable personal home edge; past vs later home edge r = 0.018.
- Opposition: −13.8% xG per +1 SD of opponent strength; 0 of 23,022 player × metric estimates show individual resistance.
- Bruno (Study 4): robust Serie A matches Samardžić (99), Dybala (97), Chukwueze (94) — "closer than X% of the pool"; Bruno's chance creation 3.6 SD above role average; Serie A's highest 1.9 (Baturina, one season of evidence), Dybala 1.8.
- Similarity vs prediction (Study 5): comparables alone are worse than the player's own history (+0.019 MAE, no better than "he'll do what he did"); adding similarity to the history model changes the error by nothing detectable.
- Transfer model: MAE 0.096 vs 0.129 naive, R² 0.76, AUC 0.80 (keeps ≥ 75%), on 142 moves in seasons locked away until the model was fixed. Movers keep 97% of output vs comparable stayers; into the Premier League 82%.
- Man Utd 2024 (no hindsight): Zirkzee predicted 0.46 xG + xA / 90, actual 0.47 (48th of 106 strikers on the board); Ugarte 0.02 vs 0.14 (outside the range — known midfield bias + defensive value the data can't see); strikers 4/4 and midfielders 5/6 inside their 80% range.
- Study 1 (weather) is **provisional** until its written conclusion and freeze — don't headline it at launch.
