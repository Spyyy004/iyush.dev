#!/usr/bin/env python3
"""Render /football/methodology (M8 §8–21) from content/methodology.json.

    python3 scripts/build_methodology.py

Every section carries `checks` — [findings file, regex] pairs against ~/dev/weather_football/findings — and the build
fails if any no longer matches, so the page cannot drift from the research. {glossary-key|label} markup is validated
against content/glossary.json (the build fails on an unknown key).
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
C = json.loads((SITE / "content/methodology.json").read_text())
GLOSS = json.loads((SITE / "content/glossary.json").read_text())["terms"]
META = json.loads((FB / "data/meta.json").read_text())
PATH = "/football/methodology"
esc = html.escape


def fail(msg):
    sys.exit("build_methodology: " + msg)


def md(text):
    """{key|label} → glossary term button; **bold**. Text is trusted content (it may carry <a> links)."""
    def term(m):
        key, label = m.group(1), m.group(2)
        if key not in GLOSS:
            fail(f"unknown glossary term '{key}' in: {text[:60]}")
        return f'<button type="button" class="term" data-term="{key}">{label}</button>'
    text = re.sub(r"\{([a-z0-9-]+)\|([^}]+)\}", term, text)
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)


# ---------------------------------------------------------------- guards: every section's numbers must still be in the research
_cache = {}
n_checks = 0
for s in C["sections"]:
    for f, pat in s.get("checks", []):
        if f not in _cache:
            _cache[f] = re.sub(r"\s+", " ", (RS / "findings" / f"{f}.md").read_text())   # findings wrap long lines
        if not re.search(pat, _cache[f]):
            fail(f"section '{s['id']}': findings/{f}.md no longer matches /{pat}/ — re-check the methodology against the research")
        n_checks += 1
ids = {s["id"] for s in C["sections"]}
for _, anchor in C["hero"]["pipeline"]:
    if anchor not in ids:
        fail(f"pipeline step points at missing section #{anchor}")
gl_methods = {g["method"] for g in GLOSS.values() if g["method"]}
if not gl_methods <= ids:
    fail(f"glossary links to missing methodology sections: {gl_methods - ids}")


# ---------------------------------------------------------------- render
def flow(steps, to=None):
    sep = '<li class="mt-flow__op" aria-hidden="true">+</li>' if to else '<li class="mt-flow__op" aria-hidden="true">↓</li>'
    items = sep.join(f'<li class="mt-flow__s">{esc(x)}</li>' for x in steps)
    if to:
        items += f'<li class="mt-flow__op" aria-hidden="true">↓</li><li class="mt-flow__s mt-flow__s--to">{esc(to)}</li>'
    label = (" + ".join(steps) + (f" → {to}" if to else "")) if to else " → ".join(steps)
    return f'<ol class="mt-flow{" mt-flow--sum" if to else ""}" aria-label="{esc(label)}">{items}</ol>'


def block(b):
    cells = [("Why this?", b["why"]), ("Technical implementation", b["technical"]), ("What it controls for", b["controls"]), ("What it doesn't solve", b["not"])]
    return (f'<div class="mt-block"><h3>{esc(b["h"])}</h3><dl class="mt-quad">'
            + "".join(f'<div class="mt-quad__{i}"><dt>{t}</dt><dd>{md(v)}</dd></div>' for i, (t, v) in enumerate(cells)) + "</dl></div>")


def section(s):
    parts = [f'<p class="lv-kicker">{s["num"]} · {esc(s["kicker"])}</p><h2 id="{s["id"]}-h" class="h2-sm">{esc(s["title"])}</h2>']
    if s.get("lead"):
        parts.append(f'<p class="lede mt-lead">{md(s["lead"])}</p>')
    if s.get("stats"):
        parts.append('<dl class="mt-stats">' + "".join(f"<div><dt>{esc(l)}</dt><dd>{esc(v)}</dd></div>" for v, l in s["stats"]) + "</dl>")
    if s.get("sources"):
        parts.append('<ul class="mt-sources">' + "".join(
            f'<li><p class="mt-src__n">{esc(n)}</p><p>{esc(what)}</p><p class="small muted">Used in: {esc(where)}</p></li>' for n, what, where in s["sources"]) + "</ul>")
    if s.get("flow"):
        parts.append(flow(s["flow"], s.get("flow_to")))
    if s.get("callout") and s["id"] == "opponents":
        parts.append(f'<div class="mt-callout"><p class="mt-callout__v">{esc(s["callout"][0])}</p><p>{md(s["callout"][1])}</p></div>')
    for b in s.get("blocks", []):
        parts.append(block(b))
    if s.get("callout") and s["id"] != "opponents":
        parts.append(f'<div class="mt-callout mt-callout--key"><p class="label">{esc(s["callout"][0])}</p><p>{md(s["callout"][1])}</p></div>')
    if s.get("items"):
        parts.append('<ul class="mt-items">' + "".join(f"<li><b>{esc(h)}</b><span>{md(t)}</span></li>" for h, t in s["items"]) + "</ul>")
    if s.get("metrics"):
        parts.append('<dl class="mt-metrics">' + "".join(
            f'<div><dt><button type="button" class="term" data-term="{g}">{esc(k)}</button></dt><dd>{esc(v)}<small>{esc(sub)}</small></dd></div>' for k, v, sub, g in s["metrics"]) + "</dl>")
    if s.get("scope"):
        parts.append(f'<p class="mt-scope">{esc(s["scope"])}</p>')
    if s.get("chips"):
        parts.append('<ul class="mt-chips" aria-label="Not in the data">' + "".join(f"<li>{esc(c)}</li>" for c in s["chips"]) + "</ul>")
    for p in s.get("paras", []):
        parts.append(f'<p class="body mt-p">{md(p)}</p>')
    if s.get("link"):
        parts.append(f'<p><a class="link-arrow" href="{s["link"][0]}">{esc(s["link"][1])} <span class="arr" aria-hidden="true">→</span></a></p>')
    if s.get("corrections"):
        parts.append('<ol class="mt-corr">' + "".join(
            f'<li><p class="mt-corr__m"><time datetime="{d}">{datetime.fromisoformat(d).strftime("%-d %b %Y")}</time> · {esc(w)}</p><p>{md(t)}</p></li>' for d, w, t in s["corrections"]) + "</ol>")
    return f'<section class="lv-sec mt-sec" id="{s["id"]}" aria-labelledby="{s["id"]}-h"><div class="wrap mt-wrap">' + "".join(parts) + "</div></section>"


h = C["hero"]
pipe = "".join(f'<li><a href="#{a}">{esc(l)}</a></li>' + ('<li aria-hidden="true">↓</li>' if i < len(h["pipeline"]) - 1 else "")
               for i, (l, a) in enumerate(h["pipeline"]))
toc = "".join(f'<li><a href="#{s["id"]}"><span>{s["num"]}</span>{esc(s["kicker"])}</a></li>' for s in C["sections"])
body = f"""<main id="main" class="mt">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li aria-current="page">Methodology</li></ol></nav>
<header class="mt-hero wrap">
  <div><p class="lv-kicker">{esc(h["kicker"])}</p><h1>{esc(h["title"])}</h1><p class="lede">{esc(h["lede"])}</p>
    <p class="small muted">Terms with a dotted underline open a definition · <a href="/football/glossary">Full glossary →</a></p></div>
  <ol class="mt-pipe" aria-label="The research pipeline">{pipe}</ol>
</header>
<nav class="wrap mt-toc" aria-label="On this page"><ol>{toc}</ol></nav>
{"".join(section(s) for s in C["sections"])}
</main>"""

desc = ("How do we know? The data (18,011 matches, five leagues, 2015/16–2024/25), context adjustment, pre-match opponent ratings "
        "(0 of 155,282 leakage checks changed), PPML models, similarity and transfer methods, locked-test validation, limitations and corrections.")
ld = {"@context": "https://schema.org", "@type": "TechArticle", "headline": "How do we know? · Methodology", "description": desc, "url": fb_chrome.SITE + PATH,
      "author": {"@id": "https://iyush.dev/#person"}, "isPartOf": {"@id": "https://iyush.dev/football#site"}}
updated = datetime.fromisoformat(META["tracker_generated_utc"]).strftime("%b %Y")
doc = (fb_chrome.head(PATH, "Methodology · How do we know? · Home Turf & Hard Opponents", desc, "How do we know?", "methodology.png", ld)
       + "\n<body>\n" + fb_chrome.header(PATH) + "\n\n" + body + "\n\n" + fb_chrome.footer(updated) + "\n</body>\n</html>\n")
(FB / "methodology.html").write_text(doc)
print(f"methodology: {len(C['sections'])} sections · {n_checks} findings checks passed · page {len(doc) / 1024:.1f} KB")
