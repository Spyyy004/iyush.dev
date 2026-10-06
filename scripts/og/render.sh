#!/bin/sh
# Regenerate football/og/*.png from card.html. Needs a clean-URL server on :4601 at the repo root (npx serve -l 4601 .).
set -e
cd "$(dirname "$0")/../.."
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
mkdir -p football/og
enc() { python3 -I -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1]))' "$1"; }
card() { # name kicker title subtitle
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=6000 --window-size=1200,630 \
    --screenshot="$PWD/football/og/$1.png" "http://localhost:4601/scripts/og/card?k=$(enc "$2")&t=$(enc "$3")&s=$(enc "$4")" 2>/dev/null
  echo "football/og/$1.png"
}
card home "Football research · 01—05" "What actually belongs to the player?" "Five studies on 525K player-matches from Europe's top five leagues."
card research "Research · 01—05" "Five studies, one dataset" "Environment → Home → Opponent → Similarity → Transferability."
card environment "Study 01 · Environment" "Does the environment change player performance?" "Mostly no. Weather barely matters; crowds clearly do. Weather confirmation pending."
card home-advantage "Study 02 · Home advantage" "Everyone gets better at home." "+27% xG per minute for the same player. 0 of 4,665 players have a reliable personal home edge."
card opposition "Study 03 · Opposition" "There aren't reliable “big-game players.”" "−14% xG per +1 SD of opponent strength. 0 of 23,022 estimates show reliable resistance."
card similarity-study "Study 04 · Similarity" "Bruno doesn't have a statistical twin in Serie A." "Chance creation 3.6 SD above his role average; Serie A's best is 1.9."
card transferability "Study 05 · Transferability" "Will his game travel?" "Similarity adds +0.000 to the forecast. Player history does the work."
card tools "Tools" "Interact with the models" "Player similarity across leagues and a validated transfer calculator."
card similarity-tool "Tool · Player similarity" "Who plays like Bruno?" "Context-adjusted profiles, compared within a role, in any league."
card transfer-calculator "Tool · Transfer calculator" "Will his game travel?" "Expected output, retention and an 80% range for any forward or midfielder."
card live "Live tracker" "Does the research still hold?" "Re-tested every week on seasons the studies never saw."
# Case study (M7 §24): its own template, values read from the locked board export.
CASE_Q=$(python3 -I -c 'import json,urllib.parse as u;B={r["player"]:r for r in json.load(open("football/data/case-study.json"))["board"]}
print("&".join("r="+u.quote(f"{n.split()[-1]}|{B[n]['pred']:.2f}|{B[n]['actual_xgxa90']:.2f}|{int(B[n]['q10']<=B[n]['actual_xgxa90']<=B[n]['q90'])}") for n in ("Joshua Zirkzee","Manuel Ugarte")))')
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --virtual-time-budget=6000 --window-size=1200,630 \
  --screenshot="$PWD/football/og/manchester-united-2024.png" "http://localhost:4601/scripts/og/card-case?$CASE_Q" 2>/dev/null
echo football/og/manchester-united-2024.png
card glossary "Glossary" "Football analytics, in plain English" "xG, shrinkage, leakage, retention — what they mean and why we use them."
card methodology "Methodology" "How do we know?" "Within-player comparisons, signal vs noise, 155,282 leakage checks, locked test seasons."
card about "About" "I'm Ayush." "Product engineer by trade, football obsessive by choice."
