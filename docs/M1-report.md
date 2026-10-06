# M1B — Implementation report
## `iyush.dev/football` · design system + homepage

**Spec:** [M1.md](./M1.md) · **Status:** M1B done → ready for **M1C review on the running site** · **Stopped.** Nothing from M2 was started.

Run locally: `npx serve -l 4601 .` from the repo root → http://localhost:4601/football

---

## 1. Components created

Vanilla HTML/CSS/JS (no framework), so each M1 §30 contract is a CSS class with an optional `FB.*` JS helper. All live in `football/football.css` and `football/js/football.js`.

| M1 contract | Implementation |
|---|---|
| FootballHeader | `.fhead` + `.brand` ("FOOTBALL / AYUSH PAWAR"), red active indicator; < 640px: "FOOTBALL" + Menu button → full-screen overlay (`.fnav.open`) |
| FootballFooter | `.ffoot`: name, sections, external links, "Data updated / Frozen dataset" strip |
| Container · Section · Grid | `.wrap` (1280 max, 20/24/32 padding) · `.section` (96–128px rhythm) · `.grid` 4 → 8 → 12 columns with `.t-4`, `.d-3…d-12` spans |
| Eyebrow · DisplayHeading · SectionHeading · BodyText · MonoLabel | `.eyebrow` · `h1`/`.display` · `h2`/`.section-h` · `.lede`/`.body` · `.label` |
| StudyMarker · StudyTimeline | `.tl-no`/`.marker` · `.timeline` > `.tl-item` (vertical line, question/answer/evidence/CTA) |
| Finding · StatBlock | `.finding-card` · `.stats` > `.stat` |
| ChartContainer · SourceNote | `.chart` (title = what you're looking at, `.chart__summary` "In words", `.source`) · `.source` |
| Chart states | `FB.state(el, "loading" \| "empty" \| "error" \| "insufficient", {text, retry})`: skeleton, empty, error with **Try again →**, insufficient sample |
| Research figures | HTML-drawn so text never shrinks on mobile: `.hbar` (bars/ranges/dots on an axis), `.hist`, `.cols`, `.dotstrip`, `.range` |
| Button · LinkButton | `.btn` (accent CTA), `.btn--ghost`, `.link-arrow`. States: default, hover, focus, active, disabled, loading (`aria-busy`) |
| Select · SearchInput | `.input` / `select.input` / `.combo`. States: hover, focus, disabled, invalid (`aria-invalid`) + `.field__err` |
| Tooltip · GlossaryPopover · MetricTerm · GlossaryLink | `.term` (`xG ⓘ`, 44px tap area) → `.gpop`: definition, **Technical**, **View glossary →**. Bottom sheet < 640px |
| Accordion | `.acc` (`<details>`) |
| ShareButton | `.share`, labelled **Copy link**. Always copies the URL with its state |

## 2. Files changed

- `football/football.css`: rebuilt on M1 tokens (colour, type scale, spacing, grid, motion); new figure, teaser, live-table, pillar and state components
- `football/js/football.js`: overlay nav (focus trap, Esc, scroll lock), `FB.state`, popover layout, Copy link
- `football/index.html`: homepage rebuilt to M1 §10–20
- All 15 `/football` pages: shared header, footer and font link (study and tool pages keep their content and behaviour)
- `tools/similarity.html`, `tools/transfer-calculator.html`: share label changed to "Copy link" (only change)
- **New** `scripts/build_home.py`: writes the homepage figures and teaser results from `football/data/*.json` at build time. Re-run after each data export
- **New** `docs/M1.md`, `docs/M1-report.md`

## 3. Dependencies added

**None.** The Google Fonts request now loads Instrument Serif, Inter and JetBrains Mono (it used to load Newsreader and JetBrains Mono).

## 4. Responsive behaviour

- **Breakpoints:** 640 / 1024 / 1280 (M1 §6).
- **Grid:** 4 → 8 → 12 columns. Type is set per breakpoint with `clamp()`: hero 44 → 88, sections 34 → 56, stats 40 → 64.
- **Mobile is recomposed, not just stacked:**
  - Dataset strip becomes 3 rows (§21).
  - Thesis stats go vertical.
  - Timeline uses a smaller marker, with each figure under its text.
  - Figure labels move above the bars.
  - Findings stack.
  - Teasers go full width; the transfer inputs become a list.
  - Live table tightens to fit 390px without scrolling.
  - Navigation becomes a full-screen overlay.
- **Verified:** 0px horizontal overflow on all 15 routes at 1440 and 390.

## 5. Accessibility

- **Structure:** semantic landmarks, one `h1`, ordered headings, skip link.
- **Focus:** keyboard focus visible everywhere (2px `#E06A5F` ring). The mobile menu traps focus, closes on Esc and returns focus to the button.
- **Contrast (WCAG AA):** all text passes. See the token deviations in §7.
- **Touch targets:** all interactive targets ≥ 44px; inline glossary terms get an invisible 44px hit area. 0 undersized targets in the automated pass.
- **Figures:** every figure has a "What you're looking at" title, an "In words" summary and a `role="img"` label. The live table has a caption and scoped headers.
- **Colour:** never the only signal. Every value is printed and pills carry words.
- **Popovers:** dialog role, `aria-expanded`, Esc to close, focus returns to the term.
- **Motion:** `prefers-reduced-motion` turns animation off. Motion is used only for state changes (150 / 250 / 400ms).

## 6. Performance

- **No models, no player datasets on the homepage.** Before M1 the homepage loaded both model engines plus `transfer.json` (49 KB gzipped) and `similarity.json` (132 KB gzipped). Now the figures and teaser results are static HTML from `build_home.py`.
- **First load:** HTML 9 KB + CSS 12 KB + JS 9 KB + glossary 8 KB, all gzipped, plus fonts.
- **Live tracker:** the only fetch, `research.json` (18 KB gzipped). It loads lazily when scrolled near, with skeleton, error and retry states.
- **Content first:** all research content renders without JavaScript (M1 §29).

## 7. Questions / blockers for PM

1. **Colour deviations, forced by the accessibility rules.**
   - Muted text `#666666` is 3.4:1 against the background, which fails AA. Text uses `#858585` (5.3:1); `#666` is kept for rules, axes and input borders.
   - Red text uses `#E06A5F` (6.0:1). `#B83A3A` (3.5:1) is kept for fills, bars and indicators.
   - Button hover: white on `#D04A4A` is 4.4:1, so on hover the border lightens and the arrow nudges instead.
   - Approve?
2. **Transfer teaser shows a real model run.** It shows one precomputed Bruno → Inter result: 0.68 xG + xA per 90 (0.87 last season), 78% retention, 49% chance of keeping ≥75%, 80% range 0.40–1.04. That is the model's actual output, not an invented number, but §16 said not to put Bruno's output there. Keep it, or switch to a neutral example? The range is shown as 0.40–1.04 rather than "±0.20" because it is asymmetric.
3. **Live numbers have moved since the spec was written.** The 2026/27 column reads live data: home **+22.0%** (spec said +21.0%), opposition **−13.3%** (spec said −12.9%).
4. **Navigation.** Following §9, Glossary moved out of the primary nav (it was there in M0). It is still in the footer, in the mobile menu's extras, and behind every `ⓘ`. Confirm?
5. **Pages already built before M1.** The study pages, both tools, the live page and the case study existed before M1. Their behaviour is untouched; they only picked up the new tokens, header and footer. The tool pages still run the models in the browser with large JSON files, which conflicts with §29. That's a decision for M2: keep, precompute, or put behind an API.
6. **Homepage swaps.**
   - Methodology is shown as the four §18 pillars instead of M0's expandable Fan/Analyst blocks. The toggle remains on the study and methodology pages.
   - The similarity teaser is the static case-study top three (§15 wireframe). M0's interactive league selector is gone.
7. **The "+0.000" finding next to the chart.** On the Study 5 figure, own history shows 0.110 and own history + similarity shows 0.109. The real difference is −0.0004, which rounds to the "+0.000" headline, but the two printed values look 0.001 apart. Keep 3 decimals, or show 4?
8. **Study 1 has no frozen export yet.** Its figure uses the ±2–3% weather bound from the Final Summary and is labelled pending.
9. **Choices made where the spec allowed options.**
   - Display font: Instrument Serif rather than DM Serif Display.
   - Hero: no animated data-line visual (§10 made it optional).
   - Fonts are served from Google Fonts; self-hosting is a possible later improvement.
