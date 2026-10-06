# M2 — Implementation report
## `iyush.dev/football/research` · Research experience

**Spec:** [M2.md](./M2.md) · **Status:** built and verified locally → ready for PM review · **Stopped.** Nothing from M3 was started.

Run locally: `npx serve -l 4601 .` → http://localhost:4601/football/research  
Rebuild after content or data changes: `python3 scripts/build_research.py`

---

## 1. Routes created

| Route | Status shown |
|---|---|
| `/football/research` | Research index: hero, spine, synthesis, five lessons, corrections, open items |
| `/football/research/environment` | **Weather freeze pending.** Crowds final; weather final for four leagues; Ligue 1 confirmation and freeze pending; temperature an open lead |
| `/football/research/home-advantage` | Complete |
| `/football/research/opposition` | Complete |
| `/football/research/similarity` | Complete |
| `/football/research/transferability` | Complete |

The URLs are unchanged from M0, so the sitemap, canonical URLs and share cards still apply.

## 2. Components created

**One StudyPage system renders all five studies.** No page is hand-written. Each M2 §32 component is a Python render function in `scripts/build_research.py` paired with a CSS class in `football/football.css`.

| M2 component | Implementation |
|---|---|
| ResearchIndex · ResearchHero · StudyTimeline | `index_page()` · `.hero` + `.strip--4` · `.timeline` (the spine) |
| StudyPage · StudyHeader · StudyQuestion | `study_page()` · `hero()` (number, status, question, sub-question, scope) · `.q-big` |
| StudyFinding · FindingCallout | `finding()` for headline, evidence, counter, climax, progression, locked and failure findings · `.callout` |
| StudyMethod · MethodAccordion | `method()`: flow diagram (horizontal, or vertical for Study 5), Study 4's nine dimensions, Study 5's benchmark box, plain-language explanation, and **Technical detail** in a collapsed `<details>` |
| StudyEvidence · StudyComparison | `.find--ev`: the key result as a sentence first, then the figure (§29) |
| StudyLimitation · SourceNote | `limits()` with a provenance line (sources, analysis period, frozen dataset) · a `.source` line on every figure |
| StudyTransition · StudyNavigation | `transition()` "The next question" (§27) · sticky `.snav` (five studies, current one highlighted, pending badge, swipeable on phone) + `pager()` previous/next (§24) + breadcrumb `Home / Research / 0N Study` (§25) |
| ResearchStatus | status pill in the header + `.status-box` listing each part's status (Study 1) + status-labelled finding groups ("Crowds · Final", "Weather · …pending") |
| "We were wrong" (§11) | `surprise()`: raw data suggested → what happened after we checked → lesson. Present on every study |
| Study 4 turn (§12) | `.turn` banner: "Studies 1–3 asked… / Study 4 asks…" |
| MetricTooltip | inline `{term\|label}` markup → M1 `.term` popover. **The build fails on any unknown term** |

## 3. Research data / content structure

- **`content/research.json`** holds the study content. It follows the §33 `Study` contract (id, slug, title, question, status, period, leagues, sample, summary, why, method, findings[], limitations[], next), extended with `status_parts`, `surprise`, `meaning`, `turn`, `clarify` and per-page `meta`.
- **Findings** follow the §33 `Finding` contract (title, lead = the key result as a sentence, explain, chart), plus a `kind` that selects the component.
- **Charts are referenced, never typed in.** A chart is either:
  - a builder id such as `"s3-effects"`, computed from `football/data/research.json` at build time; or
  - for Study 1 only, which has no data export yet, an inline spec holding Final Summary values, always with a source line.
- **Prose** comes from the Final Summary (`docs/Football Research Series — Final Summary.pdf`).
- **The build refuses to render a study** that is missing a framework section, or that references an unknown glossary term or chart.
- `content/` is excluded from deployment (`.vercelignore`).

## 4. Charts implemented

20 figures, all static HTML (no chart library). Each has a "What you're looking at" title, a plain-language subtitle, an "In words" summary and a source line.

| Study | Figures |
|---|---|
| 01 | Pooled xG home edge by period (+30 → +13 → +26) · home ÷ away with fans vs closed doors · weather ±2.5% band next to the crowd effect · **0 of 6** pre-registered hypotheses |
| 02 | Home edge by metric with 95% CIs · xG edge by period · by league · **0 of 4,665** + per-player histogram (raw vs shrunk) · the six "strongest home clubs" raw vs shrunk |
| 03 | Effect per +1 SD by metric with CIs (centrepiece) · **"How big is that?"** by fifth of opponents (−33%) · by position · by league · **0 of 23,022** · overall level vs elite record · Bruno's xA raw vs adjusted by season |
| 04 | Self-retrieval (top 9%) · **Bruno 3.6 SD vs Serie A's best creators** + closest profiles + "None was a true like-for-like" callout |
| 05 | 97% (93–101) vs stayers · into vs out of each league (+ table) · age and destination-club strength · **ModelProgression** (MAE and R² per step) · locked-test timeline · similarity experiment · calibration of P(≥75%) · Ugarte predicted 0.02 vs actual 0.14 |

**Motion (§30):** each chart draws once on scroll; markers fade in after the bars; non-zero counters count up once. There is no continuous animation. Motion is off for `prefers-reduced-motion`, and content stays visible if JavaScript fails.

## 5. Accessibility

- **Structure:** one `h1` (the question) per page; each framework section has an `h2` (its numbered label); findings are `h3`. Landmarks, skip link, and an `aria-current` breadcrumb and study nav.
- **Figures:** `role="img"` with a full text label, a text result above every chart, an "In words" summary below, and the Study 5 numbers also in a real `<table>`.
- **Colour is never the only signal.** Values are printed, the two series in a pair differ by shape (filled dot vs ring), and status pills carry words.
- **Tested:** 0 undersized touch targets and 0 horizontal overflow on all 15 routes at 1440 and 390. Glossary popovers work with keyboard and touch. Methodology uses native `<details>`.

## 6. Performance

- **No research data reaches the browser.** The research pages make zero requests to `/football/data/` (checked in the automated pass). The old study pages fetched `research.json` (68 KB) and drew charts in the browser.
- **Page weight:** 16–32 KB of HTML per page, plus the shared CSS, JS and glossary already cached from the homepage.
- **No loading, error or empty states needed:** nothing on these pages fetches data, so there is nothing to fail.

## 7. Dependencies added

**None.** The build uses the Python standard library plus `node`, already used in M1, to read the glossary keys.

## 7b. Cross-check against the research project (after build)

Every number was checked against `~/dev/weather_football` (findings/*.md, outputs/, site/data.json), which is newer than the Final Summary PDF. The project's Google Sheets and Docs are a one-way mirror of the same files (last synced 5 Oct).
- **Study 1 updated to the 6 Oct findings.** The five-league weather models are done: rain and humidity within about ±2%, wind about −1% per +10 km/h, temperature +3.2% key passes and +4.2% goals per +10 °C (still an open lead). Still pending: the 1,000-permutation temperature placebo, the hand-written conclusion and the freeze. Also corrected the description of the weather model's fixed effects.
- **Wording fixed:**
  - Study 2: "exactly average" → +43% vs the +33% all-player average.
  - Lesson 2: 0.018 is the correlation between 2015–19 and 2022–25, not season-to-season. The 5–8% signal figure applies to Study 2 only.
  - Study 3 "not one case": one uncorrected shots case exists; none survives the correction.
  - La Liga / Ligue 1: −7% → −7% to −8%.
  - Histogram captions now explain the n (4,606 in the export vs 4,665 in the reliability test).
- **Ligue 1 "moving out" is 89%.** The source table says 89% (82–95%); the summary's 90% came from prose that grouped it with the Bundesliga.
- About 115 other numbers match exactly.

## 8. Questions / blockers for PM

1. ~~Ligue 1 89% vs 90%~~ — resolved: the source table says 89% (see 7b).
2. **§21 "Expected retention 80%" was not built.** No general 80% retention figure exists in the research; the closest is "Serie A → Premier League keeps ~80%". I kept the AUC 0.80, Brier and ±0.2 range values, and replaced the bar with a calibration chart.
3. **§6 example numbers.** The "0.70 vs 0.55 xG + xA" example is illustrative, not a research value, so the page says it in words instead to avoid looking like data. Restore the numbers?
4. **Study 1 temperature.** The open lead's numbers (+3.3% key passes per +10 °C, Serie A xA +10.7%) are shown in a box labelled "Open · Not yet a finding", quoting the Final Summary. Keep them, or hide the numbers until the freeze?
5. **Study 1 has no data export.** Its crowd and weather figures use values from `findings/study1_environmental_conditions.md` (6 Oct) stored in the content file. When the five-league freeze lands, Study 1 needs an export like Studies 2–5.
6. **The Fan/Analyst toggle (M0 §19) is gone from the study pages.** M2's progressive disclosure replaces it: plain language by default, **Technical detail** collapsed. Confirm this supersedes the toggle (the methodology page keeps it).
7. **Mobile order (§29) vs framework order (§4).** The §4 order is used at every size. The finding still comes first on phone (it's in the header, above the method), and the technical method is collapsed.
8. **Content dropped from the old study pages:** robustness by rating definition, per-season effects, between-player spreads (τ), and the extra Study 2 metrics (assists, xGChain, xGBuildup). Bring any back in a "Show the numbers" section?
9. **Smaller items.**
   - Study 5's next question links to the existing Live tracker, which is outside M2 scope.
   - The share cards were made for the old headlines and may not match the new hero questions.
   - The homepage timeline wording (M1) differs slightly from the research spine wording (M2). Align them?
