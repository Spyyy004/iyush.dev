#!/usr/bin/env python3
"""Build /football/research and the five study pages (M2) from content + validated research outputs.

    python3 scripts/build_research.py

One StudyPage system, five studies: every page is rendered from content/research.json by the
same section components, and every chart value is read from football/data/research.json at
build time. Pages ship as static HTML — no dataset is downloaded by the browser (M2 §31).

The build fails if content references an unknown glossary term or chart, or if a study is
missing a framework section (M2 §4).
"""
import html
import json
import math
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FB = ROOT / "football"
C = json.loads((ROOT / "content/research.json").read_text())
R = json.loads((FB / "data/research.json").read_text())
META = json.loads((FB / "data/meta.json").read_text())
GLOSS = set(json.loads(subprocess.check_output(
    ["node", "-e", "global.window={};require(process.argv[1]);console.log(JSON.stringify(Object.keys(window.FB_GLOSSARY)))",
     str(FB / "js/glossary.js")], text=True)))
STUDIES = C["studies"]
BY_SLUG = {s["slug"]: s for s in STUDIES}
esc = html.escape
LEAGUE = {"EPL": "Premier League", "La_Liga": "La Liga", "Serie_A": "Serie A", "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1"}
METRIC = {"xg": "xG", "xa": "xA", "shots": "Shots", "key_passes": "Key passes", "goals": "Goals"}
FRAMEWORK = ["Question", "Why it matters", "What we did", "What we found", "What surprised us", "What it means", "Limitations", "Next question"]


def fail(msg):
    sys.exit("build_research: " + msg)


# ---------- inline markup: {term|label} **bold** *italic* ----------
def md(text):
    out = esc(text, quote=False)

    def term(m):
        key, label = m.group(1), m.group(2)
        if key not in GLOSS:
            fail(f"unknown glossary term '{key}' in: {text[:60]}")
        return f'<button type="button" class="term" data-term="{key}">{label}</button>'
    out = re.sub(r"\{([a-z0-9-]+)\|([^}]+)\}", term, out)
    out = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", out)
    return out


def pct(v, lo, hi):
    return f"{(v - lo) / (hi - lo) * 100:.2f}%"


def signed(x, d=1):
    s = f"{abs(x):.{d}f}"
    return ("+" if x > 0 else "−" if x < 0 else "") + s


# ============================================================ charts (ResearchChart family)
def figure(spec, plot, label, after=""):
    """ChartContainer: what you're looking at → plot → in words → source. `after` holds real, accessible content (e.g. a
    data table) that must not sit inside the role=img plot."""
    return (f'<figure class="chart fig" data-reveal>\n'
            f'  <figcaption><p class="chart__title">{esc(spec["title"])}</p>'
            + (f'<p class="chart__sub">{md(spec["sub"])}</p>' if spec.get("sub") else "") + '</figcaption>\n'
            f'  <div class="chart__plot" role="img" aria-label="{esc(label)}">{plot}</div>\n{after}'
            f'  <p class="chart__summary">{md(spec["words"])}</p>\n'
            f'  <p class="source">{esc(spec["source"])}</p>\n'
            f'</figure>')


def ticks_html(lo, hi, ticks, fmt):
    return ('<div class="hbar__axis" aria-hidden="true"><span></span><div class="ticks">'
            + "".join(f'<span style="left:{pct(t, lo, hi)}">{esc(fmt(t))}</span>' for t in ticks)
            + "</div><span></span></div>")


def hbar(rows, lo, hi, ticks, tick_fmt, ref=None):
    """EffectChart / ComparisonChart rows on one axis.
    row: label, v, txt, and optionally lo/hi (interval), b (second marker), kind ('bar'|'dot'|'band'|'pair'), hot."""
    x = lambda v: pct(v, lo, hi)
    zero = ref if ref is not None else (0 if lo <= 0 <= hi else None)
    out = []
    for r in rows:
        kind, hot = r.get("kind", "bar"), r.get("hot")
        parts = []
        if zero is not None:
            parts.append(f'<span class="zero" style="left:{x(zero)}"></span>')
        if kind == "band":
            parts.append(f'<span class="band" style="left:{x(r["lo"])};width:calc({x(r["hi"])} - {x(r["lo"])})"></span>')
        if kind == "bar":
            a, b = sorted((zero if zero is not None else lo, r["v"]))
            origin = "right" if r["v"] < (zero or 0) else "left"
            parts.append(f'<span class="bar grow-x{" bar--hot" if hot else ""}" style="left:{x(a)};width:calc({x(b)} - {x(a)});transform-origin:{origin}"></span>')
        if r.get("lo") is not None and kind in ("bar", "dot"):
            parts.append(f'<span class="ci" style="left:{x(r["lo"])};width:calc({x(r["hi"])} - {x(r["lo"])})"></span>')
        if kind == "pair":
            a, b = sorted((r["v"], r["b"]))
            parts.append(f'<span class="gap" style="left:{x(a)};width:calc({x(b)} - {x(a)})"></span>')
            parts.append(f'<span class="mk mk--b" style="left:{x(r["b"])}"></span>')
            parts.append(f'<span class="mk mk--a{" mk--hot" if hot is not False else ""}" style="left:{x(r["v"])}"></span>')
        if kind == "dot":
            parts.append(f'<span class="mk mk--a mk--hot" style="left:{x(r["v"])}"></span>')
        lab = r["label"]
        out.append(f'<div class="hbar__row"><span class="hbar__lbl">{lab if r.get("raw_label") else esc(lab)}</span>'
                   f'<span class="track">{"".join(parts)}</span>'
                   f'<span class="hbar__v{" hbar__v--hot" if hot else ""}">{r["txt"]}</span></div>')
    w = max(len(re.sub("<[^>]+>", "", r["txt"])) for r in rows)
    return f'<div class="hchart" style="--vw:{max(w * 0.62 + 0.4, 4.2):.1f}em">' + '<div class="hbar">' + "".join(out) + "</div>" + ticks_html(lo, hi, ticks, tick_fmt) + "</div>"


def legend(items):
    return '<div class="legend">' + "".join(f'<span><i class="sw {cls}"></i>{esc(t)}</span>' for cls, t in items) + "</div>"


PAIR_LEGEND = lambda a, b: legend([("sw--dot", a), ("sw--ring", b)])


def cols(rows, top, fmt=lambda v: f"{v}", base=0):
    out = []
    for lab, v, cls in rows:
        h = (v - base) / (top - base) * 100
        out.append(f'<span class="{cls} grow-y" style="height:{h:.1f}%"><b>{esc(fmt(v))}</b></span>')
    n = len(rows)
    return (f'<div class="cols" style="grid-template-columns:repeat({n},minmax(0,1fr))">{"".join(out)}</div>'
            f'<div class="cols__lbl" style="grid-template-columns:repeat({n},minmax(0,1fr))">'
            + "".join(f"<span>{esc(lab)}</span>" for lab, _, _ in rows) + "</div>")


# ---------- inline charts (results with no data export; values from the Final Summary) ----------
def inline_chart(spec):
    t = spec["type"]
    if t == "cols":
        plot = cols([(l, v, c) for l, v, c in spec["rows"]], spec["max"], lambda v: f"+{v}{spec.get('unit', '')}")
        label = "; ".join(f"{l}: {v}{spec.get('unit', '')}" for l, v, _ in spec["rows"])
    elif t == "paired":
        lo, hi, f = spec["lo"], spec["hi"], spec.get("fmt", "2")
        rows = [{"label": l, "v": a, "b": b, "kind": "pair", "txt": f"{a:.{f}f} → {b:.{f}f}"} for l, a, b in spec["rows"]]
        ticks = spec.get("ticks") or [lo, spec.get("ref", (lo + hi) / 2), round(hi - (hi - lo) % 0.2, 1)]
        plot = hbar(rows, lo, hi, ticks, lambda v: f"{v:.1f}", ref=spec.get("ref")) + PAIR_LEGEND(spec["a"], spec["b"])
        label = "; ".join(f"{l}: {a} with fans, {b} behind closed doors" for l, a, b in spec["rows"])
    elif t == "scale":
        lo, hi = spec["lo"], spec["hi"]
        rows = []
        for l, kind, a, b, txt in spec["rows"]:
            if kind == "band":
                rows.append({"label": l, "kind": "band", "lo": a, "hi": b, "v": 0, "txt": txt})
            else:
                rows.append({"label": l, "kind": "bar", "v": b, "hot": kind == "hot", "txt": txt})
        plot = hbar(rows, lo, hi, spec["ticks"], lambda v: (signed(v, 0) if v else "0") + "%")
        label = "; ".join(f"{r[0]}: {r[4]}" for r in spec["rows"])
    else:
        fail(f"unknown inline chart type {t}")
    return figure(spec, plot, label)


# ---------- charts computed from research.json ----------
def ch_s2_effects():
    rows = [r for r in R["s2_primary"] if r["metric"] in METRIC]
    rows = [{"label": METRIC[r["metric"]], "v": (r["full"] - 1) * 100, "lo": (r["full_lo"] - 1) * 100, "hi": (r["full_hi"] - 1) * 100,
             "hot": r["metric"] == "xg", "txt": signed((r["full"] - 1) * 100) + "%"} for r in rows]
    spec = {"title": "Home edge per minute, same player", "sub": "Home ÷ away − 1, with fans. Lines are 95% intervals.",
            "words": "Every metric rises by roughly a quarter at home; the intervals are narrow and none overlaps zero.",
            "source": "Study 02 · within-player PPML · 2015/16–2024/25"}
    return figure(spec, hbar(rows, 0, 35, [0, 10, 20, 30], lambda v: f"+{v:.0f}%" if v else "0"),
                  "; ".join(f"{r['label']} {r['txt']}" for r in rows))


def ch_s2_periods():
    p = {r["period"]: r["v"] for r in R["s2_periods"] if r["metric"] == "xg"}
    rows = [("Before", (p["before"] - 1) * 100, "end"), ("Closed doors", (p["closed"] - 1) * 100, "hot"), ("Fans back", (p["after"] - 1) * 100, "end")]
    m = R["s2_market"]
    spec = {"title": "Player xG home edge, by period", "sub": "Same player, home ÷ away − 1.",
            "words": f"The edge fell from +{rows[0][1]:.0f}% to +{rows[1][1]:.0f}% without fans and came back to +{rows[2][1]:.0f}%. "
                     f"The market's home/away win-probability ratio for evenly matched teams fell from {m['ratio_with_fans']:.2f} to {m['ratio_closed']:.2f}.",
            "source": "Study 02 · player level · betting market from football-data.co.uk"}
    return figure(spec, cols(rows, 35, lambda v: f"+{v:.0f}%"), "; ".join(f"{l}: +{v:.0f}%" for l, v, _ in rows))


def ch_s2_leagues():
    rows = sorted(((LEAGUE[r["league"]], (r["full"] - 1) * 100, (r["full_lo"] - 1) * 100, (r["full_hi"] - 1) * 100)
                   for r in R["s2_leagues"] if r["metric"] == "xg"), key=lambda t: -t[1])
    rows = [{"label": l, "v": v, "lo": a, "hi": b, "hot": i == 0, "txt": signed(v) + "%"} for i, (l, v, a, b) in enumerate(rows)]
    spec = {"title": "xG home edge by league", "sub": "Same player, with fans. Lines are 95% intervals.",
            "words": f"{rows[0]['label']} has the largest edge ({rows[0]['txt']}), {rows[-1]['label']} the smallest ({rows[-1]['txt']}).",
            "source": "Study 02 · per-league within-player models"}
    return figure(spec, hbar(rows, 0, 45, [0, 10, 20, 30, 40], lambda v: f"+{v:.0f}%" if v else "0"),
                  "; ".join(f"{r['label']} {r['txt']}" for r in rows))


def ch_s2_hist():
    h = R["s2_hist"]
    edges, raw, shr = h["edges"], h["raw"], h["shrunk"]
    bars = lambda c: "".join(f'<i class="grow-y" style="height:{v / max(c) * 100:.1f}%"></i>' for v in c)
    # edges are log(home ÷ away) units; label the axis in true % changes
    i20 = edges.index(0.2)
    core = shr[i20] + shr[i20 + 1]
    band = f"{signed((math.exp(edges[i20]) - 1) * 100, 0)}% and {signed((math.exp(edges[i20 + 2]) - 1) * 100, 0)}%"
    lo, hi = edges[0], edges[-1]
    tk = '<div class="ticks">' + "".join(f'<span style="left:{pct(math.log(r), lo, hi)}">{t}</span>' for t, r in
                                          (("−75%", 0.25), ("−50%", 0.5), ("0", 1), ("+100%", 2), ("+300%", 4))) + "</div>"
    plot = ('<div class="hist">'
            f'<div class="hist__row"><p class="label"><span>As measured</span><span>spread (SD, log scale) {h["raw_sd"]:.2f}</span></p><div class="hist__bars">{bars(raw)}</div></div>'
            f'<div class="hist__row hist__row--hot"><p class="label"><span>After removing noise</span><span>spread (SD, log scale) {h["shrunk_sd"]:.2f}</span></p><div class="hist__bars">{bars(shr)}</div>{tk}</div>'
            "</div>")
    spec = {"title": "Each player's personal home edge", "sub": f"{h['n']:,} players in this export (the reliability test reports 4,665), xG home vs away. Log scale; each row is scaled to its own peak; outer bars collect everything below −86% or above +639%.",
            "words": f"Measured naively, players' home edges look wildly different. Once match-to-match noise is removed, {core:,} of {h['n']:,} land between {band}.",
            "source": "Study 02 · empirical-Bayes shrinkage"}
    return figure(spec, plot, f"Histogram of {h['n']} players' home edges: wide when raw, a narrow spike after shrinkage.")


def ch_s2_clubs():
    # s2_clubs raw / shrunk are log differences (home ÷ away vs league average); show them as % changes: exp(x) − 1
    top = R["s2_clubs"][:6]
    pc = lambda x: (math.exp(x) - 1) * 100
    rows = [{"label": c["club"], "v": pc(c["shrunk"]), "b": pc(c["raw"]), "kind": "pair",
             "txt": f'{signed(pc(c["raw"]), 0)} → {signed(pc(c["shrunk"]), 1)}%'} for c in top]
    spec = {"title": "The six “strongest home clubs”, before and after removing noise", "sub": "Club xG home edge relative to its league's average.",
            "words": f"Raw, these clubs look {pc(top[-1]['raw']):.0f}–{pc(top[0]['raw']):.0f}% better at home than their league. After shrinkage, each is within about 1%.",
            "source": f"Study 02 · {len(R['s2_clubs'])} clubs, empirical-Bayes shrinkage"}
    return figure(spec, hbar(rows, -5, 40, [0, 10, 20, 30, 40], lambda v: signed(v, 0) + "%" if v else "0") + PAIR_LEGEND("After removing noise", "As measured"),
                  "; ".join(f"{r['label']}: {r['txt']}" for r in rows))


def ch_s3_effects():
    rows = [r for r in R["s3_definitions"] if r["rating"] == "market"]
    rows = [{"label": METRIC[r["metric"]], "v": r["pct"], "lo": r["lo"], "hi": r["hi"], "hot": r["metric"] == "xg", "txt": signed(r["pct"]) + "%"} for r in rows]
    spec = {"title": "Change in output per +1 SD of opponent strength", "sub": "Same player, team and season, venue accounted for. Lines are 95% intervals.",
            "words": "Every attacking metric falls by 10–16% for each step up in opposition; xG by 13.8%.",
            "source": "Study 03 · sequential market rating · 2015/16–2024/25"}
    return figure(spec, hbar(rows, -20, 0, [-20, -15, -10, -5, 0], lambda v: (signed(v, 0) + "%") if v else "0"),
                  "; ".join(f"{r['label']} {r['txt']}" for r in rows))


def ch_s3_quintiles():
    q = [r for r in R["s3_quintiles"] if r["metric"] == "xg"]
    labels = {"Bottom 20%": "Weakest fifth", "Top 20%": "Strongest fifth"}
    rows = [(labels.get(r["q"], r["q"]), 100 + r["pct"], "hot" if r["q"] == "Top 20%" else ("end" if r["q"] == "Bottom 20%" else "")) for r in q]
    spec = {"title": "xG by opponent strength, relative to the weakest fifth", "sub": "Opponents in five equal groups by pre-match rating. Weakest fifth = 100.",
            "words": f"Against the strongest fifth, the same player produces {abs(q[-1]['pct']):.0f}% less xG than against the weakest.",
            "source": "Study 03 · same player, team and season"}
    return figure(spec, cols(rows, 100, lambda v: "100" if v == 100 else signed(v - 100, 1) + "%"),
                  "; ".join(f"{l}: {v:.1f}" for l, v, _ in rows))


def ch_s3_positions():
    names = {"DEF": "Defenders", "MID": "Midfielders", "FWD": "Forwards"}
    rows = [{"label": names[r["pos"]], "v": r["pct"], "lo": r["lo"], "hi": r["hi"], "txt": signed(r["pct"]) + "%"} for r in R["s3_positions"] if r["metric"] == "xg"]
    spec = {"title": "xG per +1 SD of opponent strength, by position", "sub": "Lines are 95% intervals.",
            "words": "Defenders, midfielders and forwards lose about the same share against stronger opponents.",
            "source": "Study 03 · robustness by position"}
    return figure(spec, hbar(rows, -20, 0, [-20, -15, -10, -5, 0], lambda v: (signed(v, 0) + "%") if v else "0"),
                  "; ".join(f"{r['label']} {r['txt']}" for r in rows))


def ch_s3_leagues():
    rows = sorted(((LEAGUE[r["league"]], r["pct"], r["lo"], r["hi"]) for r in R["s3_leagues"] if r["metric"] == "xg"), key=lambda t: t[1])
    rows = [{"label": l, "v": v, "lo": a, "hi": b, "hot": i == 0, "txt": signed(v) + "%"} for i, (l, v, a, b) in enumerate(rows)]
    spec = {"title": "xG per +1 SD of opponent strength, by league", "sub": "Lines are 95% intervals.",
            "words": f"Steepest in {rows[0]['label']} ({rows[0]['txt']}), shallowest in {rows[-1]['label']} ({rows[-1]['txt']}).",
            "source": "Study 03 · per-league models"}
    return figure(spec, hbar(rows, -20, 0, [-20, -15, -10, -5, 0], lambda v: (signed(v, 0) + "%") if v else "0"),
                  "; ".join(f"{r['label']} {r['txt']}" for r in rows))


def ch_s3_elite():
    order = ["xg", "xa", "shots", "key_passes"]
    e = {r["metric"]: r for r in R["s3_elite"]}
    rows = [{"label": METRIC[m], "v": e[m]["overall"], "b": e[m]["past"], "kind": "pair", "txt": f'{e[m]["overall"]:.2f} vs {e[m]["past"]:.2f}'} for m in order]
    spec = {"title": "Which predicts output against elite opponents better?", "sub": "Correlation with output in later matches against elite teams.",
            "words": "For every metric, a player's overall adjusted level predicts his output against elite teams better than his past record against them.",
            "source": "Study 03 · out-of-sample check"}
    return figure(spec, hbar(rows, 0.5, 1.0, [0.5, 0.75, 1.0], lambda v: f"{v:.2f}")
                  + PAIR_LEGEND("Overall adjusted level", "Record against elite teams"),
                  "; ".join(f"{r['label']}: {r['txt']}" for r in rows))


def ch_s3_adjust():
    rows = [{"label": f'{b["season"]} · {b["team"].replace("Manchester United", "Man Utd")}', "v": b["adj"], "b": b["raw"], "kind": "pair",
             "hot": b["season"] == "2022/23", "txt": f'{b["raw"]:.3f} → {b["adj"]:.3f}'} for b in R["s3_bruno"]]
    spec = {"title": "Bruno Fernandes, xA per 90: raw and opponent-adjusted", "sub": "Each season, before and after adjusting for the opponents he faced.",
            "words": "Adjustment barely moves a full season — Bruno's 2022/23 goes from 0.467 to 0.460, still the 99.6th percentile.",
            "source": "Study 03 · season adjustments"}
    return figure(spec, hbar(rows, 0, 0.5, [0, 0.25, 0.5], lambda v: f"{v:.2f}" if v else "0") + PAIR_LEGEND("Opponent-adjusted", "Raw"),
                  "; ".join(f"{r['label']}: {r['txt']}" for r in rows))


def ch_s4_retrieval():
    ret = {r["inputs"]: r for r in R["s4"]["retrieval"] if r["moved"]}
    pick = [("Three seasons · adjusted", "adjusted, w3 vs next w3 (no overlap)", True), ("Three seasons · raw", "raw, w3 vs next w3 (no overlap)", False),
            ("Two seasons · adjusted", "adjusted, w2 vs next w2 (no overlap)", False), ("Two seasons · raw", "raw, w2 vs next w2 (no overlap)", False)]
    rows = [{"label": l, "v": ret[k]["median_pct"], "hot": h, "txt": f'top {ret[k]["median_pct"]:.1f}%'} for l, k, h in pick]
    spec = {"title": "After a league move, how high does a player rank against himself?", "sub": "Median percentile of the player's own earlier profile in the destination role pool. Lower is better.",
            "words": f"With three-season adjusted profiles, the player's own earlier profile sits in the top {rows[0]['v']:.0f}% of the destination pool; raw inputs do worse at every window.",
            "source": f"Study 04 · self-retrieval on {ret[pick[0][1]]['queries']} three-season moves"}
    return figure(spec, hbar(rows, 0, 20, [0, 5, 10, 15, 20], lambda v: f"{v:.0f}%"), "; ".join(f"{r['label']}: {r['txt']}" for r in rows))


NAMES = {"Lazar Samardzic": "Lazar Samardžić", "Matìas Soulè Malvano": "Matías Soulé"}


def ch_s4_bruno():
    cr = R["s4"]["creators"][:4]
    rows = [{"label": "<b>Bruno Fernandes</b> · Premier League", "raw_label": True, "v": 3.6, "hot": True, "txt": "3.6 SD"}]
    rows += [{"label": esc(f'{NAMES.get(c["player"], c["player"])} · {c["team"]}'), "raw_label": True, "v": c["chance creation (z)"], "txt": f'{c["chance creation (z)"]:.1f} SD'} for c in cr]
    spec = {"title": "Chance creation above role average", "sub": "Bruno against the four best creators in Serie A's attacking-mid and wide-forward pool. Standard deviations.",
            "words": f"Bruno is 3.6 SD above his role average; the best in Serie A, {cr[0]['player']}, is {cr[0]['chance creation (z)']:.1f}. His closest profile matches create less still.",
            "source": "Study 04 · Bruno case study, profiles to 2025/26"}
    return figure(spec, hbar(rows, 0, 4, [0, 1, 2, 3, 4], lambda v: f"{v:.0f}"), "; ".join(f"{re.sub('<[^>]+>', '', r['label'])}: {r['txt']}" for r in rows))


def ch_s4_closest():
    out = []
    for b in R["s4"]["bruno"][:3]:
        out.append(f'<li><span class="r">0{b["rank"]}</span><span class="n">{esc(NAMES.get(b["player"], b["player"]))}<small>{esc(b["team"])}'
                   f'{" · robust" if b["robust"] else ""}</small></span><span class="w">{esc(b["why"])}</span><span class="v">{b["median_score"]:.0f}</span></li>')
    return '<ol class="closest">' + "".join(out) + "</ol>"


def ch_s5_overall():
    o = R["s5"]["overall"][0]
    rows = [{"label": f"All {o['n']} league moves", "v": o["vs_stay"] * 100, "lo": o["vs_lo"] * 100, "hi": o["vs_hi"] * 100, "kind": "dot",
             "hot": True, "txt": f"{o['vs_stay'] * 100:.0f}%"}]
    spec = {"title": "Output kept after a move, vs comparable stayers", "sub": "xG + xA per 90. 100% = no change relative to similar players who stayed. Line is the 95% interval.",
            "words": f"Movers keep {o['vs_stay'] * 100:.0f}% (95% interval {o['vs_lo'] * 100:.0f}–{o['vs_hi'] * 100:.0f}%): an average move costs about 3%, and the interval just reaches 100%.",
            "source": "Study 05 · 428 summer moves, 2016/17–2025/26"}
    return figure(spec, hbar(rows, 85, 105, [85, 90, 95, 100, 105], lambda v: f"{v:.0f}%", ref=100), rows[0]["label"] + ": " + rows[0]["txt"])


def ch_s5_leagues():
    d = {r["destination_league"]: r for r in R["s5"]["dest"]}
    o = {r["origin_league"]: r for r in R["s5"]["origin"]}
    rows = [{"label": LEAGUE[k], "v": d[k]["vs_stay"] * 100, "b": o[k]["vs_stay"] * 100, "kind": "pair", "hot": k == "EPL",
             "txt": f'{d[k]["vs_stay"] * 100:.0f}% · {o[k]["vs_stay"] * 100:.0f}%'} for k in LEAGUE]
    spec = {"title": "Output kept moving into vs out of each league", "sub": "vs comparable stayers, xG + xA per 90. 100% = no change.",
            "words": "Moving into the Premier League costs the most and moving out of it gains the most; the Bundesliga and Ligue 1 are the reverse.",
            "source": "Study 05 · 428 moves; per-league 95% intervals in the table below"}
    table = ('<details class="data"><summary>Show the numbers</summary><div class="tscroll"><table><thead><tr><th>League</th><th>Moving into</th><th>Moving out of</th></tr></thead><tbody>'
             + "".join(f'<tr><td>{LEAGUE[k]}</td><td>{d[k]["vs_stay"] * 100:.0f}% ({d[k]["vs_lo"] * 100:.0f}–{d[k]["vs_hi"] * 100:.0f}) · n {d[k]["n"]}</td>'
                       f'<td>{o[k]["vs_stay"] * 100:.0f}% ({o[k]["vs_lo"] * 100:.0f}–{o[k]["vs_hi"] * 100:.0f}) · n {o[k]["n"]}</td></tr>' for k in LEAGUE)
             + "</tbody></table></div></details>")
    return figure(spec, hbar(rows, 70, 130, [70, 100, 130], lambda v: f"{v:.0f}%", ref=100)
                  + PAIR_LEGEND("Moving into", "Moving out of"),
                  "; ".join(f"{r['label']}: into {r['v']:.0f}%, out of {r['b']:.0f}%" for r in rows), after=table)


def ch_s5_groups():
    g = R["s5"]["groups"]
    age = [(r["age bucket"], r["vs_stay"]) for r in g["age"]]
    club = [({"weaker third": "Weakest third", "middle third": "Middle third", "stronger third": "Strongest third"}[list(r.values())[0]], r["vs_stay"]) for r in g["destination_club"]]
    def rows(items):
        return [{"label": l, "v": v * 100, "kind": "dot", "txt": f"{v * 100:.0f}%"} for l, v in items]
    tk = [70, 100, 120]
    plot = ('<p class="label fig-sub">Age at the move</p>' + hbar(rows(age), 70, 120, tk, lambda v: f"{v:.0f}%", ref=100)
            + '<p class="label fig-sub">Destination club strength</p>' + hbar(rows(club), 70, 120, tk, lambda v: f"{v:.0f}%", ref=100))
    spec = {"title": "Output kept vs comparable stayers, by age and destination club", "sub": "xG + xA per 90. 100% = no change.",
            "words": f"Under-21s keep {age[0][1] * 100:.0f}%, players over 30 {age[-1][1] * 100:.0f}%. Joining a club in the weakest third keeps {club[0][1] * 100:.0f}%; the strongest third, {club[-1][1] * 100:.0f}%.",
            "source": "Study 05 · 428 moves"}
    return figure(spec, plot, "; ".join(f"{l}: {v * 100:.0f}%" for l, v in age + club))


def ch_s5_progression():
    ev = {r["model"]: r for r in R["s5"]["test_eval"]}
    steps = [("Naive", "“He'll do what he did before” (post = pre)", "naive"), ("Role", "Pull toward the role average", "shrinkage"),
             ("Context", "Age, minutes, both clubs' strength, leagues", "M3 context"), ("Final model", "Context + three-season history", "Model A")]
    top = 0.14
    out = []
    for i, (name, desc, k) in enumerate(steps):
        e = ev[k]
        last = i == len(steps) - 1
        out.append(f'<li class="prog__step{" prog__step--hot" if last else ""}"><div class="prog__h"><span class="prog__n">0{i + 1}</span><b>{esc(name)}</b><span>{esc(desc)}</span></div>'
                   f'<div class="prog__m"><span class="label">MAE</span><span class="track"><span class="bar grow-x{" bar--hot" if last else ""}" style="width:{e["MAE"] / top * 100:.1f}%;transform-origin:left"></span></span>'
                   f'<span class="hbar__v{" hbar__v--hot" if last else ""}">{e["MAE"]:.3f}</span></div>'
                   f'<div class="prog__r"><span class="label">R²</span><span class="hbar__v">{e["R²"]:.2f}</span></div></li>')
    n = ev["Model A"]["n"]
    spec = {"title": f"Prediction error on {n} locked test moves, step by step", "sub": "First season after the move, xG + xA per 90. Lower MAE is better; higher R² is better.",
            "words": f"Each step adds information and lowers the error: {ev['naive']['MAE']:.3f} → {ev['shrinkage']['MAE']:.3f} → {ev['M3 context']['MAE']:.3f} → {ev['Model A']['MAE']:.3f}.",
            "source": "Study 05 · locked test, 2023/24–2025/26"}
    return figure(spec, '<ol class="prog">' + "".join(out) + "</ol>", spec["words"])


def ch_s5_similarity():
    ev = {r["model"]: r for r in R["s5"]["sim_eval"]}
    rows = [("“He'll do what he did”", "naive", False), ("Similar players only", "Model B: comparables only", False),
            ("Own history", "Model A: own history", True), ("Own history + similar players", "A + comparable output", False)]
    rows = [{"label": l, "v": ev[k]["MAE"], "hot": h, "txt": f'{ev[k]["MAE"]:.4f}'} for l, k, h in rows]   # 4 dp: own history vs + similarity differ by 0.0004
    a, nv = ev["Model A: own history"]["MAE"], ev["naive"]["MAE"]
    spec = {"title": f"Prediction error on {ev['naive']['n']} league moves", "sub": "Mean absolute error, xG + xA per 90, first season after the move. Lower is better.",
            "words": f"Similar players alone barely beat the naive guess. The player's own history cuts the error by {round((1 - a / nv) * 100)}%; adding similarity on top moves it by less than 0.001.",
            "source": "Study 05 · critical experiment, transfers with Study 4 profiles"}
    return figure(spec, hbar(rows, 0, 0.14, [0, 0.04, 0.08, 0.12], lambda v: f"{v:.2f}" if v else "0"), "; ".join(f"{r['label']}: {r['txt']}" for r in rows))


def ch_s5_calibration():
    cal = R["s5"]["calibration"]
    dots = []
    for c in cal:
        x, y = c["mean_predicted"] * 100, c["observed"] * 100
        dots.append(f'<span class="cal__ci" style="left:{x:.1f}%;bottom:{c["lo"] * 100:.1f}%;height:{(c["hi"] - c["lo"]) * 100:.1f}%"></span>'
                    f'<span class="cal__dot" style="left:{x:.1f}%;bottom:{y:.1f}%" title="predicted {x:.0f}%, observed {y:.0f}%"></span>')
    plot = ('<div class="cal"><div class="cal__plot"><span class="cal__diag"></span>' + "".join(dots) + "</div>"
            '<div class="cal__x"><span>0%</span><span>Predicted chance of keeping ≥75%</span><span>100%</span></div>'
            '<div class="cal__y"><span>Observed share</span></div></div>')
    top = cal[-2:]
    cl = [r for r in R["s5"]["classification"] if "75" in r["threshold"]][0]
    spec = {"title": "Is the chance of keeping ≥75% honest?", "sub": f"Five groups of about {cal[0]['n']} test moves. On the diagonal = says what it means.",
            "words": f"Where the model says about {top[0]['mean_predicted'] * 100:.0f}% and {top[1]['mean_predicted'] * 100:.0f}%, {top[0]['observed'] * 100:.0f}% and {top[1]['observed'] * 100:.0f}% of players kept ≥75%. "
                     f"Lower down it is less reliable. AUC {cl['AUC Model A']:.2f}; Brier {cl['Brier Model A']:.3f} vs {cl['Brier base rate']:.3f} for a same-for-everyone guess.",
            "source": "Study 05 · locked test, calibration by fifths"}
    return figure(spec, plot, spec["words"])


CHARTS = {k[3:].replace("_", "-"): v for k, v in globals().items() if k.startswith("ch_")}


def chart(ref):
    if isinstance(ref, dict):
        return inline_chart(ref)
    if ref not in CHARTS:
        fail(f"unknown chart '{ref}'")
    return CHARTS[ref]()


# ============================================================ page components
def status_pill(status, label):
    cls = {"final": "pill--final", "pending": "pill--pending", "open": "pill--pending", "live": "pill--live"}[status]
    return f'<span class="pill {cls}">{esc(label)}</span>'


def study_nav(cur):
    items = []
    for s in STUDIES:
        here = s["slug"] == cur
        items.append(f'<li><a href="/football/research/{s["slug"]}"{" aria-current=\"page\"" if here else ""}>'
                     f'<span class="snav__n">0{s["id"]}</span><span class="snav__t">{esc(s.get("nav", s["short"]))}</span>'
                     + ('<span class="snav__st" title="Weather freeze pending">pending</span>' if s["status"] == "pending" else "") + "</a></li>")
    return f'<nav class="snav" aria-label="Studies"><div class="wrap"><ol>{"".join(items)}</ol></div></nav>'


def crumbs(s=None):
    tail = (f'<li><a href="/football/research">Research</a></li><li aria-current="page">0{s["id"]} {esc(s["short"])}</li>'
            if s else '<li aria-current="page">Research</li>')
    return f'<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li>{tail}</ol></nav>'


def section(n, sid, title, body, extra_cls=""):
    lab = FRAMEWORK[n - 1]
    # the framework label IS the section heading (no duplicate visible title)
    return (f'<section class="ss{extra_cls}" id="{sid}" aria-labelledby="{sid}-h">\n<div class="wrap ss__grid">\n'
            f'<div class="ss__rail"><h2 class="ss__k" id="{sid}-h"><span>{n:02d}</span>{esc(lab)}</h2></div>\n'
            f'<div class="ss__body">\n{body}\n</div>\n</div>\n</section>')


def hero(s):
    turn = (f'<p class="turn" data-reveal><span>{esc(s["turn"]["before"])}</span><b>{esc(s["turn"]["after"])}</b></p>' if s.get("turn") else "")
    clarify = (f'<p class="clarify">{"<br>".join(esc(x) for x in s["clarify"])}</p>' if s.get("clarify") else "")
    strip = "".join(f'<li><b>{esc(v)}</b><span>{esc(k)}</span></li>' for v, k in s["sample"])
    status = ""
    if s["status"] != "final":
        rows = "".join(f'<li>{status_pill(st, lab)}<span>{esc(part)}</span></li>' for part, st, lab in s["status_parts"])
        status = (f'<aside class="status-box" aria-label="Study status"><p class="label">Status · {esc(s["status_label"])}</p>'
                  f'<ul>{rows}</ul><p>{esc(s["status_note"])}</p></aside>')
    return f"""<header class="s-hero wrap">
  {turn}
  <p class="eyebrow s-hero__no" data-reveal><b class="s-hero__num">0{s["id"]}</b> / {esc(s["short"])} {status_pill(s["status"], s["status_label"])}</p>
  <div class="s-hero__grid">
    <div>
      <h1 id="q-h">{esc(s["question"])}</h1>
      <p class="study-sub">{esc(s["subquestion"])}</p>
      {clarify}
      <ul class="s-meta" aria-label="Study scope">{strip}</ul>
    </div>
    <div class="s-hero__side">
      <div class="callout" data-reveal><p class="label">Finding</p><p>{md(s["summary"])}</p></div>
      {status}
    </div>
  </div>
</header>"""


def why(s):
    w = s["why"]
    body = "".join(f'<p class="body">{md(p)}</p>' for p in w["body"]) + f'<p class="q-big">{md(w["question"])}</p>'
    return section(2, "why", "Why this matters", body)


def method(s):
    m = s["method"]
    dims = ""
    if m.get("dims"):
        dims = '<div class="dims" data-reveal>' + "".join(
            f'<div class="dims__g"><p class="label">{esc(g)}</p><ul>{"".join(f"<li>{md(x)}</li>" for x in items)}</ul></div>' for g, items in m["dims"]) + "</div>"
    steps = "".join(f'<li>{esc(x)}</li>' for x in m["flow"])
    result = f'<li class="flow__out">{esc(m["result"])}</li>' if m.get("result") else ""
    flow = f'<ol class="flow{" flow--v" if m.get("vertical") else ""}" aria-label="Method in steps" data-reveal>{steps}{result}</ol>'
    bench = f'<p class="benchmark"><span class="label">The benchmark</span>{md(m["benchmark"])}</p>' if m.get("benchmark") else ""
    tech = "".join(f"<p>{md(p)}</p>" for p in m["technical"])
    body = (dims + flow + bench + f'<p class="body">{md(m["plain"])}</p>'
            f'<div class="acc"><details><summary><span class="label">Technical detail</span><span class="acc__h">How the estimate is built</span></summary>'
            f'<div class="acc__body">{tech}</div></details></div>')
    return section(3, "method", "What we did", body)


def finding(f, s):
    k = f["kind"]
    if k == "group":
        return f'<div class="fgroup"><h3>{esc(f["title"])}</h3>{status_pill(f["status"], f["status_label"])}</div>'
    if k == "counter":
        intro = f'<p class="body">{md(f["intro"])}</p>' if f.get("intro") else ""
        ch = chart(f["chart"]) if f.get("chart") else ""
        return (f'<article class="find find--counter"><h3 class="find__h">{esc(f["title"])}</h3>{intro}'
                f'<p class="counter" data-reveal><b class="count" data-to="{esc(f["value"])}">{esc(f["value"])}</b><span class="counter__of">of {esc(f["of"])}</span>'
                f'<span class="counter__l">{esc(f["label"])}</span></p><p class="lead">{md(f["lead"])}</p>{ch}</article>')
    if k == "open":
        return f'<aside class="open-box"><p class="label">{esc(f["title"])}</p><p>{md(f["lead"])}</p></aside>'
    if k == "locked":
        steps = "".join(f"<li>{esc(x)}</li>" for x in f["steps"])
        return (f'<article class="find"><h3 class="find__h">{esc(f["title"])}</h3>'
                f'<ol class="locked" data-reveal>{steps}</ol><p class="lead">{md(f["lead"])}</p></article>')
    if k == "failure":
        ex = f["example"]
        top = max(v for _, v in ex["rows"]) * 1.25
        bars = "".join(f'<div class="hbar__row"><span class="hbar__lbl">{esc(l)}</span><span class="track"><span class="bar grow-x{" bar--hot" if l == "Actual" else ""}" '
                       f'style="width:{v / top * 100:.1f}%;transform-origin:left"></span></span><span class="hbar__v">{v:.2f}</span></div>' for l, v in ex["rows"])
        link = f'<p><a class="link-arrow" href="{f["link"][0]}">{esc(f["link"][1])} <span class="arr" aria-hidden="true">→</span></a></p>' if f.get("link") else ""
        return (f'<article class="find find--fail"><p class="label find__k">Known weakness</p><h3 class="find__h">{esc(f["title"])}</h3><p class="lead">{md(f["lead"])}</p>'
                f'<div class="fail-ex"><p class="fail-ex__n">Example: {esc(ex["name"])}</p><p class="small muted">{esc(ex["context"])}</p>'
                f'<div class="hbar" role="img" aria-label="{esc("; ".join(f"{l} {v:.2f}" for l, v in ex["rows"]))} xG + xA per 90">{bars}</div>'
                f'<p class="source" style="margin-top:8px">xG + xA per 90 · Study 05 case study</p></div>'
                f'<p class="body">{md(f["explain"])}</p>{link}</article>')
    ch = chart(f["chart"]) if f.get("chart") else ""
    explain = f'<p class="body find__x">{md(f["explain"])}</p>' if f.get("explain") else ""
    if k == "headline":
        return (f'<article class="find find--head"><h3 class="find__big">{esc(f["title"])}</h3><p class="lead lead--big">{md(f["lead"])}</p>'
                f'{ch}{explain}</article>')
    if k == "climax":
        lst = f'<div class="closest-wrap"><p class="label">{esc(f["list_title"])}</p>{chart(f["list"])}</div>'
        return (f'<article class="find find--climax"><h3 class="find__big">{esc(f["title"])}</h3><p class="lead lead--big">{md(f["lead"])}</p>'
                f'<div class="ev">{ch}{lst}</div><p class="callout callout--warn" data-reveal><strong>{esc(f["callout"])}</strong></p>{explain}</article>')
    if k == "progression":
        return f'<article class="find"><h3 class="find__h">{esc(f["title"])}</h3><p class="lead">{md(f["lead"])}</p>{ch}</article>'
    # evidence: key result as text first, then the figure (M2 §29)
    if not ch:
        return f'<article class="find"><h3 class="find__h">{esc(f["title"])}</h3><p class="lead">{md(f["lead"])}</p>{explain}</article>'
    return (f'<article class="find find--ev"><div class="ev"><div><h3 class="find__h">{esc(f["title"])}</h3><p class="lead">{md(f["lead"])}</p>{explain}</div>'
            f'{ch}</div></article>')


def found(s):
    return section(4, "found", "What we found", "\n".join(finding(f, s) for f in s["findings"]))


def surprise(s):
    w = s["surprise"]
    body = ('<ol class="surprise">'
            f'<li><p class="label">What the raw data suggested</p><p>{md(w["suggested"])}</p></li>'
            f'<li><p class="label">What happened after we checked</p><p>{md(w["after"])}</p></li>'
            f'<li class="surprise__l"><p class="label">Lesson</p><p>{md(w["lesson"])}</p></li></ol>')
    return section(5, "surprise", "What surprised us", body)


def meaning(s):
    return section(6, "meaning", "What it means", '<ul class="means">' + "".join(f"<li>{md(p)}</li>" for p in s["meaning"]) + "</ul>")


def limits(s):
    body = ('<ul class="limits">' + "".join(f"<li>{md(p)}</li>" for p in s["limitations"]) + "</ul>"
            f'<p class="prov"><span class="label">Sources</span>{esc(C["sources"])}<br><span class="label">Analysis period</span>{esc(s["period"])} · frozen dataset · '
            '<a href="/football/methodology">Methodology</a></p>')
    return section(7, "limits", "Limitations", body)


def transition(s):
    n = s["next"]
    if n.get("slug"):
        t = BY_SLUG[n["slug"]]
        href, target = f'/football/research/{t["slug"]}', f'0{t["id"]} / {t["short"]}'
    else:
        href, target = n["href"], n["label"]
    kicker = f'<p class="next__k">{esc(n["kicker"])}</p>' if n.get("kicker") else ""
    return (f'<section class="next" aria-labelledby="next-h"><div class="wrap">'
            f'<p class="ss__k"><span>08</span>The next question</p>{kicker}'
            f'<h2 id="next-h">{esc(n["question"])}</h2><span class="next__arrow" aria-hidden="true">↓</span>'
            f'<a class="next__go" href="{href}">{esc(target)} <span class="arr" aria-hidden="true">→</span></a></div></section>')


def pager(s):
    i = STUDIES.index(s)
    prev = STUDIES[i - 1] if i else None
    nxt = STUDIES[i + 1] if i + 1 < len(STUDIES) else None
    a = (f'<a class="pager__prev" href="/football/research/{prev["slug"]}"><span class="label">← Previous study</span><span>0{prev["id"]} {esc(prev["short"])}</span></a>' if prev
         else '<a class="pager__prev" href="/football/research"><span class="label">← All research</span><span>One question, five studies</span></a>')
    b = (f'<a class="pager__next" href="/football/research/{nxt["slug"]}"><span class="label">Next study →</span><span>0{nxt["id"]} {esc(nxt["short"])}</span></a>' if nxt
         else '<a class="pager__next" href="/football/research"><span class="label">Back to →</span><span>All research</span></a>')
    return f'<nav class="pager wrap" aria-label="Study sequence">{a}{b}</nav>'


def ld_article(s, path):
    url = fb_chrome.SITE + path
    return {"@context": "https://schema.org", "@type": "ScholarlyArticle", "headline": f'Study 0{s["id"]} — {s["title"]}',
            "description": s["meta"]["description"], "url": url, "mainEntityOfPage": url,
            "image": f'{fb_chrome.SITE}/football/og/{s["meta"]["og_image"]}', "inLanguage": "en",
            "creativeWorkStatus": "Draft" if s["status"] == "pending" else "Published",
            "author": {"@id": "https://iyush.dev/#person"}, "isPartOf": {"@id": "https://iyush.dev/football#site"},
            "about": "Association football performance analytics"}


def page(path, meta, ld, body, og_type="article"):
    updated = datetime.fromisoformat(META["tracker_generated_utc"]).strftime("%b %Y")
    return (fb_chrome.head(path, meta["title"], meta["description"], meta["og_title"], meta["og_image"], ld, og_type) + "\n<body>\n"
            + fb_chrome.header(path) + "\n\n" + body + "\n\n" + fb_chrome.footer(updated) + "\n</body>\n</html>\n")


def study_page(s):
    for key in ("question", "why", "method", "findings", "surprise", "meaning", "limitations", "next"):
        if not s.get(key):
            fail(f'study {s["id"]} is missing framework section "{key}"')
    path = f'/football/research/{s["slug"]}'
    body = ('<main id="main" class="study" aria-labelledby="q-h">\n' + crumbs(s) + "\n" + study_nav(s["slug"]) + "\n" + hero(s) + "\n"
            + why(s) + "\n" + method(s) + "\n" + found(s) + "\n" + surprise(s) + "\n" + meaning(s) + "\n" + limits(s) + "\n"
            + transition(s) + "\n" + pager(s) + "\n</main>")
    return path, page(path, s["meta"], ld_article(s, path), body)


def index_page():
    ix = C["index"]
    path = "/football/research"
    strip = "".join(f'<li><b>{esc(v)}</b><span>{esc(k)}</span></li>' for v, k in ix["strip"])
    spine = []
    for s in STUDIES:
        spine.append(f"""<li class="tl-item{" tl-item--last" if s is STUDIES[-1] else ""}">
  <span class="tl-no" aria-hidden="true">0{s["id"]}</span>
  <div class="tl-body">
    <p class="tl-kicker"><b>0{s["id"]} / {esc(s["short"])}</b> <span>{esc(s["period"])}</span> {status_pill(s["status"], s["status_label"])}</p>
    <h3 class="tl-q"><a class="spine__a" href="/football/research/{s["slug"]}">{esc(s["spine_question"])}</a></h3>
    <p class="tl-a">{esc(s["spine_answer"])}</p>
    <p class="tl-d">{md(s["summary"])}</p>
    <a class="link-arrow" href="/football/research/{s["slug"]}">Read the study<span class="sr-only">: 0{s["id"]}, {esc(s["short"])}</span> <span class="arr" aria-hidden="true">→</span></a>
  </div>
</li>""")
    lessons = "".join(f'<li><p class="lesson__h">{md(h)}</p><p>{md(b)}</p></li>' for h, b in ix["lessons"])
    corr = "".join(f"<li>{md(c)}</li>" for c in ix["corrections"])
    opn = "".join(f"<li>{md(c)}</li>" for c in ix["open"])
    fit = "".join(f'<p class="body">{md(p)}</p>' for p in ix["fit"])
    body = f"""<main id="main">
{crumbs()}
<section class="hero" aria-labelledby="r-h">
  <div class="wrap">
    <p class="eyebrow">{esc(ix["eyebrow"])}</p>
    <h1 id="r-h">{esc(ix["title"])}</h1>
    <p class="lede">{esc(ix["lede"])}</p>
    <ul class="strip strip--4" aria-label="The dataset">{strip}</ul>
  </div>
</section>

<section class="section" id="spine" aria-labelledby="spine-h">
  <div class="wrap">
    <div class="section__head">
      <p class="eyebrow">The research spine</p>
      <h2 id="spine-h">{esc(ix["spine_title"])}</h2>
      <p class="lede">{esc(ix["spine_lede"])}</p>
    </div>
    <ol class="timeline">
{"".join(spine)}
    </ol>
  </div>
</section>

<section class="section" aria-labelledby="fit-h">
  <div class="wrap grid">
    <div class="d-4"><p class="eyebrow">Synthesis</p><h2 id="fit-h" class="h2-sm">{esc(ix["fit_title"])}</h2></div>
    <div class="d-7 d-end">{fit}</div>
  </div>
</section>

<section class="section" aria-labelledby="lessons-h">
  <div class="wrap">
    <div class="section__head"><p class="eyebrow">What we learned</p><h2 id="lessons-h">{esc(ix["lessons_title"])}</h2></div>
    <ol class="lessons">{lessons}</ol>
  </div>
</section>

<section class="section" aria-labelledby="corr-h">
  <div class="wrap grid">
    <div class="d-6">
      <p class="eyebrow">Corrections</p><h2 id="corr-h" class="h2-sm">{esc(ix["corrections_title"])}</h2>
      <p class="body" style="margin-top:16px">{esc(ix["corrections_lede"])}</p>
      <ul class="limits">{corr}</ul>
    </div>
    <div class="d-5 d-end">
      <p class="eyebrow"><span class="pill pill--pending">Open</span></p><h2 class="h2-sm">{esc(ix["open_title"])}</h2>
      <ul class="limits" style="margin-top:16px">{opn}</ul>
      <p class="prov"><span class="label">Sources</span>{esc(C["sources"])}<br><span class="label">Analysis period</span>2015/16 — 2024/25 · frozen dataset · <a href="/football/methodology">Methodology</a></p>
    </div>
  </div>
</section>
</main>"""
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Research · Home Turf & Hard Opponents",
          "url": fb_chrome.SITE + path, "description": ix["meta"]["description"], "isPartOf": {"@id": "https://iyush.dev/football#site"},
          "hasPart": [{"@type": "ScholarlyArticle", "headline": f'Study 0{s["id"]} — {s["title"]}', "url": f'{fb_chrome.SITE}/football/research/{s["slug"]}'} for s in STUDIES]}
    return path, page(path, ix["meta"], ld, body, "website")


if __name__ == "__main__":
    out = [index_page()] + [study_page(s) for s in STUDIES]
    for path, doc in out:
        f = FB / (path[len("/football/"):] + ("/index.html" if path == "/football/research" else ".html"))
        f.write_text(doc)
        print(f"{path:40} {len(doc) / 1024:6.1f} KB")
