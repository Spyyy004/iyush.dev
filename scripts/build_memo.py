#!/usr/bin/env python3
"""Render a club research memo (M10A outreach series) from content/memos/<slug>.json.

    python3 scripts/build_memo.py club-brugge          # -> football/research/club-brugge.html
    python3 scripts/build_memo.py club-brugge --pdf    # + docs/outreach/<slug>/<slug>-memo.pdf (Playwright)

The research sections are shared by every memo in the series; only the framing (recipient, why this club, what the
model can't do for this club, the next question) comes from the club's JSON. Nothing is modelled here: chart values
are read from the Study 5 tables, and every number quoted in prose is checked against the findings files (the build
fails if the research stops saying it).

Memo pages are public but unlisted: noindex, not in the nav, the sitemap or any index page.
"""
import csv
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402

SITE = Path(__file__).resolve().parent.parent
FB = SITE / "football"
RS = Path(os.environ.get("FB_RESEARCH", Path.home() / "dev/weather_football"))
T5 = RS / "outputs/study5/tables"
esc = html.escape
NAME = {"EPL": "Premier League", "La_Liga": "La Liga", "Serie_A": "Serie A", "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1"}


def fail(msg):
    sys.exit("build_memo: " + msg)


def flat(p):
    return re.sub(r"\s+", " ", p.read_text())


F4 = flat(RS / "findings/study4_player_similarity.md")
F5 = flat(RS / "findings/study5_transferability.md")
METH = flat(FB / "methodology.html")

# Every number the prose quotes, and where the research says it. Fails loudly on drift.
GUARDS = [
    (METH, r"18,011", "18,011 matches"), (METH, r"8,348", "8,348 players"), (FB / "index.html", r"525,328", "525,328 player-matches"),
    (METH, r"2015/16–2024/25", "the frozen 2015/16–2024/25 dataset"),
    (F5, r"\*\*2,917 between leagues\*\*", "2,917 cross-league moves"), (F5, r"\*\*Primary population: 428 summer cross-league moves\*\*, ≥ 900 minutes", "428 primary moves at ≥ 900 min"),
    (F5, r"97% of xG \+ xA per 90 against comparable players who stayed \(CI 93–101%\)", "97% (93–101%)"),
    (F5, r"pair-specific terms add nothing \(F-test p = 0\.91\)", "one ladder (p = 0.91)"),
    (F5, r"−2\.0% per year", "−2% per year of age"),
    (F5, r"weaker third of destination clubs 79%, stronger third 106%; step up in club strength 114%, step down 81%", "club strength 79/106/114/81"),
    (F5, r"−9% per SD of last-season change", "−9% per SD recent jump"),
    (F5, r"scored once on 142 moves in 2023/24–2025/26", "locked test 142 moves"),
    (F5, r"\*\*Model A\*\* \| \*\*0\.096\*\* \| \*\*0\.76\*\*", "Model A 0.096 / 0.76"),
    (F5, r"rolling origin, 157 predictions", "similarity experiment 157 rolling predictions"),
    (F5, r"\+ comparables' output \| −0\.000 \(−0\.002 to \+0\.001\)", "comparables Δ −0.000"),
    (F5, r"comparables only \(Model B\) \| \+0\.019 \(\+0\.004 to \+0\.034\) — and no better than post = pre", "Model B +0.019"),
    (F5, r"27% of league movers miss 900 minutes in the new league \(stayers 20%\)", "27% survivorship"),
    (F5, r"Ugarte: predicted 0\.02 \(0\.01–0\.05\), actual 0\.14", "Ugarte 0.02 → 0.14"),
    (F5, r"under-predicted by 0\.06", "midfield-into-EPL bias 0.06"),
    (F5, r"80% prediction intervals cover 87%", "80% intervals cover 87%"),
    (F5, r"Robust at 450 / 1,500 minutes", "robust at 450 minutes"),
    (F4, r"3\.6 standard deviations above the role average; the best in Serie A's role pool in 2025/26 are Baturina 1\.9", "Bruno 3.6 SD vs 1.9"),
    (F4, r"robust Serie A matches are Samardžić, Dybala and Chukwueze", "Bruno's Serie A matches"),
    (F4, r"Nine-metric profile", "nine-metric profile"),
]
for src, pat, what in GUARDS:
    text = src if isinstance(src, str) else flat(src)
    if not re.search(pat, text):
        fail(f"the research no longer says {what} (/{pat}/) — re-check the memo against the findings")


def table(name):
    with open(T5 / name, newline="") as f:
        return list(csv.DictReader(f))


DEST = {r["destination_league"]: r for r in table("m7_destination.csv")}
M6 = {r["model"]: r for r in table("m6_eval.csv")}
M5P = {r["model"]: r for r in table("m5_paired.csv") if r["vs"] == "Model A: own history"}   # Model B also has a row vs naive
M5 = {r["model"]: r for r in table("m5_eval.csv")}
OV = table("m7_overall.csv")[0]
if round(float(M5P['Model B: comparables only']['MAE difference']), 3) != 0.019 or round(float(OV["vs_stay"]) * 100) != 97 or round(float(M6["Model A"]["MAE"]), 3) != 0.096:
    fail("Study 5 tables disagree with the findings — re-export before building")


def pct(x):
    return f"{round(float(x) * 100)}%"


# ---------- charts (plain HTML/CSS, print-safe; values read from the tables) ----------

def league_chart():
    lo_ax, hi_ax = 0.6, 1.4
    pos = lambda v: (float(v) - lo_ax) / (hi_ax - lo_ax) * 100
    rows = []
    for k in ("EPL", "Serie_A", "La_Liga", "Ligue_1", "Bundesliga"):
        r = DEST[k]
        v, lo, hi = float(r["vs_stay"]), float(r["vs_lo"]), float(r["vs_hi"])
        a, b = sorted((pos(1.0), pos(v)))
        tone = "neg" if hi < 1 else ("pos" if lo > 1 else "mid")
        rows.append(
            f'<div class="mc-row" role="listitem"><span class="mc-k">{NAME[k]}<small>{r["n"]} moves</small></span>'
            f'<span class="mc-t"><span class="mc-bar mc-bar--{tone}" style="left:{a:.2f}%;width:{b - a:.2f}%"></span>'
            f'<span class="mc-ci" style="left:{pos(lo):.2f}%;width:{pos(hi) - pos(lo):.2f}%"></span></span>'
            f'<b class="mc-v">{pct(v)}<small>{pct(lo)}–{pct(hi)}</small></b></div>')
    ticks = "".join(f'<i style="left:{pos(t):.2f}%">{round(t * 100)}%</i>' for t in (0.6, 0.8, 1.0, 1.2, 1.4))
    return f"""<figure class="mfig">
  <figcaption><p class="mfig__t">Output kept after a move, by destination league</p>
  <p class="mfig__s">xG + xA per 90 after the move vs comparable players who stayed · bar from 100% · line = 95% CI · {OV['n']} summer moves</p></figcaption>
  <div class="mc" role="list" aria-label="Output kept by destination league">{''.join(rows)}
  <div class="mc-ax" aria-hidden="true"><span></span><span class="mc-ticks">{ticks}<b class="mc-100" style="left:{pos(1.0):.2f}%"></b></span><span></span></div></div>
</figure>"""


def ladder_chart():
    spec = [("naive", "He'll do what he did before", "post = pre"),
            ("shrinkage", "Pull toward the role average", "shrinkage by role"),
            ("M3 context", "Context", "+ age, minutes, both clubs' strength, both leagues"),
            ("Model A", "Context + the player's 3-season history", "Model A")]
    mx = 0.14
    rows = []
    for k, lab, sub in spec:
        r = M6[k]
        mae, r2 = float(r["MAE"]), float(r["R²"])
        hero = " mm-row--hero" if k == "Model A" else ""
        rows.append(f'<div class="mm-row{hero}" role="listitem"><span class="mm-k">{esc(lab)}<small>{esc(sub)}</small></span>'
                    f'<span class="mm-t"><span class="mm-bar" style="width:{mae / mx * 100:.2f}%"></span></span>'
                    f'<b class="mm-v">{mae:.3f}<small>R² {r2:.2f}</small></b></div>')
    return f"""<figure class="mfig">
  <figcaption><p class="mfig__t">Forecast error on the locked test</p>
  <p class="mfig__s">Mean absolute error, xG + xA per 90 after the move · lower is better · {M6['Model A']['n']} unseen transfers, 2023/24–2025/26 · each model fixed before the test was opened</p></figcaption>
  <div class="mm" role="list" aria-label="Mean absolute error by model">{''.join(rows)}</div>
</figure>"""


def sim_chart():
    spec = [("A + comparable output", "+ the comparables' output in the new league"),
            ("A + match quality + distinctiveness", "+ match quality and profile distinctiveness"),
            ("A + past-mover retention", "+ how similar past movers kept their output"),
            ("A + all similarity", "+ all of it"),
            ("Model B: comparables only", "Comparables instead of the player's history")]
    lo_ax, hi_ax = -0.01, 0.04
    pos = lambda v: (v - lo_ax) / (hi_ax - lo_ax) * 100
    rows = []
    for k, lab in spec:
        r = M5P[k]
        d, lo, hi = float(r["MAE difference"]), float(r["lo"]), float(r["hi"])
        worse = lo > 0
        rows.append(f'<div class="ms-row{" ms-row--worse" if worse else ""}" role="listitem"><span class="ms-k">{esc(lab)}</span>'
                    f'<span class="ms-t"><span class="ms-ci" style="left:{pos(lo):.2f}%;width:{pos(hi) - pos(lo):.2f}%"></span>'
                    f'<span class="ms-dot" style="left:{pos(d):.2f}%"></span></span>'
                    f'<b class="ms-v">{d:+.3f}<small>{lo:+.3f} to {hi:+.3f}</small></b></div>')
    ticks = "".join(f'<i style="left:{pos(t):.2f}%">{t:+.2f}</i>' if t else f'<i style="left:{pos(t):.2f}%">0</i>' for t in (-0.01, 0, 0.01, 0.02, 0.03, 0.04))
    base = float(M5["Model A: own history"]["MAE"])
    return f"""<figure class="mfig">
  <figcaption><p class="mfig__t">What Study 4 similarity adds to the player's own history</p>
  <p class="mfig__s">Change in forecast error vs the history model (MAE {base:.3f}) · right of 0 = worse · line = 95% CI · {M5['naive']['n']} leak-free rolling forecasts, 2019/20–2022/23</p></figcaption>
  <div class="ms" role="list" aria-label="Change in forecast error when adding similarity">{''.join(rows)}
  <div class="ms-ax" aria-hidden="true"><span></span><span class="mc-ticks">{ticks}<b class="mc-100" style="left:{pos(0):.2f}%"></b></span><span></span></div></div>
</figure>"""


# ---------- page ----------

def build(slug, pdf=False):
    C = json.loads((SITE / f"content/memos/{slug}.json").read_text())
    path = f"/football/research/{slug}"
    out = FB / f"research/{slug}.html"
    club = esc(C["club"])
    li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
    tdl = lambda xs: "".join(f'<div><dt>{esc(x["t"])}</dt><dd>{esc(x["d"])}</dd></div>' for x in xs)
    ld = {"@context": "https://schema.org", "@type": "Report", "name": C["title"], "alternativeHeadline": C["subtitle"],
          "author": {"@type": "Person", "name": "Ayush Pawar", "url": "https://iyush.dev"}, "datePublished": C["date"], "url": fb_chrome.SITE + path}
    desc = f"{C['subtitle']}. A research memo on cross-league transfers from ten seasons of top-five-league event data, prepared for {C['club']}."
    head = fb_chrome.head(path, f"{C['title']} · Research memo · Ayush Pawar", desc, C["title"], "transferability.png", ld)
    head = head.replace('content="index, follow, max-image-preview:large"', 'content="noindex, nofollow"')
    head = head.replace('<link rel="stylesheet" href="/football/football.css" />',
                        '<link rel="stylesheet" href="/football/football.css" />\n<link rel="stylesheet" href="/football/memo.css" />')

    epl = DEST["EPL"]
    body = f"""<body class="memo-page">
{fb_chrome.header(path)}

<main id="main" class="memo">
<article class="wrap memo__doc">

<header class="mcover">
  <p class="mk">Football research · Memo</p>
  <h1>{esc(C['title'])}</h1>
  <p class="mcover__sub">{esc(C['subtitle'])}</p>
  <dl class="mcover__meta">
    <div><dt>Prepared for</dt><dd>{esc(C['recipient'])}<small>{esc(C['recipient_role'])}</small></dd></div>
    <div><dt>By</dt><dd>Ayush Pawar<small>{esc(C['date_label'])} · interactive version: iyush.dev{path}</small></dd></div>
  </dl>
  <blockquote class="mpull"><p>{esc(C['pull'][0])}<br>{esc(C['pull'][1])}</p></blockquote>
  <p class="mcover__note">Independent research from public event data, written for {club} because I think the question is relevant to its work. It was not commissioned by the club and uses none of its data.</p>
</header>

<section class="msec" aria-labelledby="s1"><p class="mnum">01</p><div>
  <h2 id="s1">The recruitment problem</h2>
  <p>A forward produces 0.65 xG + xA per 90 in league A. What should a recruitment department expect from him in league B?</p>
  <p>A player's numbers don't belong entirely to the player. League difficulty, the strength of the club around him, his age and the shape of his recent seasons all leave a mark. There are three obvious ways to make the forecast:</p>
  <ol class="mthree"><li><b>Trust his previous output.</b></li><li><b>Adjust for the destination:</b> the league and the club.</li><li><b>Find similar players</b> and look at what they did.</li></ol>
  <p>I tested all three on transfers the model had never seen.</p>
  <div class="mwhy"><p class="mk">Why {club}</p>{''.join(f'<p>{esc(p)}</p>' for p in C['why'])}<p class="msrc">{esc(C['why_source'])}</p></div>
</div></section>

<section class="msec" aria-labelledby="s2"><p class="mnum">02</p><div>
  <h2 id="s2">The data</h2>
  <ul class="mstats">
    <li><b>10</b><span>seasons, 2015/16–2024/25</span></li><li><b>5</b><span>leagues: EPL, La Liga, Serie A, Bundesliga, Ligue 1</span></li>
    <li><b>18,011</b><span>matches</span></li><li><b>8,348</b><span>players</span></li><li><b>525,328</b><span>player-matches</span></li>
    <li><b>2,917</b><span>cross-league moves, inferred from club spells</span></li><li><b>{OV['n']}</b><span>in the primary transfer sample</span></li>
  </ul>
  <p>The primary sample is every summer move between two of the five leagues by a forward or midfielder with at least 900 minutes before and after it, with destination seasons from 2016/17 to 2025/26. <b>Retention</b> is output after the move against what comparable players who stayed at their club produced the next season: same role, same pre-move output, same age. That strips out regression to the mean and normal ageing.</p>
  <p class="mnote">This is public, match-level event data: shots, xG and xA from Understat, plus club and league context. It has no defensive actions, possession, passes, carries, tracking, physical data, injuries, contracts or fees. Every forecast below is about attacking output only.</p>
</div></section>

<section class="msec" aria-labelledby="s3"><p class="mnum">03</p><div>
  <h2 id="s3">A move doesn't automatically destroy a player's output</h2>
  <p>Across all {OV['n']} moves, players kept <b>{pct(OV['vs_stay'])}</b> of their xG + xA per 90 against comparable stayers (95% CI {pct(OV['vs_lo'])}–{pct(OV['vs_hi'])}). There is no universal &ldquo;league-change penalty&rdquo;. The direction is what matters:</p>
  {league_chart()}
  <p>One ladder of league difficulty explains all 20 directions: Premier League hardest, Serie A and La Liga in the middle, the Bundesliga and Ligue 1 easiest. Pair-specific effects add nothing (F-test p = 0.91). Moving into the Premier League keeps {pct(epl['vs_stay'])}; the same player moving the other way would be expected to gain.</p>
</div></section>

<section class="msec" aria-labelledby="s4"><p class="mnum">04</p><div>
  <h2 id="s4">The league isn't everything</h2>
  <p>Within that ladder, three things about the player and the destination club matter about as much as the league itself.</p>
  <div class="mcards">
    <div class="mcard"><p class="mk">Destination club</p><p class="mcard__n">79% <i>→</i> 106%</p><p>Weakest third of destination clubs vs strongest third. A step up in club strength keeps 114%; a step down, 81%.</p></div>
    <div class="mcard"><p class="mk">Age</p><p class="mcard__n">−2%</p><p>Retention per extra year of age, beyond normal ageing (95% CI −3.2% to −0.8%).</p></div>
    <div class="mcard"><p class="mk">A recent jump</p><p class="mcard__n">−9%</p><p>Per standard deviation of last-season improvement. Players arriving off a spike come down further.</p></div>
  </div>
  <p class="mbig">The destination isn't a league. It's a league, a club and a player's trajectory.</p>
</div></section>

<section class="msec" aria-labelledby="s5"><p class="mnum">05</p><div>
  <h2 id="s5">The obvious next idea: find players like him</h2>
  <p>If output changes in a new environment, perhaps we should look at players who play like the one we're buying. That was Study 4: a cross-league similarity engine on nine context-adjusted metrics, z-scored within role, compared by cosine similarity.</p>
  <p>It finds sensible candidates. Searching Serie A for Bruno Fernandes returns Samardžić, Dybala and Chukwueze as the matches that survive every specification. It also shows the limit of similarity: Bruno's chance creation sits <b>3.6 standard deviations</b> above his role average; the best in Serie A's pool is <b>1.9</b>. The matches share his shape, not his level.</p>
  <p class="mbig">Similarity can find candidates. Does it help predict them?</p>
</div></section>

<section class="msec msec--hero" aria-labelledby="s6"><p class="mnum">06</p><div>
  <h2 id="s6">The experiment</h2>
  <p>Two tests, both leak-free: every feature is frozen at the summer of the move and each model only sees earlier moves.</p>
  <h3>Test 1 · How much does context and history buy?</h3>
  <p>Four models, specified on 286 earlier moves and then scored once on {M6['Model A']['n']} transfers from 2023/24–2025/26 that had been locked away.</p>
  {ladder_chart()}
  <p>Context and the player's own three-season history cut the error by a quarter against &ldquo;he'll do what he did before&rdquo; (0.129 → 0.096; difference −0.033, 95% CI −0.049 to −0.018). It also ranks well: AUC 0.80 for keeping at least 75% of output.</p>
  <h3>Test 2 · Does similarity add anything?</h3>
  <p>The same history model, plus Study 4's similarity features: what the most similar players produce in the destination league, how good the match is, how distinctive the player is, and how similar past movers fared.</p>
  {sim_chart()}
  <p class="mbig mbig--red">Adding the comparables changes the error by 0.000.</p>
  <p>The comparables' output is almost a restatement of the player's own level (r = 0.89), and carries nothing the history model doesn't already know. Using comparables <i>instead of</i> the player's history is worse, and no better than assuming nothing changes.</p>
</div></section>

<section class="msec mconc" aria-labelledby="s7"><p class="mnum">07</p><div>
  <h2 id="s7" class="sr-only">Conclusion</h2>
  <p class="mconc__l">Similarity finds candidates.</p>
  <p class="mconc__l mconc__l--r">Player history predicts performance.</p>
  <p>I built the similarity engine expecting it to improve transfer forecasts, then tested whether it did. It didn't. Its job is discovery: shortlisting, and covering roles whose value the data can't see. The forecast should come from the player's own history in context.</p>
</div></section>

<section class="msec" aria-labelledby="s8"><p class="mnum">08</p><div>
  <h2 id="s8">What this model cannot answer for {club}</h2>
  <dl class="mlimits">{tdl(C['limits_club'])}
    <div><dt>Retention is conditional on playing.</dt><dd>27% of league movers don't reach 900 minutes in the new league (stayers: 20%). The model says what a player produces if he plays, not whether he will.</dd></div>
    <div><dt>It sees attacking output only.</dt><dd>No defensive actions, possession, passes, carries, pressing or physical data. Goalkeepers and defenders are out of scope.</dd></div>
    <div><dt>Individual forecasts are wide.</dt><dd>A typical 80% interval is about ±0.2 xG + xA per 90. It covers 87% of outcomes on the locked test, so it's honest but conservative. This is a filter, not a decision.</dd></div>
  </dl>
</div></section>

<section class="msec" aria-labelledby="s9"><p class="mnum">09</p><div>
  <h2 id="s9">If I had club data</h2>
  <p>The structure of the test (a forecast fixed before the outcome, scored on locked seasons, compared against naive baselines) carries over. What would change is what goes into it.</p>
  <ol class="mlayers">
    <li><b>Event data</b><span>Replace xG + xA with an action-value target, so build-up, progression and defending count, not just the last two actions of a chance.</span></li>
    <li><b>Tactical context</b><span>Possession share, team style, role and zones occupied, pressing context, how much chance creation the team gives the player.</span></li>
    <li><b>Tracking</b><span>Does off-ball behaviour travel: runs, spacing, pressing intensity? It may travel better than output does.</span></li>
    <li><b>Physical</b><span>Sprints, high-speed running, accelerations, availability, against the demands of the destination league.</span></li>
    <li><b>Video</b><span>&ldquo;{esc(C['video_quote'])}&rdquo; The model should point the scout at the clips where it is least sure, and the scout's verdict should be logged so the model can be evaluated against it.</span></li>
  </ol>
</div></section>

<section class="msec" aria-labelledby="s10"><p class="mnum">10</p><div>
  <h2 id="s10">Where it fits in a recruitment workflow</h2>
  <p>I build software products for a living, so I think about this as a sequence of decisions, each with a question the data can or cannot answer.</p>
  <ol class="mflow">
    <li><b>Profile</b><span>How good is he once context is adjusted for?</span></li>
    <li><b>Similarity</b><span>Who plays like him? Discovery, not forecasting.</span></li>
    <li><b>Transferability</b><span>What should we expect at our club, in our league?</span></li>
    <li><b>Uncertainty</b><span>How wide is the range? How much history is it built on?</span></li>
    <li><b>Blind spots</b><span>What can't this data see for this role?</span></li>
    <li><b>Video</b><span>Which clips would settle the uncertainty?</span></li>
    <li class="mflow__end"><b>Decision</b><span>Does he deserve a deeper look?</span></li>
  </ol>
</div></section>

<section class="msec" aria-labelledby="s11"><p class="mnum">11</p><div>
  <h2 id="s11">What I got wrong</h2>
  <dl class="mwrong">
    <div><dt>Similarity</dt><dd>I expected comparable players to improve transfer forecasts. They didn't, and comparables alone were worse than the player's own history.</dd></div>
    <div><dt>Ugarte</dt><dd>For Manchester United in 2024 the model predicted 0.02 xG + xA per 90 (80% range 0.01–0.05); he produced 0.14. Two causes, both named before the outcome: a fixed Premier League penalty over-punishes low-output midfielders (about 0.06 too low on the locked test), and ball-winning, which is why he was bought, is invisible to this data.</dd></div>
    <div><dt>Low-minute players</dt><dd>The model needs 900 minutes. It doesn't address one of the most interesting recruitment problems: judging a player before a conventional sample exists.</dd></div>
  </dl>
</div></section>

<section class="msec mnext" aria-labelledby="s12"><p class="mnum">12</p><div>
  <h2 id="s12">The next question</h2>
  <p class="mbig">{esc(C['next']['q'])}</p>
  <ol class="mnext__l">{li(esc(s) for s in C['next']['steps'])}</ol>
</div></section>

<footer class="mfoot">
  <p class="mprint"><b>Full studies, tools and this memo online:</b> iyush.dev{path}</p>
  <p class="mscreen"><b>Full research:</b> <a href="/football/research/transferability">Study 05 · Transferability</a> · <a href="/football/research/similarity">Study 04 · Similarity</a> · <a href="/football/case-studies/manchester-united-2024">Manchester United 2024 case study</a> · <a href="/football/methodology">Methodology</a> · <a href="/football/tools/transfer">Transfer Calculator</a></p>
  <p>Data: Understat event data for the top five European leagues; ages from the CC0 Transfermarkt-derived dataset (dcaribou/transfermarkt-datasets). Transfers are inferred from consecutive club spells, not recorded. Observational data: effects are associations within matched comparisons.</p>
  <p>Ayush Pawar · i.yush.004@gmail.com · iyush.dev/football</p>
</footer>

</article>
</main>

{fb_chrome.footer(C['date_label'])}
</body>
</html>
"""
    out.write_text(head + "\n" + body)
    print(f"wrote {out.relative_to(SITE)}")
    if pdf:
        render_pdf(slug, out)


def render_pdf(slug, page):
    dest = SITE / f"docs/outreach/{slug}/{slug}-memo.pdf"
    dest.parent.mkdir(parents=True, exist_ok=True)
    # needs a local server on MEMO_BASE and playwright-core on NODE_PATH (see scripts/memo_pdf.cjs)
    subprocess.run(["node", str(SITE / "scripts/memo_pdf.cjs"), f"/football/research/{slug}", str(dest)], check=True)
    print(f"wrote {dest.relative_to(SITE)}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        fail("usage: build_memo.py <slug> [--pdf]")
    build(args[0], pdf="--pdf" in sys.argv)
