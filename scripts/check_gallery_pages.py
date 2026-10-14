#!/usr/bin/env python3
"""Check every generated match page against the canonical M1 record it was rendered from (gallery M3).

    python3 scripts/check_gallery_pages.py [path/to/GALLERY] [--record extra.json]

Stdlib only. Exits non-zero on the first page that shows a number, label or status its record does not support.
--record renders and checks one extra record (e.g. a synthetic partial rating) without writing it to the site.
"""
import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery_pages  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
argv = sys.argv[1:]
EXTRA = None
if "--record" in argv:
    i = argv.index("--record")
    EXTRA = argv[i + 1]
    argv = argv[:i] + argv[i + 2:]
SRC = Path(argv[0]) if argv else Path.home() / "dev/weather_football/data/processed/GALLERY"
MATCH_DIR = ROOT / "football" / "gallery" / "match"
problems = []


def need(cond, page, what):
    if not cond:
        problems.append(f"{page}: {what}")


def text(doc):
    return html.unescape(doc)


TOL = 0.02   # M1's documented rounding tolerance (CONTRIBUTION_TOLERANCE)


def check_rated(r, doc, page):
    sc, c, st = r["score"], r["contributions"], r["stats"]
    t = text(doc)
    # the record must be self-consistent before its numbers are trusted on a page
    total = sum(c[k]["points"] for k in ("entertainment", "competitiveness", "drama"))
    need(abs(total - r["match_score"]) <= TOL, page, f"components add to {total:.2f}, score is {r['match_score']}")
    for k in ("entertainment", "competitiveness"):
        ps = sum(p["points"] for p in c[k]["parts"].values() if p)
        need(abs(ps - c[k]["points"]) <= TOL, page, f"{k} parts add to {ps:.2f}, not {c[k]['points']}")
    fs = sum(f["points"] for f in c["drama"]["factors"].values())
    need(c["drama"]["capped"] or abs(fs - c["drama"]["points"]) <= TOL, page, "drama factors do not add up")
    need(f"{r['home']} {sc['home']}–{sc['away']} {r['away']}" in re.search(r"<title>(.*?)</title>", t).group(1), page, "title score")
    need(f'aria-label="{r["stars"]:.1f} out of 5 stars"' in doc, page, "stars")
    need(f'<span class="num">{r["match_score"]:.1f}</span>' in doc, page, "match score")
    for k in ("entertainment", "competitiveness", "drama"):
        need(f'{r["components"][k]:.2f}<small> of 1.00</small>' in doc, page, f"{k} component score")
        need(f'{c[k]["points"]:.1f}<small> of {c[k]["max_points"]:.0f}</small>' in doc, page, f"{k} points")
    parts = [p for p in c["entertainment"]["parts"].values() if p] + list(c["competitiveness"]["parts"].values()) \
        + list(c["drama"]["factors"].values())
    for p in parts:
        need(f'{p["points"]:.1f} pts' in doc, page, f"part points {p['points']}")
    # timeline: every goal once, with its type, ending on the final score; shootout never counted as goals
    goals = st["goals"]
    for kind, label in (("penalty", "Penalty"), ("own_goal", "Own goal"), ("goal", "Goal")):
        need(doc.count(f"<b>{label}</b>") == sum(g.get("type") == kind for g in goals), page, f"{label} count")
    if goals:
        end = "End of extra time" if sc["aet"] else "Full time"
        need(f"{end} · {sc['home']}–{sc['away']}" in t, page, "timeline final score")
    need(("Penalty shootout" in t) == bool(sc["shootout"]), page, "shootout shown iff there was one")
    # statistics: missing values are never zeros
    if None in st["shots_on_target"]:
        need("Not available" in t, page, "missing SOT shown as not available")
    if st["xg"] is None:
        need("Not available for this competition" in t, page, "no xG for UEFA")
    else:
        need(f"{st['xg'][0]:.2f}" in t and "not in the rating" in t, page, "xG with context note")
    for lab in r["labels"]:
        need(f">{lab['label']}</a></dt>" in doc, page, f"label {lab['label']}")
    need(("Partial rating" in t) == r["quality"]["partial"], page, "partial badge iff partial")
    need("noindex" not in doc, page, "rated pages are indexable")


def check_unrated(r, doc, page):
    t = text(doc)
    need("Not rated" in t and "gx-stars" not in doc and "gm-total" not in doc and "Match statistics" not in t,
         page, "unrated page shows no rating, score breakdown or statistics")
    need("noindex" in doc, page, "unrated pages are noindex")
    need(gallery_pages.UNRATED_REASON[r["eligibility"].split(":", 1)[1]] in t, page, "reason")


n = 0
for season in ("2026", "2025"):
    d = json.loads((SRC / f"ratings_{season}.json").read_text())
    rules = d["meta"]["label_rules"]
    export = {m["k"]: m for m in json.loads((ROOT / "football/data/gallery" / f"{season}.json").read_text())["matches"]}
    for r in d["matches"]:
        mid = gallery_pages.match_id(r["match_key"])
        path = MATCH_DIR / f"{mid}.html"
        need(path.exists(), mid, "page missing")
        if not path.exists():
            continue
        doc = path.read_text()
        need(doc == gallery_pages.render_match(r, rules)[1], mid, "page is stale (re-run build_gallery.py)")
        need(export[r["match_key"]]["u"] == mid, mid, "gallery card links elsewhere")
        check_rated(r, doc, mid)
        n += 1
    for r in d["unrated"]:
        mid = gallery_pages.match_id(r["match_key"])
        doc = (MATCH_DIR / f"{mid}.html").read_text()
        check_unrated(r, doc, mid)
        n += 1
if EXTRA:
    r = json.loads(Path(EXTRA).read_text())
    rules = json.loads((SRC / f"ratings_{r['season']}.json").read_text())["meta"]["label_rules"]
    check_rated(r, gallery_pages.render_match(r, rules)[1], "extra record")
    n += 1
if problems:
    print("\n".join(problems[:40]))
    sys.exit(f"check_gallery_pages: {len(problems)} problems in {n} pages")
print(f"check_gallery_pages: {n} pages match their records")
