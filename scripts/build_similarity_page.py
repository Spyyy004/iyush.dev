#!/usr/bin/env python3
"""Render the static shell of /football/tools/similarity (M3). The explorer itself is football/js/similarity.js,
reading the precomputed Study 4 results written by scripts/build_similarity.py.

    python3 scripts/build_similarity_page.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402

FB = Path(__file__).resolve().parent.parent / "football"
META = json.loads((FB / "data/meta.json").read_text())
SIM = json.loads((FB / "data/sim/meta.json").read_text())
PATH = "/football/tools/similarity"
LEAGUES = [("EPL", "Premier League"), ("La_Liga", "La Liga"), ("Serie_A", "Serie A"), ("Bundesliga", "Bundesliga"), ("Ligue_1", "Ligue 1")]

DESC = ("Find players with similar context-adjusted attacking profiles across Europe's top five leagues — and see why they "
        "match and where they don't. Study 4's similarity model, precomputed.")
ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": "Similarity Explorer · Home Turf & Hard Opponents",
      "url": fb_chrome.SITE + PATH, "applicationCategory": "SportsApplication", "operatingSystem": "Any", "description": DESC,
      "isPartOf": {"@id": "https://iyush.dev/football#site"}, "author": {"@id": "https://iyush.dev/#person"}}

opts = "".join(f'<option value="{c}"{" selected" if c == "Serie_A" else ""}>{n}</option>' for c, n in LEAGUES)
wins = "".join(f'<button type="button" data-n="{n}" aria-pressed="{"true" if n == 3 else "false"}">{n} season{"s" if n > 1 else ""}<small></small></button>'
               for n in (1, 2, 3))

body = f"""<main id="main">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li><a href="/football/tools">Tools</a></li><li aria-current="page">Similarity</li></ol></nav>

<section class="sx-hero wrap" aria-labelledby="sx-title">
  <p class="eyebrow">Tool <b>·</b> Study 04</p>
  <h1 id="sx-title">Who plays like him?</h1>
  <p class="lede">Find players with similar adjusted attacking profiles across European leagues.</p>
  <p class="sx-note">Similarity is based on nine attacking dimensions adjusted for opponent, venue and league, normalized within role.</p>
</section>

<section class="wrap" aria-label="Find similar players">
  <form class="sx-form" id="q-form" data-step="1" novalidate>
    <p class="wz-count label" id="wz-count" aria-live="polite">Step 1 / 3</p>
    <div class="wz-step is-current" data-n="1">
      <div class="field combo">
        <label class="label" for="q-player">Player</label>
        <input class="input" id="q-player" type="text" autocomplete="off" placeholder="Finding players…" disabled aria-describedby="q-count q-player-err" />
        <p class="field__err" id="q-player-err" hidden>Select a player to continue.</p>
        <p class="sx-hint" id="q-count"></p>
      </div>
      <div class="wz-nav"><button type="button" class="btn" data-next>Next <span class="arr" aria-hidden="true">→</span></button></div>
    </div>
    <div class="wz-step" data-n="2">
      <div class="field">
        <label class="label" for="q-league">Destination league <button type="button" class="term term--ico" data-term="destination-league" aria-label="Why destination league matters"></button></label>
        <select class="input" id="q-league">{opts}</select>
      </div>
      <div class="wz-nav"><button type="button" class="btn btn--ghost" data-prev><span aria-hidden="true">←</span> Back</button><button type="button" class="btn" data-next>Next <span class="arr" aria-hidden="true">→</span></button></div>
    </div>
    <div class="wz-step" data-n="3">
      <div class="field">
        <span class="label" id="q-window-l">Profile window</span>
        <div class="seg sx-seg" id="q-window" role="group" aria-labelledby="q-window-l">{wins}</div>
        <p class="sx-hint">Longer profiles reduce the influence of short-term variation.</p>
      </div>
      <div class="wz-nav"><button type="button" class="btn btn--ghost" data-prev><span aria-hidden="true">←</span> Back</button></div>
    </div>
    <div class="sx-go"><button type="submit" class="btn">Find similar players <span class="arr" aria-hidden="true">→</span></button></div>
  </form>
</section>

<section class="wrap sx-results" id="results" aria-label="Similarity results">
  <div id="sx-out" aria-live="polite">
    <div class="sx-empty"><p class="sx-empty__t">Find a player to begin.</p><p>The model compares adjusted attacking profiles across European leagues.</p>
    <p class="sx-hint">Try <a href="?player=bruno-fernandes&amp;league=serie-a&amp;seasons=3">Bruno Fernandes → Serie A</a>.</p></div>
  </div>
</section>

<section class="section sx-more" aria-labelledby="m-h">
  <div class="wrap grid">
    <div class="d-6">
      <h2 class="h2-sm" id="m-h">How similarity is calculated</h2>
      <ol class="flow flow--v sx-flow" aria-label="Method in steps"><li>9 metrics</li><li>Context adjustment</li><li>Role normalization</li><li>Cosine similarity</li><li>Ranked profiles</li></ol>
      <div class="acc"><details><summary><span class="label">Technical detail</span><span class="acc__h">The Study 4 engine</span></summary><div class="acc__body">
        <p><b>Profile.</b> Nine metrics: {{xa|xA}}, {{key-passes|key passes}}, {{xgchain|xGChain}}, {{xgbuildup|xGBuildup}}, {{npxg|non-penalty xG}}, shots per 90, headed share, in-box share and {{xg-per-shot|xG per shot}} — adjusted for opponent, venue and league environment (not own-team strength), shrunk toward the role average, then {{z-score|z-scored}} within the role.</p>
        <p><b>Roles.</b> Seven, from the data: Understat's granular positions clustered on per-90 output. The labels are the research's own. Candidates are compared only with players in the same role.</p>
        <p><b>Ranking.</b> {{cosine-similarity|Cosine similarity}} and Euclidean distance under four profile windows (one, two and three seasons, and the latest 2,500 minutes) — eight checks. A match is <b>robust</b> when it is in the top 10 and closer than 90% of the pool under at least two-thirds of them. Results list robust matches first, then by the median similarity score in your chosen window.</p>
        <p><b>Profile similarity</b> = closer to the player than that share of the destination pool (0–100). It is a rank, not a probability and not a rating.</p>
        <p><b>Match language</b> uses the Study 4 case study's thresholds: a metric gap of ≤ {SIM["rules"]["similar"]} SD is a strong match, ≤ {SIM["rules"]["moderate"]} SD moderate, larger a divergence; a group is “closest” at a mean gap ≤ {SIM["rules"]["group_close"]} SD and “higher/lower” beyond {SIM["rules"]["group_diff"]} SD.</p>
        <p><b>Precomputed.</b> Every player × league × window was run through the research engine ({SIM["engine"]}); this page only looks results up. Profiles as of {SIM["season"]}; pools need at least {SIM["min_minutes"]} minutes. Validated by {{self-retrieval|self-retrieval}}: three-season profiles find the same player in the top 9% of a destination pool after a real league move.</p>
      </div></details></div>
      <p style="margin-top:20px"><a class="link-arrow" href="/football/research/similarity">Read Study 04 <span class="arr" aria-hidden="true">→</span></a></p>
    </div>
    <div class="d-5 d-end">
      <h2 class="h2-sm">What the model doesn't know</h2>
      <div class="sx-knows">
        <div><p class="label">The model sees</p><ul><li>Attacking output</li><li>Chance creation</li><li>Shooting profile</li><li>Involvement</li><li>Profile shape</li></ul></div>
        <div><p class="label">The model does not see</p><ul class="sx-not"><li>Defensive actions</li><li>Completed passes</li><li>Carries</li><li>Possession</li><li>Injuries</li><li>Transfer fees</li><li>Contracts</li></ul></div>
      </div>
      <p class="prov"><span class="label">Source</span>Understat player-match data · Study 4 similarity engine · profiles {SIM["season"]}<br><span class="label">Players</span>{SIM["players"]:,} with ≥ {SIM["min_minutes"]} minutes in at least one window</p>
    </div>
  </div>
</section>
</main>

<script src="/football/js/similarity.js" defer></script>"""

# inline glossary markup → term buttons (same syntax as content/research.json)
import re  # noqa: E402
body = re.sub(r"\{([a-z0-9-]+)\|([^}]+)\}", r'<button type="button" class="term" data-term="\1">\2</button>', body)

updated = datetime.fromisoformat(META["tracker_generated_utc"]).strftime("%b %Y")
doc = (fb_chrome.head(PATH, "Similarity Explorer · Who plays like him? · Home Turf & Hard Opponents", DESC, "Who plays like him?",
                      "similarity-tool.png", ld, "website")
       + "\n<body>\n" + fb_chrome.header(PATH) + "\n\n" + body + "\n\n" + fb_chrome.footer(updated) + "\n</body>\n</html>\n")
(FB / "tools/similarity.html").write_text(doc)
print("tools/similarity.html", f"{len(doc) / 1024:.1f} KB")
