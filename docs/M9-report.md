# M9 — Implementation report
## Distribution, SEO & launch readiness

**Spec:** [M9.md](./M9.md) · **Status:** built and verified locally → ready for PM review · **Stopped.** M10 not started. Not yet committed or deployed. The one exception is the domain change in §1, which is a Vercel setting and is already live.

How the audits ran: three read-only audits ran in parallel — research integrity, copy / plain language, and accessibility / performance / links. I applied the fixes myself and re-ran the checks. Where the UI showed a research value wrongly, I fixed the **display**. Where the research sources disagree with each other, I changed nothing and list them in §9.

---

## 1. SEO implementation

- **Primary domain flipped to `iyush.dev`** (your choice).
  - Before: Vercel redirected `iyush.dev` → `www`, while every canonical, sitemap entry and OG URL said `iyush.dev`.
  - Now: `www.iyush.dev/*` → 308 → `iyush.dev/*`, query strings kept.
  - All existing canonicals are correct with no code changes. Verified live.
- **Titles** follow the brief:
  - "Home Turf & Hard Opponents — Football Research by Ayush Pawar"
  - "Who Plays Like Him? — Football Player Similarity"
  - "Will His Game Travel? — Football Transfer Prediction"
  - "What would the model have told Manchester United in 2024?"
  - Every route already had a unique title, description and canonical. Shared tool links get player-specific titles from the share functions.
- **Structured data:**
  - New: BreadcrumbList on every page (it mirrors the visible breadcrumb; `case-studies` is skipped because it has no index page).
  - Existing: WebSite, Person (`/#person`), ScholarlyArticle (studies), Article (case study), TechArticle (methodology), DefinedTermSet (glossary), Dataset (live), AboutPage (now with `mainEntity` = Person).
- **Indexing checks:**
  - `robots.txt` allows everything; the sitemap lists all 15 football routes; there is no `noindex` anywhere.
  - Clean URLs; one `h1` per page.
  - Lighthouse SEO scores 100 on every audited route.
- **Favicon:** added (`/favicon.ico`, `.svg`, `apple-touch-icon.png`) to every page, parent site included. Its absence was the only Best-Practices deduction and the only console error.

## 2. Social / OG implementation

| Card | Status |
|---|---|
| Research | re-rendered to the brief: "What actually belongs to the player? — Five studies investigating context in football performance." |
| Similarity | dynamic per player/league (`api/og/similarity`), verified live with Bruno → Serie A |
| Transfer | dynamic, shows expected retention % (`api/og/transfer`), verified live |
| Case study | Zirkzee 0.46 → 0.47 · Ugarte 0.02 → 0.14 (M7) |

- The Environment card now says temperature is a *provisional* exception.
- The Transferability card now says "nothing detectable" instead of "+0.000".
- Fixed a quoting bug in `scripts/og/render.sh` (from M7) that stopped the full re-render.

**ShareButton** (`FB.share`, reused everywhere — case study, similarity results, transfer results):
- Copy link · X · LinkedIn · native "Share…" where the device supports it.
- The URL carries the result state, so shared links reopen the same result.

## 3. Analytics events (GA4, existing property)

| Event | When it fires |
|---|---|
| `page_view` | automatic |
| `study_open` / `study_complete` | study page loaded / reader reached the footer |
| `similarity_started` / `_completed` / `_compare` / `_shared` | tool pick / result / comparison view / share |
| `transfer_started` / `_completed` / `_shared` | tool pick / result / share |
| `case_study_open`, `methodology_open` | page loaded |
| `glossary_open` | popover opened |
| `share_click` | any share (`channel`: copy / x / linkedin / native; `kind`) |
| `github_click`, `linkedin_click` | outbound links |

- Removed (not decision points): `sim_why`, `mode_change`, `glossary_search`, `glossary_view`.
- Verified locally by capturing the events.
- **GA4 dashboard setup is manual (M10):** mark key events and build the funnel — steps in `docs/launch/README.md`.

## 4. Performance audit (Lighthouse, production)

| Route | Mobile Perf | LCP | Desktop |
|---|---|---|---|
| /football | 81 | 3.7 s | 100 |
| /research/similarity | 91 | 3.3 s | 100 |
| /tools/similarity | 89 | 3.0 s | 98 |
| /tools/transfer | 95 | 2.4 s | 99 |
| /live | **71** | **5.5 s** | 99 |
| /case-studies/… | **70** | **5.5 s** | 99 |
| /glossary | 93 | 2.6 s | 98 |

Elsewhere: CLS ≤ 0.04, TBT 0–30 ms, Accessibility 100 and SEO 100 everywhere. The LCP element is always text.

**Not fixed (recommended for M10):**
- Render-blocking Google Fonts and the 27 KB stylesheet: self-host or preload the three woff2 fonts, inline critical CSS. Estimated saving 0.8–2.4 s on mobile.
- gtag.js is the largest asset (third-party, about 74 KB unused).

The www → apex redirect the audit measured (0.8 s) no longer affects share links, which all use the apex.

## 5. Accessibility audit

- **Scope:** axe-core on 18 routes at 1440 and 390 px; keyboard; headings; touch targets; reduced motion.
- **Result:** after the fixes, **every /football route is axe-clean at both widths**, with 0 console errors.

Fixed:
- **Glossary popover on desktop:** keyboard-opened popovers now take focus. Tab walks its links; Tab or Shift+Tab past either end closes it and returns focus to the term. A grace period stops the focus-scroll from closing it as it opens.
- **Scrollable tables:** the transfer results table, case-study tables, and any table that overflows are now keyboard-scrollable named regions.
- **Nested interactive content:** the league-ladder data table was inside a `role="img"` chart; it now sits outside it.
- **Link names that didn't contain the visible text:** study cards, popover study links, parent-site project cards.
- **Contrast:** the combobox hint was 4.47:1; it now uses the secondary ink colour.
- **About page headings:** the order is now valid (h1 → h2).

Already fine:
- Skip link, mobile menu (Enter / Escape / focus return), visible focus on all football routes.
- Reduced motion: no animations over 10 ms.
- Chart text alternatives.

Remaining, on the **parent site only** (`/`, `/projects`):
- `heading-order` (cards are h3 under the h1).
- Small status/tag text at 3.4–3.8:1 contrast.
- No skip link; command-bar input has no focus style.

These are pre-existing parent-theme styles, so I left them; noted for M10.

Nice-to-have: some 32–36 px touch targets (breadcrumbs, nav, glossary chips) meet WCAG 2.5.8 (24 px) but not the 44 px guideline.

## 6. Research integrity audit

Every displayed number on all 15 routes, plus meta, JSON-LD and OG text, was checked against `findings/*.md` and `outputs/**`.

**Priority list** — all OK: +27%, −13.8%, 97%, 3.6 SD / 1.9 SD, MAE 0.096, R² 0.76, AUC 0.80, Brier 0.179, 142 moves, Zirkzee, Ugarte, 4/4, 5/6.

**Display bugs fixed** (the UI misread the research; the research is unchanged):
1. **"Strongest home clubs" chart:** it showed log differences as %. Guingamp was shown as +30%; the correct value is **+35%** (Cagliari +32%, Eintracht +28%, as in the findings). Fixed in `build_research.py`.
2. **Home-edge histogram** (Study 2 page and homepage): same log-unit error.
   - "4,390 land between +20% and +30%" is really **+22% to +35%**.
   - The axis labels ±100/200% were wrong; the axis is now relabelled in true %.
   - "Spread ±77 pts" is now an SD on the log scale.
3. **Environment page:** "moves no estimate by more than 0.9 percentage points" was an early four-league figure. The final value is **0.6**.
4. **Ugarte board rank:** 138 → **137 of 206**. He is tied on similarity with Soumaré and Freuler, and the research uses shared ranks. The case study now ranks ties as the research does, and the build checks Ugarte's rank.
5. **"Similarity changed the error by 0.000":** "+0.000", and bars rounded to 0.110 vs 0.109, implied precision the research doesn't have.
   - The real values: comparables' output −0.000 (95% CI −0.002 to +0.001); all similarity +0.001 (CI −0.002 to +0.005).
   - The copy now says "nothing detectable — at most 0.002 either way", and the bars show 4 decimals.
6. **"+30% with fans"** is the pre-2020 period (team-level); it is now labelled "before 2020".
7. **Homepage:** said Study 1's "final checks … still pending". M12 is done; the copy now matches the findings.
8. **Glossary examples:**
   - Closed-doors xG is **+12%** (not "+8–14%", which is a range across metrics).
   - The 2015–19 "top 10 home players" went from +955% to +43% (all-player average +33%), not "exactly average".
9. **Case study hindsight:** the "keeps 82% into the Premier League" figure uses all 428 moves, including later seasons. It is now labelled as orientation only, not a model input.

## 7. Content and copy audit (fixed)

**Overclaiming and causal wording, softened to match what the research shows:**
- "The model knows how unsure it is" → "The model estimates its own uncertainty"
- The league ladder "decides the direction" → "accounts for the direction"
- Crowds "clearly do" / "Most of it is the crowd" → "appear to" / "About half of it disappeared without crowds"
- "We tried to find Bruno's replacement" → "We looked for Bruno's closest statistical profile in Serie A"
- The promoted-club effect "is real" / "genuinely" → "holds up" / "produced more than predicted"
- "cancel out" → "held fixed"
- "remarkably accurate" → "landed inside the 80% range for 9 of the 10 judged moves" (computed from the tallies)
- "the right number" → "close in one season"
- Live claims now state associations: "Players produce more attacking output at home"
- Transfer result: "most likely between" → "an 80% range of"

**Plain language:**
- Glossary popovers added to the case study (leakage, 80% range, MAE, R², AUC), the live tracker (intervals, SD, r), the tools index (xG, xA, per 90, 80% range) and the homepage (95% CI).
- Similarity scores now say "closer than X% of the pool".
- The homepage transfer teaser now states "attacking output only — it can't see defending, fit or injuries".

**Left as approved earlier:** the live page's "Early · Broadly stable" labels (M6 rule set).

**Stale claims also removed:** the About page still said the tools were "browser ports" of the models. M3 and M4 replaced them with precomputed results.

## 8. GitHub, About and parent site

- **`football/README.md`** in the public site repo (your choice):
  - Covers what · arc · key findings · site · methodology · data · **architecture** (raw sources → … → interactive product, mapped to real components) · reproducibility · limitations.
  - Says plainly that the research code isn't public yet.
  - Linked from the About page; excluded from deployment.
- **About page:**
  - "I'm Ayush." · "Product engineer by trade, football obsessive by choice." · "I build systems for turning football questions into data, models and usable decision tools."
  - Product engineer → Research → Engineering → Football.
  - Links: iyush.dev, GitHub, LinkedIn and email (your chosen address).
  - Person JSON-LD.
- **Parent iyush.dev:**
  - "Home Turf & Hard Opponents — `football-research/`" is the first card on the homepage and on /projects (and in the projects ItemList JSON-LD).
  - New `$ cd ~/football-research` command link; the command bar understands `cd football`; `ls` and `help` list it.
  - The football header shows "← iyush.dev" on desktop as well as in the mobile menu.
  - I did **not** change the homepage's "6 products shipped" metric — your number.
- **Launch kit** in `docs/launch/` (drafts, not posted):
  - the flagship Bruno piece, Reddit post (with prepared replies), LinkedIn post, X thread, outreach messages and target list;
  - deep links with UTM tags, the funnel, the GA4 setup, and a verified fact sheet.

## 9. Launch blockers / questions

1. **Study 1 is not frozen.** The launch checklist requires "all five studies frozen". It needs your hand-written weather conclusion and the freeze (git tag, checksum manifest, pinned packages). The site labels it provisional everywhere, and the launch kit avoids headlining it.
2. **The research sources disagree with themselves.** I didn't change these; please resolve them on the research side:
   - `findings/study5`: "out of the EPL **116%** (106–126%)", "Ligue 1 out **90%**". The evidence table `outputs/study5/m7_subgroups.md` says **117%** (107–127%) and **89%**. The site's study and transfer pages show 117 / 89 (from the export); the glossary example quotes the findings' 116. Which is right?
   - `findings/live_tracker.md` (written 20:32, 2026/27 +21.0%, 250 matches) is older than the tracker snapshot the site shows (21:10, +22.0%, 249). Regenerating the findings file should reconcile them on Monday's run.
   - Shots per SD of opponent strength: the findings tables say −10.5%; the frozen export rounds −10.45 to −10.4 (and the live baseline manifest locks −10.4).
   - The opposition page says "one player in about 4,800 shows a reliable pattern (for shots)". That matches the export (`rel_flat` = 1), but the findings text only mentions "0 reliably steeper / 0 positive". Please confirm the wording.
3. **Mobile LCP of 5.5 s on /live and the case study** (fonts / render-blocking CSS) — the M10 performance item in §4.
4. **The research code isn't public.** The README says so; publishing it (without redistributing raw Understat or odds data) is your call.
5. **GA4 key events and funnel** must be configured in the GA dashboard (manual).
6. **Parent-site accessibility leftovers** (§5).

**Dependencies:** none added. New files: `favicon.*`, `apple-touch-icon.png`, `football/README.md`, `docs/launch/*`.
