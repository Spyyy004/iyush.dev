#!/usr/bin/env python3
"""Propose club colours for the Match Gallery posters (scripts/club_colours.csv).

One row per club in the research project's data/processed/GALLERY/clubs.json. For each club it reads ESPN's team
colours (primary and alternate) and the dominant colour of the club's crest (football/crests/<club>.png), then picks
the first usable one as `primary` and the next distinct one as `secondary`. Black-and-white kits keep their mono
colour (`source` ends in "-mono"); the build paints those as warm greys.

The CSV is reviewed by hand. Rows marked `checked` = yes (or edited, with `source` = manual) are never overwritten;
re-running only adds clubs that are not in the file yet. Colours are display-only: they never touch a rating.

    python3 scripts/build_club_colours.py [path/to/GALLERY]        # needs Pillow for the crest fallback
"""
import colorsys
import csv
import json
import sys
import time
import urllib.request
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "dev/weather_football/data/processed/GALLERY")
ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "scripts" / "club_colours.csv"
CRESTS = ROOT / "football" / "crests"
API = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/teams/{id}"
FIELDS = ["club_id", "name", "primary", "secondary", "source", "checked", "espn_primary", "espn_alternate", "crest"]


def hls(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return colorsys.rgb_to_hls(r, g, b)


def norm(c):
    c = (c or "").strip().lstrip("#")
    return "#" + c.lower() if len(c) == 6 and all(ch in "0123456789abcdefABCDEF" for ch in c) else ""


def usable(c):
    """A colour that reads as the club's colour on a poster: not white, black or grey."""
    if not c:
        return False
    h, l, s = hls(c)
    return s >= 0.25 and 0.12 <= l <= 0.82


def distinct(a, b):
    ra, rb = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return sum((x - y) ** 2 for x, y in zip(ra, rb)) ** 0.5 >= 110


def espn_colours(espn_id):
    try:
        req = urllib.request.Request(API.format(id=espn_id), headers={"User-Agent": "iyush.dev-site-build/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            t = json.load(r).get("team", {})
        time.sleep(0.15)
        return norm(t.get("color")), norm(t.get("alternateColor"))
    except Exception:
        return "", ""


def crest_colour(club_id):
    """The most common saturated colour in the crest (transparent, white, black and grey pixels ignored)."""
    try:
        from PIL import Image
        im = Image.open(CRESTS / f"{club_id.replace(':', '-')}.png").convert("RGBA").resize((48, 48))
    except Exception:
        return ""
    counts = {}
    px = im.get_flattened_data() if hasattr(im, "get_flattened_data") else im.getdata()
    for r, g, b, a in px:
        if a < 200:
            continue
        h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        if l > 0.9 or l < 0.08 or s < 0.25:
            continue
        key = (r // 24, g // 24, b // 24)
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return ""
    k = max(counts, key=counts.get)
    return "#%02x%02x%02x" % tuple(min(255, v * 24 + 12) for v in k)


def propose(espn_p, espn_a, crest):
    cands = [(espn_p, "espn"), (espn_a, "espn-alt"), (crest, "crest")]
    good = [(c, s) for c, s in cands if usable(c)]
    if good:
        primary, source = good[0]
        rest = [c for c, _ in good[1:] if distinct(c, primary)]
        mono = [c for c in (espn_a, espn_p) if c and not usable(c) and distinct(c, primary)]
        return primary, (rest or mono or [""])[0], source
    mono = [c for c in (espn_p, espn_a) if c]
    if mono:
        sec = next((c for c in mono[1:] if distinct(c, mono[0])), "")
        return mono[0], sec, "espn-mono"
    return "", "", "none"


def main():
    clubs = json.loads((SRC / "clubs.json").read_text())
    rows = {}
    if CSV.exists():
        with CSV.open() as f:
            rows = {r["club_id"]: r for r in csv.DictReader(f)}
    added = 0
    for cid, c in sorted(clubs.items()):
        if cid in rows:
            continue
        ep, ea = espn_colours(c["espn_id"]) if c.get("espn_id") else ("", "")
        cr = crest_colour(cid)
        primary, secondary, source = propose(ep, ea, cr)
        rows[cid] = {"club_id": cid, "name": c["name"], "primary": primary, "secondary": secondary, "source": source,
                     "checked": "", "espn_primary": ep, "espn_alternate": ea, "crest": cr}
        added += 1
    with CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for cid in sorted(rows):
            w.writerow({k: rows[cid].get(k, "") for k in FIELDS})
    by_source = {}
    for r in rows.values():
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
    print(f"club_colours.csv: {len(rows)} clubs ({added} added) · sources {by_source}")


if __name__ == "__main__":
    main()
