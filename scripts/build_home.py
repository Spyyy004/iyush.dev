#!/usr/bin/env python3
"""Render the static research figures + tool-teaser results on /football (M1 §12, §15, §16, §29).

The homepage ships no datasets and runs no model in the browser: every number in these
fragments is read from football/data/*.json (the validated research outputs) at build time.
Re-run after football_export.py:   python3 scripts/build_home.py

Each fragment replaces the region between <!-- gen:NAME --> and <!-- /gen:NAME --> in
football/index.html. Study 1 has no frozen export yet, so its weather bound (±2%, five-league run of 6 Oct 2026) is
taken from findings/study1_environmental_conditions.md in the research project, flagged pending on the page.
"""
import html, json, math, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FB = ROOT / "football"
R = json.loads((FB / "data/research.json").read_text())
META = json.loads((FB / "data/meta.json").read_text())
esc = html.escape


def pct(x, lo, hi):
    return f"{(x - lo) / (hi - lo) * 100:.2f}%"


def ticks(items):
    return '<div class="ticks">' + "".join(f'<span style="left:{p}">{esc(t)}</span>' for t, p in items) + "</div>"


def axis_row(tk):
    return f'<div class="hbar__axis" aria-hidden="true"><span></span>{ticks(tk)}<span></span></div>'


def figure(title, sub, plot, words, source, label):
    return (f'<figure class="chart fig">\n'
            f'  <figcaption><p class="chart__title">{title}</p><p class="chart__sub">{sub}</p></figcaption>\n'
            f'  <div class="chart__plot" role="img" aria-label="{esc(label)}">{plot}</div>\n'
            f'  <p class="chart__summary">{words}</p>\n'
            f'  <p class="source">{source}</p>\n'
            f'</figure>')


# ---------- 01 Environment: weather bound next to home advantage, for scale ----------
def fig_s1():
    home = next(r for r in R["s2_primary"] if r["metric"] == "xg")["full"]
    hv = (home - 1) * 100
    lo, hi = -10, 30
    x = lambda v: pct(v, lo, hi)
    plot = ('<div class="hbar">'
            f'<div class="hbar__row"><span class="hbar__lbl">Rain, humidity</span>'
            f'<span class="track"><span class="zero" style="left:{x(0)}"></span><span class="band" style="left:{x(-2)};width:{pct(4 + lo, lo, hi)}"></span></span>'
            f'<span class="hbar__v">±2%</span></div>'
            f'<div class="hbar__row"><span class="hbar__lbl"><b>Playing at home</b></span>'
            f'<span class="track"><span class="zero" style="left:{x(0)}"></span><span class="bar bar--hot" style="left:{x(0)};width:{pct(hv + lo, lo, hi)}"></span></span>'
            f'<span class="hbar__v hbar__v--hot">+{hv:.1f}%</span></div>'
            '</div>' + axis_row([("−10%", "0%"), ("0", x(0)), ("+10%", x(10)), ("+20%", x(20)), ("+30%", x(30))]))
    return figure("Weather, next to home advantage",
                  "Change in a player’s xG. The shaded band is the largest weather effect the data still allows.",
                  plot,
                  f"On all five leagues, rain and humidity move output by about ±2% at most (wind about −1%). Playing at home lifts the same player’s xG by {hv:.1f}%.",
                  "Study 01 (five-league run, 6 Oct 2026; final conclusion pending) · Study 02",
                  f"Rain and humidity: within plus or minus 2 percent. Playing at home: plus {hv:.1f} percent.")


# ---------- 02 Home advantage: individual home edges, raw vs after shrinkage ----------
def fig_s2():
    h = R["s2_hist"]
    edges, raw, shr = h["edges"], h["raw"], h["shrunk"]
    def bars(c):
        m = max(c)
        return "".join(f'<i style="height:{v / m * 100:.1f}%"></i>' for v in c)
    i20 = edges.index(0.2)
    core = shr[i20] + shr[i20 + 1]
    lo, hi = edges[0], edges[-1]
    # edges are log(home ÷ away) units; label the axis in true % changes
    band = f"{(math.exp(edges[i20]) - 1) * 100:+.0f}% and {(math.exp(edges[i20 + 2]) - 1) * 100:+.0f}%"
    tk = ticks([(t, pct(math.log(r), lo, hi)) for t, r in (("−75%", 0.25), ("−50%", 0.5), ("0", 1), ("+100%", 2), ("+300%", 4))])
    plot = ('<div class="hist">'
            f'<div class="hist__row"><p class="label"><span>As measured</span><span>spread (SD, log scale) {h["raw_sd"]:.2f}</span></p><div class="hist__bars">{bars(raw)}</div></div>'
            f'<div class="hist__row hist__row--hot"><p class="label"><span>After removing noise</span><span>spread (SD, log scale) {h["shrunk_sd"]:.2f}</span></p><div class="hist__bars">{bars(shr)}</div>{tk}</div>'
            '</div>')
    n = h["n"]
    return figure("Each player’s personal home edge",
                  f"{n:,} players in this export (the reliability test reports 4,665), xG at home vs away. Log scale; each row is scaled to its own peak; the outer bars collect everything below −86% or above +639%.",
                  plot,
                  f"Measured naively, players’ home edges look wildly different. Once match-to-match noise is removed, {core:,} of {n:,} land between {band}.",
                  "Study 02 · empirical-Bayes shrinkage",
                  f"Histogram of {n} players' home edges. Raw estimates spread widely; after shrinkage {core} of {n} sit between {band}.")


# ---------- 03 Opposition: xG per 90 by opponent-strength decile ----------
def fig_s3():
    d = sorted((r for r in R["s3_deciles"] if r["metric"] == "xg"), key=lambda r: r["d"])
    top = 0.2
    cols = []
    for r in d:
        cls = ' class="end"' if r["d"] in (1, 10) else ""
        lab = f'<b>{r["v"]:.2f}</b>' if r["d"] in (1, 10) else ""
        cols.append(f'<span{cls} style="height:{r["v"] / top * 100:.1f}%">{lab}</span>')
    plot = f'<div class="cols">{"".join(cols)}</div><div class="cols__x"><span>Weakest opponents</span><span>Strongest</span></div>'
    a, b = d[0]["v"], d[-1]["v"]
    return figure("xG per 90, by opponent strength",
                  "All players. Opponents split into ten equal groups by pre-match strength rating.",
                  plot,
                  f"xG per 90 falls from {a:.2f} against the weakest tenth of opponents to {b:.2f} against the strongest — and by about the same share for everyone.",
                  "Study 03 · sequential market rating from pre-match odds",
                  f"Bar chart: xG per 90 declines steadily from {a:.2f} against the weakest opponents to {b:.2f} against the strongest.")


# ---------- 04 Similarity: Bruno's chance creation against Serie A's role pool ----------
def fig_s4():
    cr = R["s4"]["creators"]
    bruno = 3.6  # Study 4 case study (Final Summary); matches the Study 4 page
    best = cr[0]
    x = lambda v: pct(v, 0, 4)
    dots = "".join(f'<span class="d" style="left:{x(c["chance creation (z)"])}"></span>' for c in cr)
    plot = (f'<div class="dotstrip"><span class="axis"></span>{dots}'
            f'<span class="d d--hot" style="left:{x(bruno)}"></span>'
            f'<span class="tag tag--hot tag--r" style="left:calc({x(bruno)} + 7px)">Bruno {bruno}</span>'
            f'<span class="tag tag--below" style="left:{x(best["chance creation (z)"])}">Best in Serie A {best["chance creation (z)"]:.1f}</span></div>'
            + ticks([("0", "0%"), ("1", x(1)), ("2", x(2)), ("3", x(3)), ("4 SD", "100%")]))
    return figure("Chance creation, above role average",
                  f"Bruno Fernandes (Premier League) against Serie A’s top {len(cr)} attacking midfielders and wide forwards. In standard deviations.",
                  plot,
                  f"Bruno sits {bruno} SD above his role average. The best in Serie A’s pool, {esc(best['player'])}, is at {best['chance creation (z)']:.1f}. His closest statistical matches all create less.",
                  "Study 04 · Bruno case study, profiles to 2025/26",
                  f"Dot strip: Bruno at {bruno} standard deviations; Serie A's best at {best['chance creation (z)']:.1f}; the rest of the pool lower.")


# ---------- 05 Transferability: prediction error, history vs similarity ----------
def fig_s5():
    ev = {r["model"]: r for r in R["s5"]["sim_eval"]}
    rows = [("“He’ll do what he did”", "naive", False),
            ("Similar players only", "Model B: comparables only", False),
            ("<b>Own history</b>", "Model A: own history", True),
            ("Own history + similar players", "A + comparable output", False)]
    top = 0.14
    n = ev["naive"]["n"]
    out = []
    for lab, key, hot in rows:
        v = ev[key]["MAE"]
        out.append(f'<div class="hbar__row"><span class="hbar__lbl">{lab}</span>'
                   f'<span class="track"><span class="bar{" bar--hot" if hot else ""}" style="width:{pct(v, 0, top)}"></span></span>'
                   f'<span class="hbar__v{" hbar__v--hot" if hot else ""}">{v:.4f}</span></div>')   # 4 dp: 0.1095 vs 0.1091
    plot = '<div class="hbar">' + "".join(out) + "</div>" + axis_row([("0", "0%"), ("0.04", pct(.04, 0, top)), ("0.08", pct(.08, 0, top)), ("0.12", pct(.12, 0, top))])
    a, nv = ev["Model A: own history"]["MAE"], ev["naive"]["MAE"]
    plus = ev["A + comparable output"]["MAE"] - a
    return figure(f"Prediction error on {n} league moves",
                  "Mean absolute error in xG + xA per 90, first season after the move. Lower is better.",
                  plot,
                  f"Similar players alone barely beat the naive guess. The player’s own history cuts the error by {round((1 - a / nv) * 100)}%; adding similarity on top moves it by less than 0.001.",
                  "Study 05 · comparison on transfers with Study 4 profiles",
                  f"Bar chart of error: naive {nv:.4f}, similar players only {ev['Model B: comparables only']['MAE']:.4f}, own history {a:.4f}, own history plus similar players {a + plus:.4f}.")


# ---------- Similarity teaser: Study 4 case-study top 3 ----------
NAMES = {"Lazar Samardzic": "Lazar Samardžić"}
def sim_rows():
    out = []
    for r in R["s4"]["bruno"][:3]:
        sc = r["median_score"]
        out.append(f'<li><span class="r">0{r["rank"]}</span><span class="n">{esc(NAMES.get(r["player"], r["player"]))}<small>{esc(r["team"])}</small></span>'
                   f'<span class="track" aria-hidden="true"><span class="bar" style="width:{sc:.1f}%;background:var(--muted-decor)"></span></span>'
                   f'<span class="v">{sc:.0f}</span></li>')
    return "\n".join(out)


# ---------- Transfer teaser: one precomputed run of the Study 5 model ----------
def transfer():
    """Homepage example: Bruno Fernandes → Inter, read from the Transfer Calculator's precomputed Study 5 results."""
    ix = json.loads((FB / "data/transfer/index.json").read_text())
    key = next(p[0] for p in ix["players"] if p[5] == "bruno-fernandes")
    ci = next(i for i, c in enumerate(ix["clubs"]) if c[0] == "Serie_A" and c[1] == "Inter")
    d = json.loads((FB / f"data/transfer/p/{key}.json").read_text())
    pred, q10, q90, p75 = d["pred"][str(ci)]
    r = {"pred": pred, "q10": q10, "q90": q90, "p75": p75, "retention": pred / d["pre"]}
    p = {"pre": d["pre"]}
    o = {"pre_season": ix["pre_season"]}
    lo, hi = 0, 1.2
    x = lambda v: pct(v, lo, hi)
    return f'''<div class="kv">
        <div><span class="label">Expected output</span><b>{r["pred"]:.2f}</b><i>xG + xA / 90 · last season {p["pre"]:.2f}</i></div>
        <div><span class="label">Retention</span><b class="hot">{r["retention"] * 100:.0f}%</b><i>of last season’s output</i></div>
        <div><span class="label">Chance of ≥75%</span><b>{r["p75"] * 100:.0f}%</b><i>keeps at least three-quarters</i></div>
      </div>
      <div class="range" role="img" aria-label="80% prediction range {r["q10"]:.2f} to {r["q90"]:.2f}; prediction {r["pred"]:.2f}; last season {p["pre"]:.2f}">
        <p class="label" style="margin:0 0 6px">80% prediction range · {r["q10"]:.2f} – {r["q90"]:.2f}</p>
        <div class="range__track"><span class="range__axis"></span><span class="range__band" style="left:{x(r["q10"])};width:calc({x(r["q90"])} - {x(r["q10"])})"></span><span class="range__pt" style="left:{x(r["pred"])}"></span><span class="range__pre" style="left:{x(p["pre"])}"></span></div>
        <div class="range__lbl"><span>0.00</span><span>0.60</span><span>1.20</span></div>
        <div class="legend"><span><i class="sw" style="--c:var(--accent-text);width:4px"></i>Prediction</span><span><i class="sw" style="--c:var(--accent-wash);border:1px solid var(--accent)"></i>80% range</span><span><i class="sw sw--dash" style="--c:var(--frozen)"></i>Last season</span></div>
      </div>
      <p class="source" style="margin-top:14px">Example run of the Study 5 model · player inputs as of {esc(o["pre_season"])} · attacking output only — it can't see defending, fit or injuries</p>'''


def footer_date():
    from datetime import datetime
    return datetime.fromisoformat(META["tracker_generated_utc"]).strftime("%b %Y")


FRAGS = {"fig-s1": fig_s1, "fig-s2": fig_s2, "fig-s3": fig_s3, "fig-s4": fig_s4, "fig-s5": fig_s5,
         "sim-rows": sim_rows, "transfer": transfer}

if __name__ == "__main__":
    page = FB / "index.html"
    s = page.read_text()
    for name, fn in FRAGS.items():
        pat = re.compile(rf"(<!-- gen:{name} -->)(.*?)(<!-- /gen:{name} -->)", re.S)
        if not pat.search(s):
            sys.exit(f"marker gen:{name} missing in {page}")
        s = pat.sub(lambda m: m.group(1) + "\n" + fn() + "\n" + m.group(3), s)
    page.write_text(s)
    # footer "Data updated" on every /football page
    d = footer_date()
    for f in FB.rglob("*.html"):
        t = f.read_text()
        t2 = re.sub(r"<p>Data updated: [^<]*</p>", f"<p>Data updated: {d}</p>", t)
        if t2 != t:
            f.write_text(t2)
    print("ok ·", ", ".join(FRAGS), "· data updated", d)
