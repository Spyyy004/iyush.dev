#!/usr/bin/env python3
"""Copy the shared header (scripts/fb_chrome.py) into the hand-written /football pages, so the nav can't drift.

    python3 scripts/sync_chrome.py

Generated pages get the header from fb_chrome directly; this covers the rest. Fails if a page has no header block.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402

FB = Path(__file__).resolve().parent.parent / "football"
PAGES = {"index.html": "/football", "about.html": "/football/about", "tools/index.html": "/football/tools"}
for f, path in PAGES.items():
    p = FB / f
    s = p.read_text()
    new, n = re.subn(r'<a class="skip" href="#main">Skip to content</a>\s*(?:<!--.*?-->\s*)?<header class="fhead">.*?</header>', lambda m: fb_chrome.header(path), s, count=1, flags=re.S)
    if n != 1:
        sys.exit(f"sync_chrome: no header block in football/{f}")
    if path != "/football":   # BreadcrumbList JSON-LD, same as generated pages (M9 §15)
        crumb = f'<script type="application/ld+json" id="ld-crumbs">{json.dumps(fb_chrome.breadcrumbs(path), ensure_ascii=False)}</script>'
        new = re.sub(r'<script type="application/ld\+json" id="ld-crumbs">.*?</script>\n?', "", new, flags=re.S)
        new = new.replace("</head>", crumb + "\n</head>", 1)
    p.write_text(new)
    print(f"football/{f}: header synced")
