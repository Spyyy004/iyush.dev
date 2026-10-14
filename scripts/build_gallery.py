#!/usr/bin/env python3
"""Football Match Gallery (M2, M3): export the canonical M1 match ratings and render /football/gallery and one page per
match at /football/gallery/match/<id>.

Source: the research project's rating output, ~/dev/weather_football/data/processed/GALLERY/ratings_<season>.json
(Match Entertainment Rating, method and calibration frozen there). Nothing is rated or recomputed here: every star,
score and label is copied from that output. The build stops if the export disagrees with its source.

Writes
  football/data/gallery/index.json        seasons available, default season, versions
  football/data/gallery/<season>.json     one compact record per rated match + the unrated matches (no ratings)
  football/gallery/index.html             the gallery shell; football/js/gallery.js renders the matches
  football/gallery/match/<id>.html        one static page per match (rated: full explanation; unrated: the reason)
  football/gallery/match-not-found.html   served for unknown match ids (vercel.json rewrite)
  sitemap-gallery.xml                     rated match pages (unrated and not-found pages are noindex)

    python3 scripts/build_gallery.py [path/to/GALLERY]
"""
import html
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402
import gallery_pages  # noqa: E402

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "dev/weather_football/data/processed/GALLERY")
FB = Path(__file__).resolve().parent.parent / "football"
OUT = FB / "data" / "gallery"
PATH = "/football/gallery"
SEASONS = ["2026", "2025"]          # newest first; 2026 = 2026/27 is the default
DEFAULT = "2026"
METHOD, CALIBRATION = "mer-1.0.0", "cal-2025-v1"
CRESTS_FILE = FB / "data" / "gallery" / "crests.json"   # written by scripts/fetch_club_crests.py
gallery_pages.CRESTS = set(json.loads(CRESTS_FILE.read_text())) if CRESTS_FILE.exists() else set()   # the frozen M1 versions this page was built for
COMP_ORDER = ["EPL", "La_Liga", "Serie_A", "Bundesliga", "Ligue_1", "UCL", "UEL", "UECL"]
COMP_SHORT = {"EPL": "PL", "La_Liga": "LL", "Serie_A": "SA", "Bundesliga": "BL", "Ligue_1": "L1",
              "UCL": "UCL", "UEL": "UEL", "UECL": "UECL"}
LABEL_ORDER = ["Thriller", "Late Drama", "Comeback", "Goal Fest", "Upset", "Hidden Gem", "Chaos", "One-Sided"]
esc = html.escape


def fail(msg):
    sys.exit(f"build_gallery: {msg}")


def kickoff_iso(s):
    """Normalise the two source formats ('2026-10-12 19:00:00+00:00', '2026-09-08T16:45Z') to 'YYYY-MM-DDTHH:MMZ'."""
    if not s:
        return None
    s = s.replace(" ", "T")
    return s[:16] + "Z" if len(s) >= 16 else None


def export_season(season):
    src = json.loads((SRC / f"ratings_{season}.json").read_text())
    meta, rated, unrated = src["meta"], src["matches"], src["unrated"]
    if (meta["method_version"], meta["calibration_version"]) != (METHOD, CALIBRATION):
        fail(f"{season}: source is {meta['method_version']}/{meta['calibration_version']}, page expects {METHOD}/{CALIBRATION}")
    keys = Counter(m["match_key"] for m in rated + unrated)
    if any(n > 1 for n in keys.values()):
        fail(f"{season}: duplicate match keys {[k for k, n in keys.items() if n > 1][:3]}")
    if len(rated) != meta["counts"]["rated"] or len(unrated) != meta["counts"]["unrated"]:
        fail(f"{season}: counts disagree with the source meta")
    rows = []
    for m in rated:
        if not m["rated"] or m["season"] != season or m["eligibility"] != "rateable":
            fail(f"{season}: {m['match_key']} is in the rated list but not rated for this season")
        if m["method_version"] != METHOD or m["calibration_version"] != CALIBRATION:
            fail(f"{season}: {m['match_key']} carries a different method or calibration version")
        sc = m["score"]
        labels = sorted((x["label"] for x in m["labels"]), key=LABEL_ORDER.index)
        rows.append({
            "k": m["match_key"], "u": gallery_pages.match_id(m["match_key"]), "c": m["competition"], "d": m["date"], "t": kickoff_iso(m.get("kickoff_utc")),
            "h": m["home"], "a": m["away"], "hc": m["home_club_id"], "ac": m["away_club_id"], "hg": sc["home"], "ag": sc["away"],
            "aet": sc["aet"] or None, "so": sc["shootout"], "fl": sc["first_leg"],
            "st": m["stars"], "sc": m["match_score"], "lb": labels,
            "p": m["quality"]["missing_inputs"] if m["quality"]["partial"] else None,
        })
    un = [{"k": m["match_key"], "u": gallery_pages.match_id(m["match_key"]), "c": m["competition"], "d": m["date"], "h": m["home"], "a": m["away"],
           "why": m["eligibility"].split(":", 1)[1]} for m in unrated]
    comps = [c for c in COMP_ORDER if any(r["c"] == c for r in rows)]
    label_counts = Counter(x for r in rows for x in r["lb"])
    out_meta = {
        "season": season, "season_label": meta["season_label"], "default": season == DEFAULT,
        "generated_utc": meta["generated_at_utc"], "method_version": METHOD, "calibration_version": CALIBRATION,
        "rated": len(rows), "partial": sum(r["p"] is not None for r in rows), "unrated": len(un),
        "first_date": min((r["d"] for r in rows), default=None), "last_date": max((r["d"] for r in rows), default=None),
        "competitions": [{"code": c, "name": next(m["competition_name"] for m in rated if m["competition"] == c),
                          "short": COMP_SHORT[c], "n": sum(r["c"] == c for r in rows)} for c in comps],
        "labels": [{"label": k, "rule": meta["label_rules"][k], "n": label_counts[k]} for k in LABEL_ORDER if label_counts[k]],
        "uefa_source": meta["sources"]["uefa"],
        # canonical club id -> club name (M4 club view); one name per id is checked in the research build
        "clubs": dict(sorted({m[f"{sd}_club_id"]: m[f"{sd}_club"] for m in rated for sd in ("home", "away")}.items())),
        "crests": sorted(gallery_pages.CRESTS & {m[f"{sd}_club_id"] for m in rated + unrated for sd in ("home", "away")}),
    }
    doc = {"meta": out_meta, "matches": rows, "unrated": un}
    # guard: the export says exactly what the source says
    by_key = {m["match_key"]: m for m in rated}
    for r in rows:
        s = by_key[r["k"]]
        if (r["st"], r["sc"], r["hg"], r["ag"], r["d"], r["c"]) != (s["stars"], s["match_score"], s["score"]["home"],
                                                                       s["score"]["away"], s["date"], s["competition"]):
            fail(f"{r['k']}: export differs from source")
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{season}.json"
    path.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False))
    print(f"gallery/{season}.json  {len(rows)} rated, {len(un)} unrated, {path.stat().st_size / 1024:.0f} KB")
    return out_meta, rated, unrated, meta["label_rules"]


def write_if_changed(path, text):
    if path.exists() and path.read_text() == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return True


def export_insights(season, rated):
    """M4: copy the research build's season rankings and club insights (insights_<season>.json) into two page files.
    Values are copied as-is; the guards only check the file belongs to this season and these ratings."""
    ins = json.loads((SRC / f"insights_{season}.json").read_text())
    m = ins["meta"]
    if (m["season"], m["method_version"], m["calibration_version"]) != (season, METHOD, CALIBRATION):
        fail(f"insights_{season}.json is for {m['season']} / {m['method_version']} / {m['calibration_version']}")
    keys = {r["match_key"] for r in rated}
    for name, sc in ins["scopes"].items():
        refs = [x for lst in sc["lists"].values() for x in lst["shown"]] + [c["best"] for c in sc["clubs"]]
        if any(x["k"] not in keys for x in refs):
            fail(f"insights_{season} scope {name} refers to a match that is not a rated {season} match")
        if name != "all" and any(x["c"] != name for x in refs):
            fail(f"insights_{season} scope {name} contains another competition's match")
        for b in sc["leaderboards"].values():
            if any(r["n"] < b["threshold"] for r in b["rows"]) or any(x["n"] >= b["threshold"] for x in b["below"]):
                fail(f"insights_{season} scope {name}: a leaderboard breaks its own threshold")
    for x in (r for sc in ins["scopes"].values() for lst in sc["lists"].values() for r in lst["shown"]):
        x["u"] = gallery_pages.match_id(x["k"])
    for sc in ins["scopes"].values():
        for c in sc["clubs"]:
            c["best"]["u"] = gallery_pages.match_id(c["best"]["k"])
    m = dict(m, crests=sorted(gallery_pages.CRESTS))
    rank = {"meta": m, "scopes": {k: {kk: v[kk] for kk in ("competition", "rated", "partial", "unrated", "lists")}
                                  for k, v in ins["scopes"].items()}}
    club = {"meta": m, "scopes": {k: {kk: v[kk] for kk in ("competition", "rated", "partial", "unrated", "clubs",
                                                           "leaderboards")} for k, v in ins["scopes"].items()}}
    for name, doc in (("rankings", rank), ("clubs", club)):
        path = OUT / f"{name}_{season}.json"
        path.write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False))
        print(f"gallery/{name}_{season}.json  {path.stat().st_size / 1024:.0f} KB")


exports = [export_season(s) for s in SEASONS]
metas = [e[0] for e in exports]
for s_, e in zip(SEASONS, exports):
    export_insights(s_, e[1])

# ---------------------------------------------------------------- match pages (M3)
MATCH_DIR = FB / "gallery" / "match"
pages, sitemap = {}, []
for meta, rated, unrated, rules in exports:
    for r in rated:
        mid, doc = gallery_pages.render_match(r, rules)
        pages[mid] = doc
        sitemap.append((mid, r["rated_at_utc"][:10]))
    for r in unrated:
        mid, doc = gallery_pages.render_unrated(r)
        pages[mid] = doc
ids = list(pages)
if len(ids) != sum(len(e[1]) + len(e[2]) for e in exports):
    fail("two matches map to the same page id")
if any(not all(ch.isalnum() and ch.islower() or ch.isdigit() or ch == "-" for ch in i) for i in ids):
    fail("a match id contains characters outside a-z, 0-9 and '-'")
changed = sum(write_if_changed(MATCH_DIR / f"{mid}.html", doc) for mid, doc in pages.items())
stale = [p for p in MATCH_DIR.glob("*.html") if p.stem not in pages]
for p in stale:
    p.unlink()
write_if_changed(FB / "gallery" / "match-not-found.html", gallery_pages.render_not_found())
print(f"gallery/match/: {len(pages)} pages ({changed} written, {len(stale)} removed)")
sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
sm += [f"  <url><loc>{fb_chrome.SITE}/football/gallery/match/{mid}</loc><lastmod>{d}</lastmod></url>"
       for mid, d in sorted(sitemap)]
write_if_changed(FB.parent / "sitemap-gallery.xml", "\n".join(sm + ["</urlset>", ""]))
index = {"default": DEFAULT, "method_version": METHOD, "calibration_version": CALIBRATION,
         "seasons": [{"season": m["season"], "label": m["season_label"], "rated": m["rated"],
                      "last_date": m["last_date"], "archive": m["season"] != DEFAULT} for m in metas]}
(OUT / "index.json").write_text(json.dumps(index, separators=(",", ":")))

# ---------------------------------------------------------------- page shells
def subnav(active):
    """Matches · Rankings · Clubs inside the gallery. Links keep the season (and competition) via gallery-subnav JS."""
    items = [("matches", "/football/gallery", "Matches"), ("rankings", "/football/gallery/rankings", "Rankings"),
             ("clubs", "/football/gallery/clubs", "Clubs")]
    lis = "".join(f'<li><a href="{href}" data-subnav="{key}"{" aria-current=\"page\"" if key == active else ""}>{lab}</a></li>'
                  for key, href, lab in items)
    return f'<nav class="gx-subnav wrap" aria-label="Match Gallery"><ul>{lis}</ul></nav>'


def controls(include_sort=False):
    return """<form class="gi-controls" id="gi-controls" aria-label="Season and competition" novalidate>
    <div class="field"><label class="label" for="gi-season">Season</label><select class="input" id="gi-season" name="season"></select></div>
    <div class="field"><label class="label" for="gi-comp">Competition</label><select class="input" id="gi-comp" name="comp"><option value="">All competitions</option></select></div>
  </form>"""


def insights_page(kind):
    path = f"/football/gallery/{kind}"
    if kind == "rankings":
        title, h1, lede = ("Season Rankings — Football Match Gallery", "Season rankings",
                           "The season’s matches, ranked by their stored ratings and match facts.")
        desc = ("The best, highest-scoring, closest, most dramatic and most one-sided matches of the season across "
                "Europe’s top five leagues and the Champions, Europa and Conference Leagues.")
    else:
        title, h1, lede = ("Club Insights — Football Match Gallery", "Club insights",
                           "Which clubs’ matches are the most entertaining, chaotic, dramatic or one-sided.")
        desc = ("Average match ratings and match-type rates for every club, with sample sizes. Describes the matches "
                "a club played in, not the club’s quality.")
    ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": h1, "url": fb_chrome.SITE + path,
          "description": desc, "isPartOf": {"@id": "https://iyush.dev/football#site"}}
    body = f"""<main id="main" class="gx gi" data-insights="{kind}">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li><a href="/football/gallery">Match Gallery</a></li><li aria-current="page">{h1.capitalize()}</li></ol></nav>
{subnav(kind)}
<section class="gx-hero wrap" aria-labelledby="gi-title">
  <div class="gx-hero__text">
    <p class="eyebrow">Match Gallery <b>·</b> <span id="gi-context">Loading…</span></p>
    <h1 id="gi-title">{h1}</h1>
    <p class="lede">{lede}</p>
  </div>
</section>
<section class="wrap gi-top">
  {controls()}
  <p class="gi-coverage" id="gi-coverage" aria-live="polite"></p>
</section>
<div class="wrap" id="gi-results" aria-busy="true">
  <div class="state gx-loading" role="status"><p class="state__t">Loading</p><p>Fetching the season’s rankings…</p></div>
</div>
<noscript><div class="wrap"><div class="state state--empty"><p class="state__t">JavaScript needed</p><p>This page builds its tables in your browser. Turn on JavaScript to see them.</p></div></div></noscript>
</main>
<script src="/football/js/gallery-insights.js" defer></script>"""
    doc = (fb_chrome.head(path, title, desc, h1, "gallery.png", ld, og_type="website", crumb_name=h1.capitalize())
           + "\n<body>\n" + fb_chrome.header(path) + "\n\n" + body + "\n\n" + fb_chrome.footer(datetime.now().strftime("%-d %b %Y"))
           + "\n</body>\n</html>\n")
    write_if_changed(FB / "gallery" / f"{kind}.html", doc)
    print(f"football/gallery/{kind}.html")


insights_page("rankings")
insights_page("clubs")
cur = next(m for m in metas if m["season"] == DEFAULT)
DESC = ("Every match in the Premier League, La Liga, Serie A, Bundesliga, Ligue 1 and the Champions, Europa and "
        "Conference Leagues, rated 1–5 stars for entertainment. Find the ones worth watching.")
LD = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "Football Match Gallery",
      "url": fb_chrome.SITE + PATH, "description": DESC, "isPartOf": {"@id": "https://iyush.dev/football#site"},
      "author": {"@id": "https://iyush.dev/#person"}}
season_opts = "".join(f'<option value="{m["season"]}"{" selected" if m["season"] == DEFAULT else ""}>'
                      f'{esc(m["season_label"])}{" · archive" if m["season"] != DEFAULT else ""}</option>' for m in metas)

body = f"""<main id="main" class="gx">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li aria-current="page">Match Gallery</li></ol></nav>
{subnav("matches")}

<section class="gx-hero wrap" aria-labelledby="gx-title">
  <div class="gx-hero__text">
    <p class="eyebrow">Match Gallery <b>·</b> <span id="gx-eyebrow-season">{esc(cur["season_label"])}</span></p>
    <h1 id="gx-title">Football Match Gallery</h1>
    <p class="lede">Every match tells a story. Find the ones worth watching.</p>
  </div>
  <div class="gx-season field">
    <label class="label" for="gx-season">Season</label>
    <select class="input" id="gx-season" name="season">{season_opts}</select>
  </div>
</section>

<section class="gx-featured wrap" aria-labelledby="gx-feat-h">
  <div class="gx-sechead">
    <h2 id="gx-feat-h" class="gx-h2">Top of the season</h2>
    <p class="gx-sub" id="gx-feat-sub">The highest-rated matches so far.</p>
  </div>
  <ol class="gx-feat" id="gx-feat" aria-live="polite"></ol>
</section>

<section class="gx-browse wrap" aria-labelledby="gx-all-h">
  <div class="gx-sechead">
    <h2 id="gx-all-h" class="gx-h2">All matches</h2>
  </div>
  <form class="gx-controls" id="gx-controls" aria-label="Sort and filter matches" novalidate>
    <div class="field gx-f-sort">
      <span class="label" id="gx-sort-l">Sort</span>
      <div class="seg" role="group" aria-labelledby="gx-sort-l">
        <button type="button" data-sort="rating" aria-pressed="true">Highest rated</button>
        <button type="button" data-sort="recent" aria-pressed="false">Most recent</button>
      </div>
    </div>
    <div class="field">
      <label class="label" for="gx-comp">Competition</label>
      <select class="input" id="gx-comp" name="comp"><option value="">All competitions</option></select>
    </div>
    <div class="field">
      <label class="label" for="gx-label">Match type</label>
      <select class="input" id="gx-label" name="label"><option value="">All match types</option></select>
    </div>
    <div class="field gx-f-dates">
      <span class="label" id="gx-dates-l">Played between</span>
      <div class="gx-dates" role="group" aria-labelledby="gx-dates-l">
        <input class="input" type="date" id="gx-from" name="from" aria-label="From date" />
        <span aria-hidden="true">–</span>
        <input class="input" type="date" id="gx-to" name="to" aria-label="To date" />
      </div>
    </div>
  </form>
  <div class="gx-active" id="gx-active" hidden>
    <ul class="gx-chips" id="gx-chips" aria-label="Active filters"></ul>
    <button type="button" class="gx-clear" id="gx-clear">Clear all</button>
  </div>
  <p class="gx-count" id="gx-count" role="status" aria-live="polite"></p>
  <div id="gx-results" aria-busy="true">
    <div class="state gx-loading" role="status"><p class="state__t">Loading matches</p><p>Fetching the season's ratings…</p></div>
  </div>
  <div class="gx-more" id="gx-more" hidden><button type="button" class="btn btn--ghost" id="gx-more-btn">Show more matches</button></div>
  <noscript><div class="state state--empty"><p class="state__t">JavaScript needed</p><p>The gallery filters the season's ratings in your browser. Turn on JavaScript to browse the matches.</p></div></noscript>
</section>

<section class="gx-about wrap" aria-labelledby="gx-about-h">
  <h2 id="gx-about-h" class="gx-h3">About the ratings</h2>
  <div class="gx-about__body">
    <p>Each completed match gets 1 to 5 stars from what happened in it: goals and shots on target, how long the score stayed close, and late goals, comebacks, equalisers, red cards and penalties. It measures entertainment, not football quality, and it is the same formula for every competition. xG is not part of the rating.</p>
    <p>A <span class="gx-partial-inline">partial</span> rating means an input was missing for that match and the rating uses what was available. Matches that were postponed, or where the sources disagree on the result, are listed without a rating.</p>
    <p class="gx-meta-line" id="gx-meta-line">Rating method {METHOD} · calibration {CALIBRATION} (2025/26, frozen).</p>
    <p class="gx-meta-line">Data: Understat and football-data.co.uk (domestic leagues), ESPN (Champions, Europa and Conference Leagues; qualifying rounds not included). {gallery_pages.CREST_NOTE}</p>
  </div>
  <details class="gx-unrated" id="gx-unrated" hidden><summary id="gx-unrated-sum"></summary><ul id="gx-unrated-list"></ul></details>
</section>
</main>
<script src="/football/js/gallery.js" defer></script>"""

updated = datetime.now().strftime("%-d %b %Y")
doc = (fb_chrome.head(PATH, "Football Match Gallery — The Season's Most Entertaining Matches", DESC,
                      "Football Match Gallery", "gallery.png", LD, og_type="website")
       + "\n<body>\n" + fb_chrome.header(PATH) + "\n\n" + body + "\n\n" + fb_chrome.footer(updated) + "\n</body>\n</html>\n")
write_if_changed(FB / "gallery" / "index.html", doc)
print("football/gallery/index.html")
