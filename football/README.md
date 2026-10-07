# Home Turf & Hard Opponents

**Football research by [Ayush Pawar](https://iyush.dev/football/about)** · live at **[iyush.dev/football](https://iyush.dev/football)**

> What actually belongs to the player — and what belongs to the context?

Five studies on every player-match in Europe's top five leagues from 2015/16 to 2024/25, built into a set of interactive tools and a live tracker that re-tests the findings every week.

---

## The research arc

| Study | Question | Page |
|---|---|---|
| 01 · Environment | Do weather and crowds change individual output? | [/research/environment](https://iyush.dev/football/research/environment) |
| 02 · Home advantage | Which players benefit most from playing at home? | [/research/home-advantage](https://iyush.dev/football/research/home-advantage) |
| 03 · Opposition | How much does opponent quality distort player statistics? | [/research/opposition](https://iyush.dev/football/research/opposition) |
| 04 · Similarity | Can context-adjusted profiles find similar players across leagues? | [/research/similarity](https://iyush.dev/football/research/similarity) |
| 05 · Transferability | How much of a player's output survives a league move? | [/research/transferability](https://iyush.dev/football/research/transferability) |

## Key findings

- **Weather barely matters; crowds do.** Rain and humidity move per-90 output by less than ±2% and wind by about −1% per +10 km/h. Temperature is a small association, mostly in Serie A, that survived a 1,000-permutation placebo check; the written conclusion is still pending, so it is provisional. Without fans, the xG home edge roughly halved (+29% → +13% at team level).
- **Everyone gets better at home — nobody is a home specialist.** The same player produces about +27% xG per minute at home, but 0 of 4,665 players show a reliable personal home edge, and past home edge doesn't predict future home edge (r = 0.018).
- **There aren't reliable "big-game players".** Output falls 13.8% per +1 SD of opponent strength; 0 of 23,022 player × metric estimates show individual resistance. A player's overall adjusted level predicts his output against elite opponents better than his past elite record (xG r 0.84 vs 0.75).
- **Similarity is descriptive, not predictive.** Three-season profiles find the same player in the top 9% of a destination league's role pool after a move. Bruno Fernandes's chance creation is 3.6 SD above his role average; Serie A's closest is 1.9 SD.
- **History beats similarity for transfers.** Movers keep 97% of their output against comparable stayers (CI 93–101%); moving into the Premier League keeps 82%. A model of the player's own history, age, clubs and leagues scored **MAE 0.096 vs 0.129** for "he'll do what he did" on 142 locked, unseen moves (R² 0.76; AUC 0.80 for keeping ≥ 75%). Adding Study 4's similarity changed the error by nothing detectable.
- **Case study:** standing at 1 June 2024, the model predicted Joshua Zirkzee at 0.46 xG + xA per 90 at Manchester United (actual 0.47) and missed Manuel Ugarte (0.02 vs 0.14) — on the model's documented weak spot. [Read it →](https://iyush.dev/football/case-studies/manchester-united-2024)

All observational: effects are associations within matched comparisons.

## The interactive site

- **[Similarity Explorer](https://iyush.dev/football/tools/similarity)** — who plays like him, in any of the five leagues (shareable: [Bruno → Serie A](https://iyush.dev/football/tools/similarity?player=bruno-fernandes&league=serie-a&seasons=3))
- **[Transfer Calculator](https://iyush.dev/football/tools/transfer)** — expected xG + xA per 90 after a move, with an 80% range
- **[Live tracker](https://iyush.dev/football/live)** — Studies 2 and 3 re-tested every week on 2025/26 and 2026/27, beside an immutable frozen baseline
- **[Methodology](https://iyush.dev/football/methodology)** and **[Glossary](https://iyush.dev/football/glossary)** — how we know, and what the terms mean

## Methodology in one paragraph

Compare each player with himself: Poisson pseudo-likelihood (PPML) models on per-minute output with player × team × season fixed effects, so ability and team quality are held fixed. Opponent strength comes from a sequential rating built on pre-match betting odds (0 of 155,282 leakage checks changed a rating). Individual effects are separated from noise with calibrated errors, DerSimonian–Laird spread and empirical-Bayes shrinkage, and every headline effect survives Benjamini–Hochberg correction, permutation and placebo tests. The transfer model was fixed before its test seasons were opened and scored once. Full detail: **[iyush.dev/football/methodology](https://iyush.dev/football/methodology)**.

## Data

Premier League, La Liga, Serie A, Bundesliga, Ligue 1 · 2015/16–2024/25 (frozen) · 18,011 matches (18,008 with usable player data) · 160 teams · 8,348 players · 525,328 player-matches · ~452,000 shots. Live seasons are added weekly and never change the frozen results.

Sources: Understat (player and shot data) · football-data.co.uk (pre-match odds) · fixturedownload.com and openfootball (kickoffs) · Wikipedia/Wikidata and OpenStreetMap (stadiums) · Open-Meteo ERA5 (weather) · dated crowd-restriction calendars · the CC0 Transfermarkt-derived dataset (dates of birth).

## Architecture

```text
RAW SOURCES          Understat · odds · kickoffs · stadiums · ERA5 weather · crowd calendars
     ↓
INGESTION            fetchers per source, cached; weekly for live seasons
     ↓
NORMALISATION        kickoff reconciliation, stadium geocoding, crowd status, team / player ids
     ↓
RESEARCH DATASET     frozen 2015/16–2024/25 + separate live seasons
     ↓
STUDY PIPELINES      one package per study (PPML, shrinkage, ratings, similarity engine, transfer model)
     ↓
VALIDATION           data checks, leakage tests, placebos, locked test seasons
     ↓
FRONTEND SNAPSHOTS   exported JSON + precomputed tool results, checked at build time
     ↓
INTERACTIVE PRODUCT  this static site (no framework) on Vercel
```

The research pipeline (Python) lives in a separate, not-yet-public project; every Monday it fetches new matches, re-runs the live tracker and rebuilds this site's data. **This repository is the presentation layer.** It never re-runs the research in the browser: it reads validated exports, and the build stops if a displayed number drifts from the research.

| In this repo | What it does |
|---|---|
| `football/` | the site: static HTML, `football.css`, `js/` (tools, glossary popovers), `data/` (exports, precomputed tool results) |
| `scripts/football_export.py` | copies the research exports into `football/data/` |
| `scripts/build_*.py` | generate the pages from `content/*.json` + data, with guards against the research findings (e.g. 56 checks on the methodology page; the frozen live baseline is verified against a sha256 manifest) |
| `api/` | Vercel functions for result-specific social cards on shared tool links |

## Reproducibility

The site is reproducible from this repository: `python3 scripts/build_*.py` rebuilds every page from the committed data. The underlying research code and the raw data are not published yet (the raw sources have their own terms); the methodology page documents every model, test and correction.

## Limitations

The data is attacking output only: no defending, passing volume, carries, possession, injuries, fees, contracts or tactical fit, and no cup matches. Goalkeepers are excluded throughout, defenders from the transfer model. The closed-doors period is mostly one season. Similarity describes resemblance; it is not a forecast. The transfer model under-predicts low-output central midfielders moving into the Premier League.

---

Built by **Ayush Pawar** — product engineer by trade, football obsessive by choice · [iyush.dev](https://iyush.dev) · [LinkedIn](https://www.linkedin.com/in/ayush-pawar004) · [i.yush.004@gmail.com](mailto:i.yush.004@gmail.com)
