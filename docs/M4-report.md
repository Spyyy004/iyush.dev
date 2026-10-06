# M4 — Implementation report
## `iyush.dev/football/tools/transfer` · Transfer Calculator

**Spec:** [M4.md](./M4.md) · **Status:** built and verified locally → ready for PM review · **Stopped.** Nothing from M5 was started.

Local URL: http://localhost:4601/football/tools/transfer?player=bruno-fernandes&from=premier-league&to=serie-a&club=inter

---

## 1. Components created

| M4 component | Implementation (`football/js/transfer.js`, `football/football.css`, page from `scripts/build_transfer_page.py`) |
|---|---|
| TransferCalculator | page + script; the qualifier ("predicts post-transfer attacking output… does not predict overall player quality or career success") is shown **before** any run |
| TransferPlayerInput | M3 PlayerSearch (`FB.combo`), 834 forwards and midfielders; after a pick it shows "club · available history: N seasons · minutes · last season's xG + xA per 90 · role" |
| OriginLeague | inferred from the player and shown read-only (§6) |
| DestinationLeague | derived from the model's supported leagues, minus the origin league (moves are cross-league) |
| DestinationClub | that league's clubs plus "A newly promoted club" (the research's own option). **Required**: see question 1 |
| TransferPrediction | "Transfer projection" header (player, origin → destination · club, role, age, seasons of history) and the two key numbers: **expected output** and **expected retention** |
| RetentionVisualization | pre-transfer bar vs post-transfer expected bar, with the 80% range shaded on the same scale (no gauges) |
| ProbabilityThreshold | "Probability of retaining at least 75% of pre-transfer attacking output", stated as not a chance of "success"; hidden with the research's reason when last season's output is < 0.10 |
| PredictionRange | low ── ▲ point ── high, labelled **80% prediction range**, explicitly "not a confidence interval"; typical width ±0.2 |
| PredictionDrivers | "Why does the model expect this outcome?": **the model's own additive terms**, grouped into player history, league move, age, club context and playing time, as diverging bars that sum to the prediction |
| ModelProgression | MAE / R² table: naive → role average → context → final model (locked test) |
| ValidationCard | 142 unseen transfers · 2023/24–2025/26 · locked before testing · beat naive by 0.033 (CI 0.018–0.049) · AUC 0.80 / Brier 0.179 vs 0.224 · 80% ranges covered 87% |
| TransferLimitations | "Where the model can fail" (fixed league effect, **Ugarte predicted 0.02 (0.01–0.05) vs actual 0.14**), "What this doesn't tell you" (10 items, §21), scope and data sources |
| LeagueRetentionTable | into / out of each league vs comparable stayers, with 95% CIs and number of moves, plus the regression-to-the-mean explanation and 97% (93–101%) |
| TransferShare | **Copy link** + share card |
| Connections | "See the model tested against Manchester United's 2024 recruitment →" under the calculator; "Looking for similar players instead?" → Similarity Explorer. The Similarity Explorer now links back with the same player |

States: loading players, no player, no league, no club, a four-step "Analysing player history" progress tied to the real data fetch, out of scope / not covered, no prediction, and error with **Try again**.

## 2. Routes

- **`/football/tools/transfer`** (new). **`/football/tools/transfer-calculator` → permanent redirect** (query string kept). Every internal link, the sitemap, `llms.txt` and the README now point to the new route.
- **`/api/transfer-page`** (Edge, via a `vercel.json` rewrite when `?player=` is present) adds result-specific title and social tags.
- **`/api/og/transfer`** (Edge) draws the share card.
- **Removed:** the old calculator page, the in-browser engine `js/s5_engine.js`, and its 207 KB `data/transfer.json`. The homepage example now reads the precomputed result; it shows the same numbers as before.

## 3. Study 5 data contract used

The contract is adapted to the real outputs:

- **`transfer/index.json`:** model facts (Model A refitted on 428 moves; inputs 2025/26; move 2026/27; 900-minute scope; in-scope roles; 0.10 floor for the ≥75% probability) and the five leagues.
  - Players: `[key, name, 2025/26 club, league, role, slug, seasons of history, minutes, last-season xG + xA per 90]`.
  - Clubs: `[league, club, market strength, promoted flag, the club's model terms]`.
- **`transfer/p/<key>.json`:** one per player. Last season's and three-season output, xG, xA, age, the player's model terms, and `pred[club] = [expected output, q10, q90, P(≥75%)]` for every club in the other four leagues.
- **Not built:** a single "transfer score" (§28).

## 4. Precomputed outputs consumed

**All predictions come from the research's production model.** `scripts/build_transfer.py` calls:
- `site_export.production()` for Model A and its out-of-sample error model;
- `site_export.players()` and `site_export.clubs()` for eligibility and club strengths;
- the fitted `statsmodels` object for the predictions;
- `transferability_model.predictive()` for the 80% range and P(≥75%).

**Coverage:** 834 players × 101 clubs = 67,296 predictions, built in 4 s.

**Checks built into the precompute:**
- The driver terms (from `site_export.engine_params`) must add up to the model's prediction. Maximum error is 2.2×10⁻¹⁶.
- All **60 research engine test cases** (`m9_engine_fixture.json`) match, with a maximum difference of 2.2×10⁻¹⁶.

**The browser does no modelling.** It looks up four numbers and divides expected output by last season's output to show retention.

## 5. Share / OG

- **URL format:** `?player=<slug>&from=<league>&to=<league>&club=<club-slug>`.
  - Slugs are shared with the Similarity Explorer, so the two tools link to each other.
  - Search and run add browser-history entries, and Back works.
  - A link without a club pre-fills the form instead of running.
- **Share card:** "Will his game travel? · player · origin → destination · club · Expected retention XX% · range · attacking output only · not a verdict".
- **Page tags:** the title and description carry the retention and the range.
- **Tested in Node only, same as M3.** It still needs a deploy check.

## 6. Mobile

- **Three-step wizard (§23):** player → "Where is he moving?" (From, read-only, and To) → destination club → **Run prediction**.
- **Result:** a vertical brief (key numbers stacked, bars with labels above, the two cards stacked, driver labels above their bars).
- **Tested:** 0 px overflow at 390 px.

## 7. Accessibility

- **Form:** labelled controls; errors are announced and focus moves to the field that needs attention.
- **Results:** an `aria-live` region; focus moves to the result heading.
- **Charts:** the retention bars and the prediction range have full text labels, plus an "In words" summary. The driver values are printed as numbers.
- **Colour is never the only signal:** contributions are signed (+/−), and up/down also differ in colour.
- **Tables:** real `<table>`s with captions.
- **Tested:** clean automated pass on all 15 routes at 1440 / 390.

## 8. Performance

- **First visit:** the player index (`index.json`, about 23 KB compressed) and about 1 KB per player.
- **Query time:** a result renders **2–4 ms** after clicking, measured in the page.
- **Size on disk:** 2.6 MB in total (835 files). No dataset or model reaches the browser.

## 9. Dependencies

**None new.** It reuses M3's `@vercel/og` and fonts and adds two Edge functions (`api/transfer-page.js`, `api/og/transfer.js`) plus a shared lookup (`api/_transfer.js`).

## 10. Questions / blockers for PM

1. **The "Any club" / league-level estimate doesn't exist in Study 5.** The model always uses a destination club's strength (and a promoted-club flag). The research offers each league's clubs plus "A newly promoted club", but no league-average option. Following the brief (don't fabricate a missing contract), **the club is required**, and the page explains why. If you want a league-level estimate, the research would need to define one (for example, a league-average club in `site_export.clubs()`).
2. **Drivers are numbers, not labels.** §15's example labels (Strong / Moderate / Positive) aren't in the research, so the page shows the model's actual contributions in xG + xA per 90, which add up to the prediction. "Recent performance jump" isn't a separate model term; it's how last season (weight 0.12 / 0.16 / −0.19 by role group) counts for much less than the three-season level (0.59 / 0.53 / 0.87). The page says this in those terms.
3. **"Baseline for his role group" appears as a driver**, even though Study 5 says role adds nothing. It's the model's per-role-group intercept and must be included for the terms to add up; the page notes that role as a predictor added nothing. Is this wording clear enough?
4. **Premier League "moving out": 117% (107–127%) vs 116% (106–126%).** The results table and the data say 117%; `findings/study5_transferability.md` and the Final Summary say 116%. The site now uses 117% everywhere, including the Study 5 page text and `llms.txt`. The findings file should be corrected (it's the same kind of slip as Ligue 1's 89% vs 90%).
5. **Timing.** Inputs are as of 2025/26, for a move in summer 2026. Players who moved this summer are listed with their 2025/26 club, as the model's "origin".
6. **Share cards still need a preview deploy** to check the Vercel rewrites and Edge functions (same as M3).
7. **Rebuild steps.** Not yet in the weekly pipeline:
   ```
   ~/dev/weather_football/.venv/bin/python scripts/build_transfer.py
   python3 scripts/build_transfer_page.py
   python3 scripts/build_home.py
   ```
