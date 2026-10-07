#!/usr/bin/env python3
"""Render /football/tools/transfer (M4): the static shell + research context sections. Every number in the static
sections is read from football/data/research.json (Study 5 tables) or football/data/transfer/index.json at build time;
the calculator itself is football/js/transfer.js reading the precomputed predictions.

    python3 scripts/build_transfer_page.py
"""
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402

FB = Path(__file__).resolve().parent.parent / "football"
R = json.loads((FB / "data/research.json").read_text())["s5"]
META = json.loads((FB / "data/meta.json").read_text())
IX = json.loads((FB / "data/transfer/index.json").read_text())
PATH = "/football/tools/transfer"
NAME = {"EPL": "Premier League", "La_Liga": "La Liga", "Serie_A": "Serie A", "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1"}
esc = html.escape

ev = {r["model"]: r for r in R["test_eval"]}
steps = [("Naive", "post = pre", "naive"), ("Role average", "pull toward the role average", "shrinkage"),
         ("Context", "age, minutes, both clubs' strength, leagues", "M3 context"), ("Final model", "context + three-season history", "Model A")]
prog = "".join(f'<tr{" class=\"hot\"" if k == "Model A" else ""}><th scope="row">{a}<small>{esc(b)}</small></th><td>{ev[k]["MAE"]:.3f}</td><td>{ev[k]["R²"]:.2f}</td></tr>'
               for a, b, k in steps)
n_test = ev["Model A"]["n"]
pair = [r for r in R["test_paired"] if r["model"] == "Model A" and r["vs"] == "naive"][0]
dest = {r["destination_league"]: r for r in R["dest"]}
orig = {r["origin_league"]: r for r in R["origin"]}
league_rows = "".join(
    f'<tr><th scope="row">{NAME[k]}</th><td>{dest[k]["vs_stay"] * 100:.0f}%<small>{dest[k]["vs_lo"] * 100:.0f}–{dest[k]["vs_hi"] * 100:.0f}%</small></td>'
    f'<td>{orig[k]["vs_stay"] * 100:.0f}%<small>{orig[k]["vs_lo"] * 100:.0f}–{orig[k]["vs_hi"] * 100:.0f}%</small></td><td>{dest[k]["n"]}</td></tr>'
    for k in IX["leagues"])
ov = R["overall"][0]
cov = R["coverage"][0]
cls = [r for r in R["classification"] if "75" in r["threshold"]][0]

DESC = ("Estimate how much of a player's attacking output may survive a move between Europe's top five leagues — "
        "expected xG + xA per 90, retention, the chance of keeping 75% and an 80% prediction range, from Study 5's validated model.")
ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Transfer Calculator · Home Turf & Hard Opponents",
      "url": fb_chrome.SITE + PATH, "applicationCategory": "SportsApplication", "operatingSystem": "Any", "description": DESC,
      "isPartOf": {"@id": "https://iyush.dev/football#site"}, "author": {"@id": "https://iyush.dev/#person"}}

body = f"""<main id="main">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li><a href="/football/tools">Tools</a></li><li aria-current="page">Transfer calculator</li></ol></nav>

<section class="sx-hero wrap" aria-labelledby="t-title">
  <p class="eyebrow">Tool <b>·</b> Study 05</p>
  <h1 id="t-title">Will his game travel?</h1>
  <p class="lede">Estimate how much of a player's attacking output may survive a move between European leagues.</p>
  <p class="callout tr-qual"><span class="label" style="display:block;margin-bottom:6px">What this predicts</span>The model predicts post-transfer attacking output using player history, league context and transfer characteristics. It does not predict overall player quality or career success.</p>
</section>

<section class="wrap" aria-label="Run a transfer prediction">
  <form class="sx-form tr-form" id="t-form" data-step="1" novalidate>
    <p class="wz-count label" id="wz-count" aria-live="polite">Step 1 / 3</p>
    <div class="wz-step is-current" data-n="1">
      <div class="field combo">
        <label class="label" for="t-player">Player</label>
        <input class="input" id="t-player" type="text" autocomplete="off" placeholder="Finding players…" disabled aria-describedby="t-count t-hist t-player-err" />
        <p class="field__err" id="t-player-err" hidden>Select a player to continue.</p>
        <p class="sx-hint" id="t-hist" aria-live="polite"></p>
        <p class="sx-hint" id="t-count"></p>
      </div>
      <div class="wz-nav"><button type="button" class="btn" data-next>Next <span class="arr" aria-hidden="true">→</span></button></div>
    </div>
    <div class="wz-step" data-n="2">
      <p class="tr-q label">Where is he moving?</p>
      <div class="tr-pair">
        <div class="field"><span class="label">From</span><p class="tr-from input" id="t-from" aria-live="polite">—</p></div>
        <div class="field"><label class="label" for="t-to">To</label><select class="input" id="t-to" disabled></select>
          <p class="field__err" id="t-to-err" hidden>Select a destination league.</p></div>
      </div>
      <div class="wz-nav"><button type="button" class="btn btn--ghost" data-prev><span aria-hidden="true">←</span> Back</button><button type="button" class="btn" data-next>Next <span class="arr" aria-hidden="true">→</span></button></div>
    </div>
    <div class="wz-step" data-n="3">
      <div class="field">
        <label class="label" for="t-club">Destination club <button type="button" class="term term--ico" data-term="club-strength" aria-label="Why the club matters"></button></label>
        <select class="input" id="t-club" disabled></select>
        <p class="field__err" id="t-club-err" hidden>Select a destination club.</p>
        <p class="sx-hint">Club strength changes expected retention, so the model always uses a club. Not sure? Pick “A newly promoted club” or the club you're curious about.</p>
      </div>
      <div class="wz-nav"><button type="button" class="btn btn--ghost" data-prev><span aria-hidden="true">←</span> Back</button></div>
    </div>
    <div class="sx-go"><button type="submit" class="btn">Run prediction <span class="arr" aria-hidden="true">→</span></button></div>
  </form>
</section>

<section class="wrap sx-results" id="results" aria-label="Transfer prediction">
  <div id="t-out" aria-live="polite">
    <div class="sx-empty"><p class="sx-empty__t">Pick a player, a league and a club.</p><p>The model estimates his first-season xG + xA per 90 after the move — and how unsure it is.</p>
    <p class="sx-hint">Try <a href="?player=bruno-fernandes&amp;from=premier-league&amp;to=serie-a&amp;club=inter">Bruno Fernandes → Inter</a>.</p></div>
  </div>
  <p class="tr-links"><a class="link-arrow" href="/football/case-studies/manchester-united-2024">See the model tested against Manchester United's 2024 recruitment <span class="arr" aria-hidden="true">→</span></a></p>
</section>

<section class="section" aria-labelledby="ctx-h">
  <div class="wrap grid">
    <div class="d-5">
      <h2 class="h2-sm" id="ctx-h">What usually happens when players move?</h2>
      <p class="body" style="margin-top:16px">Output drops after any strong season, move or no move — {{regression-to-the-mean|regression to the mean}}. So Study 5 compares movers with {{stayers|comparable players who stayed}}: same club, role, output and age. Against them, the average move cost about 3%: movers kept <b>{ov["vs_stay"] * 100:.0f}%</b> (95% {{interval|confidence interval}} {ov["vs_lo"] * 100:.0f}–{ov["vs_hi"] * 100:.0f}%).</p>
      <p class="body">One {{league-ladder|ladder of league difficulty}} accounts for the direction: hardest to enter is the Premier League, easiest the Bundesliga and Ligue 1.</p>
    </div>
    <div class="d-6 d-end">
      <div class="tscroll"><table class="tr-table"><caption class="sr-only">Output kept vs comparable stayers, by league</caption>
        <thead><tr><th scope="col">League</th><th scope="col">Moving into</th><th scope="col">Moving out of</th><th scope="col">Moves in</th></tr></thead>
        <tbody>{league_rows}</tbody></table></div>
      <p class="source">Study 05 · {ov["n"]} summer moves 2016/17–2025/26 · xG + xA per 90 vs comparable stayers · 95% intervals</p>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="mod-h">
  <div class="wrap grid">
    <div class="d-6">
      <h2 class="h2-sm" id="mod-h">How much does context improve the prediction?</h2>
      <div class="tscroll" style="margin-top:20px"><table class="tr-table tr-prog"><caption class="sr-only">Prediction error by model, locked test</caption>
        <thead><tr><th scope="col">Model</th><th scope="col">{{mae|MAE}}</th><th scope="col">{{r-squared|R²}}</th></tr></thead><tbody>{prog}</tbody></table></div>
      <p class="body" style="margin-top:12px">Each step adds information, while the final model is evaluated only once on unseen transfers. Lower MAE and higher R² are better.</p>
    </div>
    <div class="d-5 d-end">
      <div class="tr-valid">
        <p class="label">Model validation</p>
        <p class="tr-valid__n">{n_test}</p><p class="tr-valid__l">unseen transfers</p>
        <dl><div><dt>Test period</dt><dd>2023/24 — 2025/26</dd></div><div><dt>Locked</dt><dd>Model fixed before the test seasons were opened</dd></div>
        <div><dt>Beat the naive guess by</dt><dd>{-pair["MAE difference"]:.3f} xG + xA per 90 (CI {-pair["hi"]:.3f}–{-pair["lo"]:.3f})</dd></div>
        <div><dt>≥75% probability</dt><dd>{{auc|AUC}} {cls["AUC Model A"]:.2f} · {{brier|Brier}} {cls["Brier Model A"]:.3f} vs {cls["Brier base rate"]:.3f}</dd></div>
        <div><dt>80% ranges</dt><dd>covered {cov["coverage"] * 100:.0f}% of test moves</dd></div></dl>
        <p class="small">This prediction model was fixed before the test seasons and evaluated once on {n_test} unseen moves. The calculator uses the same specification refitted on all {IX["n_fit"]} moves.</p>
      </div>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="fail-h">
  <div class="wrap grid">
    <div class="d-6">
      <p class="label" style="color:var(--accent-text)">Known weakness</p>
      <h2 class="h2-sm" id="fail-h">Where the model can fail</h2>
      <p class="body" style="margin-top:16px">The model is built primarily around attacking output. It cannot see defensive actions, completed passes, carries or possession. And its league effect is a fixed amount, not a percentage, so low-output central midfielders moving into the Premier League are under-predicted by about 0.06 xG + xA per 90.</p>
      <div class="fail-ex"><p class="fail-ex__n">Manuel Ugarte</p><p class="small muted">Manchester United, summer 2024 — standing at 1 June 2024 with only what was known then.</p>
        <div class="hbar" role="img" aria-label="Predicted 0.02, actual 0.14 xG + xA per 90">
          <div class="hbar__row"><span class="hbar__lbl">Predicted</span><span class="track"><span class="bar" style="width:11.4%"></span></span><span class="hbar__v">0.02</span></div>
          <div class="hbar__row"><span class="hbar__lbl">Actual</span><span class="track"><span class="bar bar--hot" style="width:80%"></span></span><span class="hbar__v">0.14</span></div></div>
        <p class="source" style="margin-top:8px">xG + xA per 90 · predicted range 0.01–0.05 · Study 05 case study</p></div>
      <p class="body">Ugarte is a useful example of why model output should not be interpreted as a complete player evaluation: he was bought for defensive work this data cannot see.</p>
    </div>
    <div class="d-5 d-end">
      <h2 class="h2-sm">What this doesn't tell you</h2>
      <div class="sx-knows" style="grid-template-columns:1fr"><div><p class="label">The model does not predict</p><ul class="sx-not">
        <li>Injuries</li><li>Adaptation outside attacking output</li><li>Defensive contribution</li><li>Possession or carrying contribution</li><li>Transfer fee</li><li>Contract</li><li>Team tactics</li><li>Fixture congestion</li><li>Cup competition</li><li>Overall player value</li></ul></div></div>
      <p class="prov"><span class="label">Scope</span>Forwards and midfielders with ≥ {IX["min_minutes"]} minutes in {IX["pre_season"]} · defenders and goalkeepers excluded<br><span class="label">Data</span>Understat · football-data.co.uk odds (club strength) · Transfermarkt-derived dates of birth</p>
    </div>
  </div>
</section>

<section class="section" aria-labelledby="how-h">
  <div class="wrap grid">
    <div class="d-6">
      <h2 class="h2-sm" id="how-h">How the prediction is made</h2>
      <div class="acc" style="margin-top:20px"><details><summary><span class="label">Technical detail</span><span class="acc__h">Study 5's final model</span></summary><div class="acc__body">
        <p><b>Target.</b> First-season xG + xA per 90 after a summer league move (≥ 900 minutes before and after). {{retention|Retention}} = after ÷ before.</p>
        <p><b>Inputs.</b> Last season's output and the three-season level (both by role group), seasons of history, age (with a curve), minutes, origin and destination league, and both clubs' pre-match market strength, plus a promoted-club term. Nothing else: role, consistency, profile distinctiveness, penalty duties and loans were tested and added nothing.</p>
        <p><b>Uncertainty.</b> From the model's own out-of-sample errors in rolling folds (2019/20–2025/26), per role group: that gives the 80% prediction range and the chance of keeping ≥ 75%, which is only reported when last season's output is at least {IX["ret_floor"]:.2f}.</p>
        <p><b>Precomputed.</b> Every eligible player × destination club ({len(IX["players"])} × {len(IX["clubs"])}) was predicted with the research's production model; this page only looks results up. Inputs as of {IX["pre_season"]}, for a move in {IX["dest_season"]}.</p>
        <p><b>No “transfer score”.</b> The research has no validated 0–100 rating, so this tool shows the model's actual outputs and their uncertainty instead.</p>
      </div></details></div>
      <p style="margin-top:20px"><a class="link-arrow" href="/football/research/transferability">Read Study 05 <span class="arr" aria-hidden="true">→</span></a></p>
    </div>
    <div class="d-5 d-end">
      <aside class="sx-disc" style="margin-top:0"><p class="label">Looking for similar players instead?</p>
        <p>Similarity describes player profiles. Transferability estimates how much output may survive a league move.</p>
        <p><a class="link-arrow" href="/football/tools/similarity">Open Similarity Explorer <span class="arr" aria-hidden="true">→</span></a></p></aside>
    </div>
  </div>
</section>
</main>

<script src="/football/js/transfer.js" defer></script>"""

body = re.sub(r"\{([a-z0-9-]+)\|([^}]+)\}", r'<button type="button" class="term" data-term="\1">\2</button>', body)
updated = datetime.fromisoformat(META["tracker_generated_utc"]).strftime("%b %Y")
doc = (fb_chrome.head(PATH, "Will His Game Travel? — Football Transfer Prediction", DESC, "Will his game travel?",
                      "transfer-calculator.png", ld, "website")
       + "\n<body>\n" + fb_chrome.header(PATH) + "\n\n" + body + "\n\n" + fb_chrome.footer(updated) + "\n</body>\n</html>\n")
(FB / "tools/transfer.html").write_text(doc)
print("tools/transfer.html", f"{len(doc) / 1024:.1f} KB")
