#!/bin/zsh
# Prepare a reviewable Match Gallery update (gallery M5). Never pushes.
#
#   zsh scripts/prepare_gallery_publish.sh [path/to/GALLERY]
#
# Works in a dedicated git worktree (~/Sites/.iyush-gallery-publish) reset to origin/main, so the main working copy
# (~/Sites/iyush.dev) is never touched. Rebuilds only the gallery's generated files from the research project's
# validated output, runs both page checks, and if the checks pass and anything changed, commits on the local branch
# `gallery-refresh`. Nothing is committed when a check fails or nothing changed.
# To publish after review:  git -C ~/Sites/.iyush-gallery-publish push origin gallery-refresh:main
# Exit codes: 0 prepared or unchanged (see the last line), 1 failed.
set -u
GALLERY=${1:-$HOME/dev/weather_football/data/processed/GALLERY}
SITE=${IYUSH_SITE:-$HOME/Sites/iyush.dev}
WT=${GALLERY_WORKTREE:-$HOME/Sites/.iyush-gallery-publish}
BASE=${GALLERY_BASE:-}   # what the changeset is built on (default below); tests may point it at a local commit
PATHS=(football/gallery football/data/gallery football/crests sitemap-gallery.xml)
PY=/usr/bin/python3
[[ -x /opt/homebrew/bin/python3 ]] && PY=/opt/homebrew/bin/python3

fail() { echo "FAILED: $1"; [[ -d $WT ]] && { git -C $WT reset -q --hard; git -C $WT clean -fdq -- $PATHS; }; exit 1; }

git -C $SITE fetch -q origin main || fail "git fetch origin main (network?)"
# Build on origin/main, unless local main is strictly ahead of it (site code committed but not pushed yet): then on
# main, so the changeset never drops that code. The summary lists those commits, since a push publishes them too.
EXTRA=""
if [[ -z $BASE ]]; then
  BASE=origin/main
  if [[ $(git -C $SITE rev-parse main) != $(git -C $SITE rev-parse origin/main) ]] && git -C $SITE merge-base --is-ancestor origin/main main; then
    BASE=main
    EXTRA=$(git -C $SITE log --format='  %h %s' origin/main..main)
  fi
fi
if [[ ! -d $WT ]]; then
  git -C $SITE worktree add -q --detach $WT $BASE || fail "creating the publish worktree"
fi
git -C $WT checkout -q --detach $BASE 2>/dev/null || fail "checking out $BASE in the worktree"
git -C $WT reset -q --hard $BASE && git -C $WT clean -fdq -- $PATHS

cd $WT || fail "worktree missing"
$PY scripts/fetch_club_crests.py $GALLERY || echo "warning: crest download failed; existing crests kept, new clubs show initials"
$PY scripts/build_gallery.py $GALLERY > /tmp/gallery_build.$$ 2>&1 || { tail -5 /tmp/gallery_build.$$; fail "build_gallery.py"; }
$PY scripts/check_gallery_pages.py $GALLERY || fail "check_gallery_pages.py"
$PY scripts/check_gallery_insights.py || fail "check_gallery_insights.py"

CHANGED=$(git status --porcelain -- $PATHS | wc -l | tr -d ' ')
if [[ $CHANGED == 0 ]]; then
  echo "UNCHANGED: the validated output matches what is already on $BASE; nothing to publish"
  exit 0
fi
STATUS=$GALLERY/status.json
THROUGH=$($PY -c "import json;s=json.load(open('$STATUS'));c=s['current_season'];print(s['seasons'][c]['through'])" 2>/dev/null)
git add -A -- $PATHS
git -c core.hooksPath=/dev/null commit -q -m "data(football): Match Gallery refresh — results through ${THROUGH:-?}" \
  -m "Prepared by scripts/prepare_gallery_publish.sh from validated output; $CHANGED generated files changed." || fail "commit"
git branch -q -f gallery-refresh HEAD
echo "PREPARED: $(git log -1 --format='%h %s') ($(git diff --stat HEAD~1 HEAD | tail -1 | sed 's/^ *//'))"
[[ -n $EXTRA ]] && printf "Also includes unpushed commit(s) from local main:\n%s\n" "$EXTRA"
echo "Review:  git -C $WT log --stat origin/main..gallery-refresh"
echo "Publish: git -C $WT push origin gallery-refresh:main"
