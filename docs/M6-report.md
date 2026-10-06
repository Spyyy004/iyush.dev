# M6 — Implementation report
## `iyush.dev/football/live` · Live Research Tracker

**Spec:** [M6.md](./M6.md) · **Status:** built and verified locally → ready for PM review · **Stopped.** Nothing from M7 was started.

Local URL: http://localhost:4601/football/live

---

## 0. Three things the PM should know first

1. **Study 1 is not frozen in the research repo.**
   - `findings/study1_environmental_conditions.md` → "Open" still has these unticked:
     - the 1,000-permutation temperature placebo (M12; at 990/1000 when this was built);
     - the hand-written weather conclusion;
     - the freeze itself (git tag, checksum manifest, pinned packages).
   - The research folder isn't a git repo yet, so the git tag can't exist.
   - **So the status board shows Study 1 as "◐ Not yet frozen", with the open items listed.**
   - It reads that checklist and flips to "● Frozen" by itself once `[x] Freeze` appears. The Temperature open question disappears at the same moment.
   - Studies 2–5 show "● Frozen" (their findings say complete on the 2015/16–2024/25 data).
2. **"Historical r = .011" is actually the 2025/26 live result.** The frozen equivalent is Study 2's out-of-sample check:
   - **r = 0.018**, 595 players, 2015/16–18/19 vs 2022/23–24/25.
   - The page shows: Historical 0.018 · 2025/26 0.011 · 2026/27 not yet recalculated.
   - Claim 04's .84 vs .75 is correctly historical. 2025/26 is .76 vs .68.
3. **2026/27 is +22.0% / −13.3% on the page, not +21.0% / −12.9%.**
   - The brief's numbers come from `findings/live_tracker.md`, which was written about 35 minutes before the tracker snapshot was regenerated with one La Liga match excluded.
   - The page shows the snapshot and flags a partial update. This is the same unresolved item as M5 Q1.
   - Next Monday's run should bring the two back in line.

## 1. Routes

- `/football/live`: rebuilt by `scripts/build_live.py`.
- `?season=2025-26` / `?season=baseline`: selector state, restored on reload.
- No new API routes.
- The homepage live table reads the same snapshot and now handles the "unavailable" state.

## 2. Data contract — `football/data/live.json` (schema 2, 11 KB)

```
schema, state (ok | partial | fallback | unavailable), notices[], generatedAt (pipeline), builtAt, staleAfterDays
baseline     period, sha256, createdAt, home{}, opposition{}, opposition_seasons_xg[], home_periods_xg[],
             home_persistence{r, players, method}, elite{players, method, r{metric:{overall, past}}}
seasons[]    id, label, slug, status (complete | current | early), through, matches, player_matches, fixtures, played, progress, leagues[]
metrics      home[] / opposition[]: frozen + seasons[] {value, lo, hi, n_obs, change{word, why, early}} or {value:null, note}
checks[]     per live season: home {players, r} | null · elite {players, r{…}} | null
partial[], weeklyStatus, researchStatus[], questions[], log[], odds, sources
```

The build is two-stage:
1. `build_snapshot()` reads and validates the pipeline outputs, then writes the snapshot.
2. `render()` builds the page from the snapshot alone.

## 3. Pipeline outputs consumed

| Output | Used for |
|---|---|
| `tracker` in `site/data.json` (via `football/data/research.json`) | live estimates and intervals, season status, processed matches, exclusions, player-level checks, odds validation, timestamp |
| `s3_seasons`, `s2_periods`, `s3_elite` (frozen) | per-claim history, elite-opponent baseline |
| `findings/study2…md`, `findings/study3…md` | Claim 03 frozen r (0.018, 595 players); Claim 04 sample size (2,047). Parsed; the build fails if the wording disappears |
| `logs/live_fetch_summary.json` | season progress (fixtures vs played per league) |
| `logs/weekly/*.log`, `last_status.txt` | update log, partial / failed-run state |
| `findings/*.md` | status board (including Study 1's checklist), open questions, dated events |

## 4. Frozen / live separation

- **Immutable baseline is enforced.** `football/data/frozen_baseline.json` holds every frozen number the page shows, plus a sha256.
  - Every build recomputes those numbers from the frozen outputs and **fails** if any value moved, or if the manifest was hand-edited.
  - Tested both cases: a hand-edit is rejected, and drift (−13.8 vs −13.7) is rejected.
  - A real correction needs an explicit `--init-frozen` and a Corrections entry in the findings.
  - The page shows the checksum under "The historical baseline is immutable."
- **Frozen values come only from the manifest.** The tracker's copy is checked against it, never shown.
- **Visual separation:**
  - frozen = ◇ marker and blue-grey "Frozen" pill;
  - live = dot with 95% interval;
  - the early season gets a hollow dot, a dashed interval, a slightly dimmed hero and an "Early season" pill;
  - nothing uses red just because it's current.
- **Change labels follow fixed rules and use the brief's vocabulary.** Each label compares the frozen value with the season's 95% interval:

  | Label | Rule |
  |---|---|
  | Broadly stable | frozen value inside the interval |
  | Higher / Lower than baseline (home) | frozen value outside the interval |
  | Stronger / Weaker than baseline (opposition) | frozen value outside the interval |
  | Insufficient evidence | interval includes zero |
  | "Early ·" prefix | season in progress |

  - The rules are printed on the page.
  - For opposition, the label also says whether the value is inside the range of single frozen seasons.
- **Claims 03/04:**
  - A live value appears only where the pipeline computed it.
  - Otherwise the row shows the brief's wording: "Not yet recalculated for the live dataset." / "Historical result · live validation pending".
  - Each row states its method, because the live tests aren't identical to the frozen ones.

## 5. Status and error handling

| State | Trigger | What shows |
|---|---|---|
| Complete / Current / Early | pipeline `in_progress` + share of fixtures played (< ⅓ = early) | pill on every season row, hero and selector |
| Stale | snapshot older than 8 days (browser compares the timestamp only) | banner "Data may be stale · Last successful update …"; red timestamp; extra "Data may be stale" pill on in-progress seasons |
| Partial | exclusions, weekly-run mismatch, or a failed last run | "Partial update" banner with the pipeline's reasons (showing now) |
| Missing | no estimate for a metric or season | "Not yet available for this season." — never a bare "—" |
| Fallback | this week's output missing or failing validation, but a valid earlier snapshot exists | "Showing the last validated update" plus the reason (tested by hiding `live_fetch_summary.json`) |
| Unavailable | no valid snapshot at all | "**Live data temporarily unavailable.** The historical baseline remains available." Claims show frozen values only. The status board, questions, log and provenance still render (tested with `--simulate-failure`) |

Validation before use:
- every season has processed matches;
- xG home and opposition estimates are finite, with lo ≤ value ≤ hi;
- there is a valid timestamp.

Failure reasons never reveal local file paths.

## 6. Components (`scripts/build_live.py` + `football.css` `.lv-*`)

| Component | Implementation |
|---|---|
| LiveHero | question, lede, last-updated panel |
| Frozen / live split | two-panel FROZEN / LIVE band directly under the hero |
| SeasonSelector | live seasons (newest first) + "Historical baseline"; shows and hides blocks rendered at build time; hidden without JS (the full comparison is still visible) |
| SeasonProgress | progress bar, matches processed, matches through, last updated, per-league breakdown |
| LiveStatus / StaleDataWarning | as in §5 |
| LiveMetric | Claims 01/02 hero, which follows the selector |
| BaselineComparison | Claims 01/02 chart and "all five metrics" table |
| HistoricalSeries | "Show all historical seasons" per claim. Opposition: all 10 frozen seasons, then pooled, then live. Home: crowd periods, because no per-season series exists (stated on the page) |
| Claims 03/04 | historical vs per-season rows |
| ChangeSummary | "What's changed?", which follows the selector |
| Immutability block | "The historical baseline is immutable" + checksum |
| ResearchStatusBoard | as in §0 |
| OpenQuestions | similarity validation; transfer league effect; Temperature only while Study 1's checklist is open |
| UpdateLog | snapshot, weekly runs, 2025/26 season complete, Study 1 models, correction |
| DataProvenance | update cadence, sources, "How the research works →" |

## 7. Accessibility

- **Structure:** one `h1`, an `h2` per section, a labelled `<select>` (44 px tall), native `<details>`.
- **Alerts:** `role=status` inside an `aria-live` region.
- **Charts:** a full text label on each, with the values printed beside it.
- **Tables:** captions.
- **Status is never shown by colour alone:** pills carry words; frozen and live differ in shape; "→" has screen-reader text "to".
- **Tested:** Playwright at 1440 / 390 px: 0 console errors, 0 failed requests, 0 horizontal overflow, in both the normal and unavailable states. Homepage live table also passes.

## 8. Performance

- Page: 40 KB static HTML.
- **Zero data requests and zero external requests** from the live page; the selector only toggles `hidden`.
- Homepage still fetches the 11 KB snapshot lazily.

## 9. Dependencies

**None added to the site.** Playwright ran from the scratchpad for testing only.

## 10. Blockers / questions for PM

1. **Study 1 freeze.** Confirm the status board should keep following the research checklist; it shows "Not yet frozen" until `[x] Freeze` lands.
   - If the freeze is meant to include a git tag, `~/dev/weather_football` first needs `git init`.
2. **Claim 03 baseline.** Approve 0.018 (frozen out-of-sample) as the historical value instead of .011, which is 2025/26.
3. **The 2026/27 mismatch** (§0.3). It should clear after Monday's run; no action on the site.
4. **The labels disagree with the brief in two places:**

   | Season, metric | Brief | Rule says | Why |
   |---|---|---|---|
   | 2026/27 home xG | "lower than baseline" | Early · broadly stable | the frozen +26.6% sits inside its 11–34% interval |
   | 2025/26 opposition | "broadly within the historical range" | Weaker than baseline | −11.4% is just outside both the pooled interval and the single-season range (−16.1% to −11.8%) |

   Keep the rules?
5. **Opposition wording.** I used "stronger / weaker than baseline" instead of "higher / lower", because "higher" is ambiguous for a negative effect. OK?
6. **Home history.** Still no frozen season-by-season home series; Study 2 would need to export one (same as M5 Q3).
7. **Numbering.** The PM's M5 was "Study 1 finalization"; this repo's M5 was the first live tracker. The docs keep the repo's numbering; M7 = Manchester United case study either way.
8. **Publishing is still manual.** The weekly rebuild runs automatically (`weekly_update.sh` step 6); commit and deploy don't. Everything since M0 is still uncommitted.
