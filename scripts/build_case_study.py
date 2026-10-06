#!/usr/bin/env python3
"""Render /football/case-studies/manchester-united-2024 (M7) from the locked Study 5 recruitment output.

    python3 scripts/build_case_study.py

Sources (nothing is modelled here; values are read, rounded, counted and compared):
  football/data/case-study.json   the locked recruitment board (Study 5 Milestone 8, exported by football_export.py):
                                  every candidate's June-2024 forecast, 80% range and 2024/25 outcome
  football/data/research.json     s5: locked-test metrics (142 moves), destination-league effects
  <research>/outputs/study5/m8_recruitment.md   guard: the counts and errors shown here must match the research's
                                  own readout (4 of 4, 5 of 6, MAE, Zirkzee's rank) or the build fails
  <research>/findings/study5_transferability.md  guard: the fit sample (334 moves), the known midfield bias, and the
                                  finding that Study 2/3 context does not improve forecasts

The full board table is the only interactive part (sort / filter in the browser over the same JSON).
"""
import html
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402

SITE = Path(__file__).resolve().parent.parent
FB = SITE / "football"
RS = Path(os.environ.get("FB_RESEARCH", Path.home() / "dev/weather_football"))
B = json.loads((FB / "data/case-study.json").read_text())["board"]
S5 = json.loads((FB / "data/research.json").read_text())["s5"]
META = json.loads((FB / "data/meta.json").read_text())
PATH = "/football/case-studies/manchester-united-2024"
AS_OF = "2024-06-01"
JUDGE_MIN = 450          # the research judges a forecast only with ≥ 450 minutes at the new club
NAME = {"EPL": "Premier League", "La_Liga": "La Liga", "Serie_A": "Serie A", "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1"}
BRIEF = {"centre-forward": "Strikers", "central midfielder": "Midfielders"}
SIGNED = ("Joshua Zirkzee", "Manuel Ugarte")
esc = html.escape


def fail(msg):
    sys.exit("build_case_study: " + msg)


def f2(x):
    return f"{x:.2f}"


M8 = re.sub(r"\s+", " ", (RS / "outputs/study5/m8_recruitment.md").read_text())
F5 = re.sub(r"\s+", " ", (RS / "findings/study5_transferability.md").read_text())


def need(text, pattern, what):
    m = re.search(pattern, text)
    if not m:
        fail(f"the research no longer says {what} (/{pattern}/) — re-check the case study against the locked output")
    return m


# ---------------------------------------------------------------- the board, as published (order = the research's ranking)
briefs = {}
for r in B:
    briefs.setdefault(r["brief"], []).append(r)
for k, rows in briefs.items():
    for i, r in enumerate(rows, 1):
        r["rank"] = i
by_name = {r["player"]: r for r in B}
for p in SIGNED:
    if p not in by_name:
        fail(f"{p} is not on the locked board")

# Players who joined a Premier League club: forecast re-made for the club they joined (same June-2024 information).
joined = {k: [r for r in rows if r["actual_league"] == "EPL" and r["pred_actual_club"] is not None] for k, rows in briefs.items()}
for k, rows in joined.items():
    for r in rows:
        r["judged"] = r["actual_minutes"] >= JUDGE_MIN
        r["inside"] = r["q10_actual_club"] <= r["actual_xgxa90"] <= r["q90_actual_club"]
        r["result"] = ("within" if r["inside"] else "outside") if r["judged"] else "not_judged"
    rows.sort(key=lambda r: -r["pred_actual_club"])
summary = {}
for k, rows in joined.items():
    j = [r for r in rows if r["judged"]]
    summary[k] = {"inside": sum(r["inside"] for r in j), "judged": len(j), "mae": sum(abs(r["actual_xgxa90"] - r["pred_actual_club"]) for r in j) / len(j),
                  "candidates": len(briefs[k])}

# guards: every headline number must match the research's own readout
cf, cm = summary["centre-forward"], summary["central midfielder"]
need(M8, rf"Judged on ≥ {JUDGE_MIN} minutes: {cf['inside']} of {cf['judged']} inside their 80% interval; mean absolute error {cf['mae']:.3f}", "the striker tally")
need(M8, rf"Judged on ≥ {JUDGE_MIN} minutes: {cm['inside']} of {cm['judged']} inside their 80% interval; mean absolute error {cm['mae']:.3f}", "the midfielder tally")
Z, U = by_name["Joshua Zirkzee"], by_name["Manuel Ugarte"]
need(M8, rf"predicted at United {f2(Z['pred'])} \(80% interval {f2(Z['q10'])}–{f2(Z['q90'])}\); rank {Z['rank']} of {cf['candidates']}", "Zirkzee's forecast and rank")
need(M8, rf"Actual 2024/25 at Manchester United: {f2(Z['actual_xgxa90'])}", "Zirkzee's actual output")
need(M8, rf"Predicted {f2(U['pred'])} \(interval {f2(U['q10'])}–{f2(U['q90'])}\), actual {f2(U['actual_xgxa90'])}", "Ugarte's forecast and outcome")
n_fit = int(need(M8, r"Model A fitted on (\d+) moves whose first destination season ended by June 2024", "the June-2024 fit sample").group(1))
mid_bias = need(F5, r"under-predicted by (0\.\d+)", "the known midfield bias").group(1)
need(F5, r"Study 2/3 context \(opponents faced, home share\) does not improve forecasts", "that Study 2/3 context does not improve forecasts")
need(F5, r"similarity adds nothing to that forecast", "that similarity adds nothing to the forecast")
target = {k: need(M8, rf"## Brief: {k} \(target profile: ([^,]+), 2023/24\)", f"the {k} target profile").group(1) for k in briefs}

ev = {r["model"]: r for r in S5["test_eval"]}["Model A"]
auc75 = next(r for r in S5["classification"] if r["threshold"] == "≥75%")["AUC Model A"]
cov = S5["coverage"][0]["coverage"]
epl_in = next(r for r in S5["dest"] if r["destination_league"] == "EPL")


# ---------------------------------------------------------------- render helpers
def track(pred, lo, hi, actual, ax_max, label):
    """PredictionVsActual: two rows on one scale — predicted (ring) with its 80% range, actual (filled dot)."""
    x = lambda v: f"{max(0, min(v, ax_max)) / ax_max * 100:.2f}%"
    inside = lo <= actual <= hi
    return f"""<div class="cs-pva" role="img" aria-label="{esc(label)}: predicted {f2(pred)} xG + xA per 90 (80% range {f2(lo)}–{f2(hi)}); actual {f2(actual)}; {"inside" if inside else "outside"} the range">
  <div class="cs-pva__r"><span class="cs-pva__k">Predicted<b>{f2(pred)}</b></span><span class="cs-pva__t"><span class="cs-band" style="left:{x(lo)};width:calc({x(hi)} - {x(lo)})"></span><span class="cs-ring" style="left:{x(pred)}"></span></span></div>
  <div class="cs-pva__r"><span class="cs-pva__k">Actual<b>{f2(actual)}</b></span><span class="cs-pva__t"><span class="cs-band cs-band--ghost" style="left:{x(lo)};width:calc({x(hi)} - {x(lo)})"></span><span class="cs-dot{" cs-dot--out" if not inside else ""}" style="left:{x(actual)}"></span></span></div>
  <div class="cs-pva__ax" aria-hidden="true"><span></span><span class="cs-pva__ticks"><i style="left:0">0</i><i style="left:50%">{ax_max / 2:.2f}</i><i style="left:100%">{ax_max:.2f}</i></span></div>
</div>"""


def result_pill(res):
    return {"within": '<span class="pill pill--final">Within range</span>', "outside": '<span class="pill pill--pending">Outside expected range</span>',
            "not_judged": f'<span class="pill">Not judged · under {JUDGE_MIN}′</span>'}[res]


def short_club(c):
    return c.replace("Wolverhampton Wanderers", "Wolves")


def joined_table(k):
    rows = joined[k]
    ax = max(max(r["q90_actual_club"], r["actual_xgxa90"]) for r in joined["centre-forward"] + joined["central midfielder"])
    ax = round(ax + 0.05, 1)
    x = lambda v: f"{max(0, min(v, ax)) / ax * 100:.2f}%"
    body = "".join(
        f'<tr class="{"signed" if r["player"] in SIGNED else ""}"><th scope="row">{esc(r["player"])}{" <small>· signed by United</small>" if r["player"] in SIGNED else ""}'
        f'<small>{esc(r["origin_club"])} → {esc(short_club(r["actual_club"]))} · {r["actual_minutes"]:,.0f}′</small>'
        + ('<small class="cs-note">Forecast floored at 0.00 by the pipeline, below its own range — the additive league effect pushed it under zero.</small>' if r["pred_actual_club"] < r["q10_actual_club"] else "")
        + '</th>'
        f'<td>{f2(r["pred_actual_club"])}<small>{f2(r["q10_actual_club"])}–{f2(r["q90_actual_club"])}</small></td><td>{f2(r["actual_xgxa90"])}</td>'
        f'<td class="cs-mini" aria-hidden="true"><span class="cs-pva__t"><span class="cs-band" style="left:{x(r["q10_actual_club"])};width:calc({x(r["q90_actual_club"])} - {x(r["q10_actual_club"])})"></span>'
        f'<span class="cs-ring" style="left:{x(r["pred_actual_club"])}"></span><span class="cs-dot{" cs-dot--out" if r["result"] == "outside" else ""}" style="left:{x(r["actual_xgxa90"])}"></span></span></td>'
        f'<td>{result_pill(r["result"])}</td></tr>' for r in rows)
    return (f'<div class="tscroll"><table class="ltable cs-joined"><caption class="sr-only">{BRIEF[k]} who joined Premier League clubs: predicted xG + xA per 90 with 80% range, actual 2024/25, and result</caption>'
            f'<thead><tr><th scope="col">Player</th><th scope="col">Predicted<small>80% range</small></th><th scope="col">Actual<small>2024/25</small></th>'
            f'<th scope="col"><span class="sr-only">Chart</span><span aria-hidden="true">0 — {ax:.1f}</span></th><th scope="col">Result</th></tr></thead><tbody>{body}</tbody></table></div>')


def shortlist(k, n=5):
    rows = briefs[k][:n]
    s = by_name[SIGNED[0] if k == "centre-forward" else SIGNED[1]]
    li = "".join(f'<li><span class="cs-rk">{r["rank"]}</span><span>{esc(r["player"])}<small>{esc(r["origin_club"])}</small></span><b>{f2(r["pred"])}</b></li>' for r in rows)
    li += (f'<li class="cs-gap" aria-hidden="true"><span></span><span>…</span><b></b></li>'
           f'<li class="signed"><span class="cs-rk">{s["rank"]}</span><span>{esc(s["player"])}<small>{esc(s["origin_club"])} · signed</small></span><b>{f2(s["pred"])}</b></li>')
    how = ("ranked by predicted Premier League output at United" if k == "centre-forward"
           else f"ranked by similarity to {target[k]} (a holding midfielder's job is mostly outside this data, so Study 4 builds this shortlist; the forecast is the risk column)")
    return f"""<div class="cs-brief"><p class="label">{BRIEF[k]} · {summary[k]['candidates']} candidates</p>
  <p class="small muted">Target profile: {esc(target[k])}, 2023/24 · {how}.</p>
  <ol class="cs-short" aria-label="{BRIEF[k]} shortlist, top {n} and the signed player">{li}</ol>
  <p class="small muted">Number = predicted xG + xA per 90 at United in 2024/25.</p></div>"""


def lens(r, extra):
    keep = r["pred"] / r["pre"] if r["pre"] else None
    p75 = f"chance of keeping ≥ 75%: {r['p_ret75'] * 100:.0f}%" if r["p_ret75"] is not None else "chance of keeping ≥ 75% not shown (2023/24 output under 0.10 — retention of tiny numbers is meaningless)"
    return f"""<dl class="cs-lens">
  <div><dt>Output expectation<small>How much attacking output might survive?</small></dt><dd>{f2(r["pred"])} xG + xA per 90 at United, from {f2(r["pre"])} in 2023/24{f" (keeps {keep * 100:.0f}%)" if keep else ""}; {p75}.</dd></div>
  <div><dt>Uncertainty<small>How wide is the prediction range?</small></dt><dd>80% range {f2(r["q10"])}–{f2(r["q90"])} (width {r["q90"] - r["q10"]:.2f}) · evidence: {esc(r["evidence"])} of qualifying history.</dd></div>
  <div><dt>Context<small>How difficult is the destination?</small></dt><dd>Into the Premier League, players keep {epl_in["vs_stay"] * 100:.0f}% of their output on average ({epl_in["vs_lo"] * 100:.0f}–{epl_in["vs_hi"] * 100:.0f}%); United's club strength is from 2023/24.</dd></div>
  <div><dt>Limitations<small>What is missing?</small></dt><dd>{extra}</dd></div>
</dl>"""


zr, ur = Z, U
z_case = f"""<article class="cs-case" id="zirkzee" aria-labelledby="z-h">
  <p class="lv-kicker">Case 01 · Striker · from Bologna</p>
  <h2 id="z-h">Joshua Zirkzee</h2>
  <div class="cs-case__g">
    <div>
      <dl class="cs-nums"><div><dt>Model prediction</dt><dd>{f2(zr["pred"])}<small>xG + xA / 90 at United</small></dd></div>
        <div><dt>Actual 2024/25</dt><dd>{f2(zr["actual_xgxa90"])}<small>{zr["actual_minutes"]:,.0f} minutes</small></dd></div>
        <div><dt>Board rank</dt><dd>{zr["rank"]} / {cf["candidates"]}<small>by expected output</small></dd></div></dl>
      <p class="cs-say">The actual output landed almost exactly on the model's prediction.</p>
      <p class="body">He kept his Bologna output almost exactly ({f2(zr["pre"])} → {f2(zr["actual_xgxa90"])}). But June-2024 data did not make him a standout: he finished {zr["rank"]}th of {cf["candidates"]} strikers by expected output, and his profile was the least like {esc(target["centre-forward"])}'s on the board (closer than only {zr["similarity"]:.0f}% of the pool). The board pointed to higher-output options — availability, price and fit are outside the data.</p>
    </div>
    <figure class="chart cs-fig"><figcaption><p class="chart__title">Zirkzee · prediction → actual</p><p class="chart__sub">xG + xA per 90 · band = 80% prediction range</p></figcaption>
      {track(zr["pred"], zr["q10"], zr["q90"], zr["actual_xgxa90"], 0.8, "Zirkzee")}
      <p class="chart__summary">Predicted {f2(zr["pred"])} (range {f2(zr["q10"])}–{f2(zr["q90"])}); actual {f2(zr["actual_xgxa90"])} — inside the range.</p></figure>
  </div>
  <details class="cs-lensbox"><summary>What signal did the model provide?</summary>{lens(zr, "Link-up play, pressing and dropping deep are not in xG + xA. One season at United, 1,378 minutes: a single outcome, not a verdict on the signing.")}</details>
</article>"""

u_case = f"""<article class="cs-case cs-case--miss" id="ugarte" aria-labelledby="u-h">
  <p class="lv-kicker">Case 02 · Central midfielder · from PSG</p>
  <h2 id="u-h">Manuel Ugarte</h2>
  <div class="cs-case__g">
    <div>
      <dl class="cs-nums"><div><dt>Model prediction</dt><dd>{f2(ur["pred"])}<small>xG + xA / 90 at United</small></dd></div>
        <div><dt>Actual 2024/25</dt><dd>{f2(ur["actual_xgxa90"])}<small>{ur["actual_minutes"]:,.0f} minutes</small></dd></div>
        <div><dt>80% range</dt><dd>{f2(ur["q10"])}–{f2(ur["q90"])}<small>{result_pill("outside")}</small></dd></div></dl>
      <p class="cs-say">At first glance, a model failure. That is exactly why it is shown.</p>
    </div>
    <figure class="chart cs-fig"><figcaption><p class="chart__title">Ugarte · prediction → actual</p><p class="chart__sub">xG + xA per 90 · band = 80% prediction range · note the smaller scale</p></figcaption>
      {track(ur["pred"], ur["q10"], ur["q90"], ur["actual_xgxa90"], 0.2, "Ugarte")}
      <p class="chart__summary">Predicted {f2(ur["pred"])} (range {f2(ur["q10"])}–{f2(ur["q90"])}); actual {f2(ur["actual_xgxa90"])} — outside the range.</p></figure>
  </div>
  <div class="cs-why">
    <h3>Why Ugarte matters</h3>
    <p class="body">Ugarte exposes two limits of the model, and the research named both before this outcome was known:</p>
    <ol class="cs-why__l">
      <li><b>A known bias.</b> The Premier League adjustment is a fixed amount, so it wipes out most of a low-output player's forecast. On the locked test, central and defensive midfielders moving into the Premier League were under-predicted by about {mid_bias} xG + xA per 90.</li>
      <li><b>A blind spot.</b> The model forecasts attacking output only. The data has no tackles, interceptions, completed passes, carries or possession — and Ugarte was bought for ball-winning.</li>
    </ol>
    <p class="body">So a player can beat the model's attacking-output expectation without the model being "wrong" about his overall football value — and the forecast was never the right tool for judging a holding midfielder.</p>
  </div>
  <details class="cs-lensbox"><summary>What signal did the model provide?</summary>{lens(ur, f"Ball-winning and build-up work are invisible to xG + xA. Midfield forecasts into the Premier League run about {mid_bias} low; compare midfielders with each other, not with strikers.")}</details>
</article>"""

timeline = """<ol class="cs-tl" aria-label="Timeline of the retrospective">
  <li><time datetime="2024-06-01">01 Jun 2024</time><b>Information cutoff</b><span>Everything after this date is hidden from the model.</span></li>
  <li><time>June 2024</time><b>Model generates predictions</b><span>Every candidate scored for Manchester United, with an 80% range.</span></li>
  <li><time>Summer 2024</time><b>Transfers happen</b><span>Players move; the model is not refitted.</span></li>
  <li><time>2024/25</time><b>Post-transfer output observed</b><span>Only now is the new season looked at.</span></li>
  <li><time>Compare</time><b>Prediction vs reality</b><span>Inside or outside the range, judged with at least 450 minutes.</span></li>
</ol>"""

limits = ["whether United should have bought a player", "whether a player was tactically suitable", "defensive contribution", "injury risk",
          "personality and adaptation", "transfer economics", "contract situation", "squad fit"]
gen = datetime.fromisoformat(META["tracker_generated_utc"])
sum_line = (f"Strikers {cf['inside']} of {cf['judged']} inside their 80% range; midfielders {cm['inside']} of {cm['judged']}.")

body = f"""<main id="main" class="cs">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li><a href="/football/research/transferability">Study 05</a></li><li aria-current="page">Manchester United 2024</li></ol></nav>

<header class="cs-hero wrap">
  <div>
    <p class="lv-kicker">Case study · Manchester United · 2024</p>
    <h1>What would the model have told Manchester United?</h1>
    <p class="lede">A leakage-free retrospective of the club's 2024 recruitment, using only information that was available on 1 June 2024.</p>
    <div class="cta-row"><button type="button" class="share" id="share">Share this case study</button></div>
  </div>
  <div class="cs-asof"><p class="label">As-of date</p><p class="cs-asof__d"><time datetime="{AS_OF}">01 Jun 2024</time></p><p class="small">Manchester United are about to enter the summer transfer window. What would this research have said about the players they could consider?</p></div>
</header>

<section class="lv-sec cs-promise" aria-labelledby="nh-h"><div class="wrap">
  <h2 id="nh-h" class="h2-sm">No hindsight.</h2>
  <p class="body">The analysis uses only information that would have been available as of 1 June 2024.</p>
  <div class="cs-avail">
    <div><p class="label">Available</p><ul class="cs-yes">
      <li>Pre-transfer player history (output up to 2023/24)</li><li>League context (league effects fitted on earlier moves)</li><li>Player age at the move</li>
      <li>Destination context (Manchester United's 2023/24 club strength)</li><li>A model trained on {n_fit} earlier moves only — none after June 2024</li></ul></div>
    <div><p class="label">Not available</p><ul class="cs-no">
      <li>Post-transfer performance</li><li>Future seasons</li><li>Actual transfer outcome</li><li>Any information from after 1 June 2024</li></ul></div>
  </div>
  {timeline}
</div></section>

<section class="lv-sec" aria-labelledby="rq-h"><div class="wrap">
  <p class="lv-kicker">The recruitment board</p>
  <p class="body">Manchester United needed attacking and midfield recruitment. The candidate pool: every player in La Liga, Serie A, the Bundesliga and Ligue 1 with ≥ 1,500 minutes in 2023/24 whose Study 4 role is centre-forward or central / defensive midfielder.</p>
  <h2 id="rq-h" class="h2-sm cs-q"><span class="lv-claim__l">Recruitment question</span>Who would the model have expected to translate successfully?</h2>
  <div class="cs-briefs">{shortlist("centre-forward")}{shortlist("central midfielder")}</div>
  <p class="source">Study 05 · Milestone 8 recruitment board, as of 1 June 2024 · the full board is at the bottom of the page</p>
</div></section>

<section class="lv-sec" aria-label="Two signings"><div class="wrap cs-cases">{z_case}{u_case}</div></section>

<section class="lv-sec" aria-labelledby="res-h"><div class="wrap">
  <p class="lv-kicker">The real test</p>
  <h2 id="res-h" class="h2-sm">Candidates who joined Premier League clubs</h2>
  <p class="body" style="max-width:46em">For every board player who moved to the Premier League that summer, the forecast was re-made for the club he actually joined, using the same June-2024 information. A forecast is judged only with at least {JUDGE_MIN} minutes.</p>
  <div class="cs-results">
    <div class="cs-res"><p class="cs-res__n">{cf["inside"]} / {cf["judged"]}</p><h3>The striker predictions held up.</h3>
      <p class="body">All {cf["judged"]} evaluated striker transfers landed within the model's 80% prediction range (mean absolute error {cf["mae"]:.3f}). One retrospective evaluation — not proof of predictive success.</p>
      {joined_table("centre-forward")}</div>
    <div class="cs-res"><p class="cs-res__n">{cm["inside"]} / {cm["judged"]}</p><h3>Midfield was harder.</h3>
      <p class="body">Five of six evaluated midfielders landed within the model's 80% prediction range (mean absolute error {cm["mae"]:.3f}). The forecasts sit visibly low — the known bias — and Ugarte is the exception.</p>
      {joined_table("central midfielder")}</div>
  </div>
  <p class="source">Ring = prediction, band = 80% range, dot = actual 2024/25 · xG + xA per 90 · Study 05 Milestone 8</p>
</div></section>

<section class="lv-sec cs-lesson" aria-labelledby="ls-h"><div class="wrap">
  <p class="lv-kicker">The biggest lesson</p>
  <h2 id="ls-h">A recruitment model can be useful without being a complete player model.</h2>
  <p class="lede">The case study shows both sides of the system. It can make remarkably accurate attacking-output predictions for some transfers, while missing important dimensions of players whose value isn't primarily captured by attacking statistics.</p>
</div></section>

<section class="lv-sec" aria-labelledby="rc-h"><div class="wrap lv-grid">
  <div><p class="lv-kicker">How the studies fit together</p><h2 id="rc-h" class="h2-sm">Finding a player and forecasting him are different jobs.</h2>
    <p class="body">Study 4 finds statistically similar players; Study 5 estimates whether their output is likely to survive a league move. In this case study the midfield shortlist comes from Study 4 and the forecast from Study 5. Similarity finds candidates — it adds nothing to the forecast itself.</p>
    <p class="body">Study 3 explains why raw output is never read on its own. But for forecasting a move, the locked tests found that adjusting for opponents faced or home share did not improve the forecast; what carries the signal is the player's own three-season history, his age and the strength of the two clubs and leagues.</p></div>
  <div class="cs-flow" aria-label="Research arc">
    <div><p class="label">Study 04 · Similarity</p><p>“Who looks like him?”</p></div><span aria-hidden="true">↓</span>
    <div><p class="label">Study 05 · Transferability</p><p>“What happens when he moves?”</p></div><span aria-hidden="true">↓</span>
    <div class="cs-flow__in"><p class="label">Forecast inputs</p><p>Three-season output · age · both clubs' strength · both leagues</p></div>
  </div>
</div></section>

<section class="lv-sec" aria-labelledby="mt-h"><div class="wrap">
  <p class="lv-kicker">Method</p><h2 id="mt-h" class="h2-sm">How was this evaluated?</h2>
  <details class="cs-drawer"><summary>What we knew — and deliberately didn't — as of 1 June 2024</summary>
    <div class="lv-grid"><div><p class="label">Known</p><ul class="cs-yes"><li>Each player's output and minutes up to 2023/24 (three-season level where available)</li><li>League effects and club-strength effects, fitted on {n_fit} moves whose first destination season ended by June 2024 (2016/17–2023/24)</li><li>Age at the move; the destination club's 2023/24 strength</li><li>Prediction ranges from the model's out-of-sample errors in rolling folds 2019/20–2023/24</li></ul></div>
    <div><p class="label">Deliberately not known</p><ul class="cs-no"><li>Any 2024/25 performance</li><li>Later seasons</li><li>Who actually signed whom — used only afterwards, to choose which club to re-score a player for, still with 2023/24 club strength</li></ul></div></div></details>
  <details class="cs-drawer"><summary>Is this a new model?</summary>
    <p class="body">No. The case study is an application of the locked Study 5 model (Model A: context + three-season level), refitted only on moves available by June 2024. Predictions were generated using information available before the transfer window and compared with post-transfer output afterwards. No forecast on this page was changed after the outcome was known.</p></details>
  <div class="cs-perf">
    <div><p class="label">Locked test · overall model, not this case study</p>
      <dl class="cs-nums cs-nums--sm"><div><dt>Unseen moves</dt><dd>{ev["n"]}</dd></div><div><dt>MAE</dt><dd>{ev["MAE"]:.3f}</dd></div><div><dt>R²</dt><dd>{ev["R²"]:.2f}</dd></div><div><dt>AUC · keeps ≥ 75%</dt><dd>{auc75:.2f}</dd></div></dl>
      <p class="small muted">The model fixed before the test, scored once on moves in 2023/24–2025/26. Its 80% ranges covered {cov * 100:.0f}% of outcomes. These are the model's overall numbers; the Manchester United results above are a separate, much smaller retrospective.</p></div>
  </div>
</div></section>

<section class="lv-sec" aria-labelledby="lim-h"><div class="wrap lv-grid">
  <div><p class="lv-kicker">Limitations</p><h2 id="lim-h" class="h2-sm">What this case study cannot tell us</h2>
    <p class="body">This is a performance-output model, not a complete recruitment department.</p></div>
  <ul class="cs-limits">{"".join(f"<li>{esc(l[0].upper() + l[1:])}</li>" for l in limits)}</ul>
</div></section>

<section class="lv-sec" aria-labelledby="board-h"><div class="wrap">
  <p class="lv-kicker">The full board</p>
  <h2 id="board-h" class="h2-sm">Every candidate, as of 1 June 2024.</h2>
  <div class="panel">
    <div class="board-ctl">
      <div class="field">
        <span class="label" id="brief-lab">Brief</span>
        <div class="seg" id="brief" role="group" aria-labelledby="brief-lab">
          <button type="button" data-v="centre-forward" aria-pressed="true">Strikers</button>
          <button type="button" data-v="central midfielder" aria-pressed="false">Central midfielders</button>
        </div>
      </div>
      <div class="field combo">
        <label class="label" for="filter">Filter by player or club</label>
        <input class="input" id="filter" type="search" placeholder="e.g. Zirkzee" />
      </div>
    </div>
    <p class="source" id="brief-note" style="margin-bottom:10px"></p>
    <div class="board-scroll" tabindex="0" role="region" aria-label="Recruitment board table">
      <table id="board"><caption class="sr-only" id="board-cap"></caption><thead></thead><tbody><tr><td class="analysing">Loading the board…</td></tr></tbody></table>
    </div>
    <p class="source" style="margin-top:12px">Predicted = expected xG + xA per 90 at Manchester United in 2024/25, with the 80% range. Retention = predicted ÷ 2023/24 output. P(≥75%) is blank when 2023/24 output was below 0.10. Similarity = closer than X% of the candidate pool to the target profile (strikers: {esc(target["centre-forward"])} 2023/24; midfielders: {esc(target["central midfielder"])} 2023/24). Actual = 2024/25 output wherever the player played; blank if he left the five leagues or didn't play — outcomes outside the Premier League are not a test of the forecast.</p>
  </div>
</div></section>

<section class="lv-sec cs-cta" aria-labelledby="cta-h"><div class="wrap">
  <h2 id="cta-h">Want to run the model yourself?</h2>
  <div class="cs-cta__b"><a class="btn" href="/football/tools/transfer">Try the Transfer Calculator <span class="arr" aria-hidden="true">→</span></a><a class="btn btn--ghost" href="/football/tools/similarity">Find Similar Players</a></div>
  <p class="body">Or <a href="/football/research">go back to the research</a>.</p>
</div></section>
</main>

<script>
// Share + the full board (sort / filter only; every value is the locked research output).
document.addEventListener("DOMContentLoaded", function () {{
  "use strict";
  var FB = window.FB;
  FB.share(document.getElementById("share"), function () {{ return "What would the model have told Manchester United in 2024?"; }});
  var SIGNED = {{ "Joshua Zirkzee": 1, "Manuel Ugarte": 1 }};
  var COLS = [
    {{ k: "rank", h: "#" }}, {{ k: "player", h: "Player" }}, {{ k: "origin_club", h: "From" }}, {{ k: "age_at_move", h: "Age" }},
    {{ k: "pre", h: "2023/24" }}, {{ k: "pred", h: "Predicted" }}, {{ k: "retention", h: "Retention" }}, {{ k: "p_ret75", h: "P(≥75%)" }},
    {{ k: "similarity", h: "Similarity" }}, {{ k: "actual_xgxa90", h: "Actual 2024/25" }}
  ];
  var B, brief = "centre-forward", sortK = "rank", sortDir = 1, filter = "";
  var thead = document.querySelector("#board thead"), tbody = document.querySelector("#board tbody");
  function num(v, d) {{ return v == null || isNaN(v) ? "—" : Number(v).toFixed(d); }}
  function renderHead() {{
    thead.innerHTML = "<tr>" + COLS.map(function (c) {{
      var s = c.k === sortK ? (sortDir > 0 ? "ascending" : "descending") : "none";
      return '<th scope="col" aria-sort="' + s + '"><button type="button" data-k="' + c.k + '">' + c.h + "</button></th>";
    }}).join("") + "</tr>";
  }}
  function render() {{
    var rows = B.filter(function (r) {{ return r.brief === brief; }});
    var f = FB.fold(filter.trim());
    if (f) rows = rows.filter(function (r) {{ return FB.fold(r.player + " " + r.origin_club + " " + (r.actual_club || "")).indexOf(f) >= 0; }});
    rows = rows.slice().sort(function (a, b) {{
      var x = a[sortK], y = b[sortK];
      if (x == null && y == null) return a.rank - b.rank;
      if (x == null) return 1; if (y == null) return -1;
      return (typeof x === "string" ? x.localeCompare(y) : x - y) * sortDir || a.rank - b.rank;
    }});
    document.getElementById("board-cap").textContent = (brief === "centre-forward" ? "Strikers" : "Central midfielders") + " board, " + rows.length + " players, sorted by " + COLS.filter(function (c) {{ return c.k === sortK; }})[0].h;
    tbody.innerHTML = rows.length ? rows.map(function (r) {{
      var act = r.actual_xgxa90 == null ? "—" : num(r.actual_xgxa90, 2) + " <small>" + FB.esc((r.actual_club || "") + (r.actual_minutes ? " · " + Math.round(r.actual_minutes).toLocaleString("en-GB") + "′" : "")) + "</small>";
      return '<tr class="' + (SIGNED[r.player] ? "signed" : "") + '">' +
        "<td>" + r.rank + "</td>" +
        '<td class="wrap-ok">' + FB.esc(r.player) + (SIGNED[r.player] ? " <small>· signed</small>" : "") + "</td>" +
        '<td class="wrap-ok">' + FB.esc(r.origin_club) + " <small>" + FB.LEAGUE_NAME[r.origin_league] + "</small></td>" +
        "<td>" + num(r.age_at_move, 1) + "</td><td>" + num(r.pre, 2) + "</td>" +
        "<td>" + num(r.pred, 2) + " <small>" + num(r.q10, 2) + "–" + num(r.q90, 2) + "</small></td>" +
        "<td>" + (r.retention == null ? "—" : FB.pct(r.retention)) + "</td><td>" + (r.p_ret75 == null ? "—" : FB.pct(r.p_ret75)) + "</td>" +
        "<td>" + num(r.similarity, 0) + '</td><td class="wrap-ok">' + act + "</td></tr>";
    }}).join("") : '<tr><td colspan="' + COLS.length + '" class="muted">No candidate matches “' + FB.esc(filter) + "”.</td></tr>";
    document.getElementById("brief-note").textContent = brief === "centre-forward"
      ? "Ranked by predicted Premier League output at United. Target profile for similarity: {esc(target["centre-forward"])}, 2023/24."
      : "Ranked by similarity to {esc(target["central midfielder"])}'s 2023/24 profile; the forecast is the risk column. Midfield forecasts sit low (the model's known bias) — compare midfielders with each other, not with strikers.";
  }}
  FB.load("case-study").then(function (d) {{
    B = d.board;
    var seen = {{}}; B.forEach(function (r) {{ seen[r.brief] = (seen[r.brief] || 0) + 1; r.rank = seen[r.brief]; }});   // the research's own order
    renderHead(); render();
    thead.addEventListener("click", function (e) {{
      var b = e.target.closest("button[data-k]"); if (!b) return;
      var k = b.getAttribute("data-k");
      if (k === sortK) sortDir = -sortDir; else {{ sortK = k; sortDir = (k === "rank" || k === "player" || k === "origin_club" || k === "age_at_move") ? 1 : -1; }}
      renderHead(); render();
      thead.querySelector('button[data-k="' + k + '"]').focus();
    }});
    document.getElementById("brief").addEventListener("click", function (e) {{
      var b = e.target.closest("button[data-v]"); if (!b) return;
      brief = b.getAttribute("data-v"); sortK = "rank"; sortDir = 1;
      FB.$$("#brief button").forEach(function (x) {{ x.setAttribute("aria-pressed", x === b ? "true" : "false"); }});
      renderHead(); render();
    }});
    document.getElementById("filter").addEventListener("input", function (e) {{ filter = e.target.value; render(); }});
  }}).catch(function (e) {{ FB.fail(document.querySelector("#board tbody"), e); }});
}});
</script>"""

title = "What would the model have told Manchester United in 2024?"
desc = (f"A leakage-free retrospective using only what was known on 1 June 2024. Zirkzee: {f2(Z['pred'])} predicted → {f2(Z['actual_xgxa90'])} actual xG + xA per 90. "
        f"Ugarte: {f2(U['pred'])} → {f2(U['actual_xgxa90'])}, outside the range. {sum_line}")
ld = {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc, "url": fb_chrome.SITE + PATH,
      "image": fb_chrome.SITE + "/football/og/manchester-united-2024.png", "author": {"@id": "https://iyush.dev/#person"},
      "isPartOf": {"@id": "https://iyush.dev/football#site"}, "about": ["Manchester United", "Joshua Zirkzee", "Manuel Ugarte", "football transfers"]}
doc = (fb_chrome.head(PATH, title + " · Home Turf & Hard Opponents", desc, title, "manchester-united-2024.png", ld)
       + "\n<body>\n" + fb_chrome.header(PATH) + "\n\n" + body + "\n\n" + fb_chrome.footer(gen.strftime("%b %Y")) + "\n</body>\n</html>\n")
(FB / "case-studies/manchester-united-2024.html").write_text(doc)
print(f"case study: {len(doc) / 1024:.1f} KB · strikers {cf['inside']}/{cf['judged']} (MAE {cf['mae']:.3f}) · midfielders {cm['inside']}/{cm['judged']} (MAE {cm['mae']:.3f}) · "
      f"Zirkzee {f2(Z['pred'])}→{f2(Z['actual_xgxa90'])} rank {Z['rank']}/{cf['candidates']} · Ugarte {f2(U['pred'])}→{f2(U['actual_xgxa90'])} · guards ok")
