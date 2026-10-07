"""Shared page chrome for generated /football pages: <head>, FootballHeader, FootballFooter (M1 §9, §20).

Hand-written pages carry the same markup; keep the two in step if either changes.
"""
import html
import json

SITE = "https://iyush.dev"
FONTS = ("https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1"
         "&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap")
NAV = [("/football/research", "Research"), ("/football/tools", "Tools"), ("/football/live", "Live"),
       ("/football/glossary", "Glossary"), ("/football/methodology", "Methodology"), ("/football/about", "About")]
esc = html.escape


CRUMB = {"football": "Football", "research": "Research", "tools": "Tools", "live": "Live", "glossary": "Glossary", "methodology": "Methodology",
         "about": "About", "case-studies": "Case studies", "environment": "Study 01 · Environment", "home-advantage": "Study 02 · Home advantage",
         "opposition": "Study 03 · Opposition", "similarity": "Similarity", "transferability": "Study 05 · Transferability", "transfer": "Transfer Calculator",
         "manchester-united-2024": "Manchester United 2024"}


def breadcrumbs(path):
    """BreadcrumbList JSON-LD mirroring the visible breadcrumb trail (M9 §15)."""
    parts = [p for p in path.strip("/").split("/") if p]
    items, acc = [], ""
    for p in parts:
        acc += "/" + p
        if p == "case-studies":   # no index page for this segment
            continue
        name = CRUMB.get(p, p)
        if p == "similarity":
            name = "Study 04 · Similarity" if "research" in parts else "Similarity Explorer"
        items.append({"@type": "ListItem", "position": len(items) + 1, "name": name, "item": SITE + acc})
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": items}


def head(path, title, description, og_title, og_image, ld, og_type="article"):
    url = SITE + path
    img = f"{SITE}/football/og/{og_image}"
    t, d, ot = esc(title), esc(description), esc(og_title)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<title>{t}</title>
<meta name="description" content="{d}" />
<link rel="canonical" href="{url}" />
<meta name="author" content="Ayush Pawar" />
<meta name="robots" content="index, follow, max-image-preview:large" />
<meta name="theme-color" content="#0b0b0b" />
<link rel="icon" href="/favicon.ico" sizes="any" />
<link rel="icon" href="/favicon.svg" type="image/svg+xml" />
<link rel="apple-touch-icon" href="/apple-touch-icon.png" />
<meta property="og:type" content="{og_type}" />
<meta property="og:site_name" content="iyush.dev" />
<meta property="og:title" content="{ot}" />
<meta property="og:description" content="{d}" />
<meta property="og:url" content="{url}" />
<meta property="og:image" content="{img}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{ot}" />
<meta name="twitter:description" content="{d}" />
<meta name="twitter:image" content="{img}" />
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
<script type="application/ld+json">{json.dumps(breadcrumbs(path), ensure_ascii=False)}</script>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="{FONTS}" rel="stylesheet" />
<link rel="stylesheet" href="/football/football.css" />
<script>document.documentElement.classList.add("js")</script>
<script src="/football/js/glossary.js" defer></script>
<script src="/football/js/football.js" defer></script>
</head>"""


def header(path):
    lis = []
    for href, lab in NAV:
        cur = ' aria-current="page"' if path == href else (' aria-current="true"' if path.startswith(href + "/") else "")
        lis.append(f'        <li><a href="{href}"{cur}>{lab}</a></li>')
    return """<a class="skip" href="#main">Skip to content</a>

<header class="fhead">
  <div class="wrap">
    <a class="brand" href="/football">Football<span class="brand__by">/ Ayush Pawar</span></a>
    <button class="navbtn" type="button" aria-expanded="false" aria-controls="fnav"><span class="navbtn__t">Menu</span><span class="navbtn__icon" aria-hidden="true"></span></button>
    <nav class="fnav" id="fnav" aria-label="Football">
      <ul>
""" + "\n".join(lis) + """
      </ul>
      <p class="fnav__extra"><a href="/" aria-label="Back to iyush.dev">← iyush.dev</a></p>
    </nav>
  </div>
</header>"""


def footer(updated):
    return f"""<footer class="ffoot">
  <div class="wrap grid">
    <div class="d-6">
      <p class="ffoot__name">Home Turf &amp; Hard Opponents</p>
      <p class="ffoot__by">Football research by Ayush Pawar</p>
    </div>
    <nav class="t-4 d-3" aria-label="Football sections">
      <ul>
        <li><a href="/football/research">Research</a></li>
        <li><a href="/football/tools">Tools</a></li>
        <li><a href="/football/live">Live</a></li>
        <li><a href="/football/methodology">Methodology</a></li>
        <li><a href="/football/glossary">Glossary</a></li>
      </ul>
    </nav>
    <div class="t-4 d-3">
      <ul>
        <li><a href="/">iyush.dev</a></li>
        <li><a href="https://github.com/Spyyy004" rel="me noopener" target="_blank">GitHub</a></li>
        <li><a href="https://www.linkedin.com/in/ayush-pawar004" rel="me noopener" target="_blank">LinkedIn</a></li>
      </ul>
    </div>
    <p class="ffoot__note">Data: Understat, football-data.co.uk and others — see <a href="/football/methodology">methodology</a>. Observational data; effects are associations within matched comparisons.</p>
    <div class="ffoot__meta">
      <p>Data updated: {esc(updated)}</p>
      <p>Frozen dataset: 2015/16 — 2024/25</p>
    </div>
  </div>
</footer>"""
