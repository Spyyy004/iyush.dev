#!/usr/bin/env python3
"""Download and resize club crests for the Match Gallery (football/crests/<club>.png, 128 px).

Source: ESPN's public team-logo images (the dark-background variant where ESPN has one, else the standard one), for
every club in the research project's data/processed/GALLERY/clubs.json (club id -> ESPN team id, from the reviewed
club map). Club crests are trademarks of their clubs; the site credits them as such.

Run when new clubs appear (the weekly job can call it; existing crests are not fetched again):
    python3 scripts/fetch_club_crests.py [path/to/GALLERY]
Needs macOS `sips` for resizing. Writes football/data/gallery/crests.json (club ids that have a crest).
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "dev/weather_football/data/processed/GALLERY")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "football" / "crests"
CACHE = ROOT / "scripts" / ".crest_cache"          # full-size downloads (gitignored)
SIZE = 128
URLS = ["https://a.espncdn.com/i/teamlogos/soccer/500-dark/{id}.png", "https://a.espncdn.com/i/teamlogos/soccer/500/{id}.png"]


def slug(club_id):
    return club_id.replace(":", "-")


def download(espn_id):
    for url in URLS:
        dest = CACHE / f"{espn_id}{'-dark' if '500-dark' in url else ''}.png"
        if dest.exists() and dest.stat().st_size > 500:
            return dest
        try:
            req = urllib.request.Request(url.format(id=espn_id), headers={"User-Agent": "iyush.dev-site-build/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            if len(data) > 500 and data[:8] == b"\x89PNG\r\n\x1a\n":
                dest.write_bytes(data)
                time.sleep(0.2)
                return dest
        except Exception:
            pass
    return None


def main():
    clubs = json.loads((SRC / "clubs.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    have, missing, made = [], [], 0
    for cid, c in clubs.items():
        target = OUT / f"{slug(cid)}.png"
        if not target.exists():
            src = download(c["espn_id"]) if c.get("espn_id") else None
            if not src:
                missing.append(f"{cid} {c['name']}")
                continue
            subprocess.run(["sips", "-Z", str(SIZE), str(src), "--out", str(target)], check=True, capture_output=True)
            made += 1
        have.append(cid)
    (ROOT / "football" / "data" / "gallery" / "crests.json").write_text(json.dumps(sorted(have), separators=(",", ":")))
    print(f"crests: {len(have)} of {len(clubs)} clubs ({made} new); without a crest: {missing or 'none'}")


if __name__ == "__main__":
    main()
