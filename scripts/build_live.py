#!/usr/bin/env python3
"""Build the live research snapshot and /football/live from the weekly pipeline's outputs (M6).

    python3 scripts/build_live.py                      # normal weekly rebuild
    python3 scripts/build_live.py --init-frozen        # (re)write the frozen-baseline manifest — only for a published correction
    python3 scripts/build_live.py --simulate-failure   # render as if this week's live output failed validation (testing)

Two stages. build_snapshot() reads the pipeline's outputs, validates them and writes football/data/live.json (the
contract); render() turns only that snapshot into football/live.html. Nothing is calculated except reading, rounding,
labelling and comparing supplied numbers.

Sources
  football/data/frozen_baseline.json  the immutable baseline (M6 §17): every frozen value the page shows, with a sha256.
                                     Each build recomputes it from the frozen outputs and fails if anything moved.
  football/data/research.json        tracker block (exported from the research project's site/data.json by
                                     football_export.py): live season estimates, exclusions, odds check, player-level
                                     checks; frozen per-season opposition (s3_seasons), crowd periods (s2_periods), elite r (s3_elite)
  <research>/logs/live_fetch_summary.json   fixtures vs played per league-season (season progress)
  <research>/logs/weekly/*.log, last_status.txt   weekly runs (update log, partial/failed state)
  <research>/findings/*.md           study status and open items (status board, open questions, dated events), and the
                                     two frozen player-level results that only exist there (Study 2 out-of-sample r, Study 3 sample)

Failure handling (M6 §20): if this week's live output is missing or fails validation, the last validated snapshot is
kept and flagged; if there is none, the page renders the frozen baseline with "Live data temporarily unavailable".
"""
import hashlib
import html
import json
import unicodedata
import math
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fb_chrome  # noqa: E402

SITE = Path(__file__).resolve().parent.parent
FB = SITE / "football"
RS = Path(os.environ.get("FB_RESEARCH", Path.home() / "dev/weather_football"))
R = json.loads((FB / "data/research.json").read_text())
MANIFEST = FB / "data/frozen_baseline.json"
SNAPSHOT = FB / "data/live.json"
IST = timezone(timedelta(hours=5, minutes=30))
LEAGUE = {"EPL": "Premier League", "La_Liga": "La Liga", "Serie_A": "Serie A", "Bundesliga": "Bundesliga", "Ligue_1": "Ligue 1"}
METRIC = {"xg": "xG", "xa": "xA", "shots": "Shots", "key_passes": "Key passes", "goals": "Goals"}
FROZEN_PERIOD = "2015/16 — 2024/25"
SCHEMA = 2
STALE_DAYS = 8          # the pipeline runs every Tuesday (10:00 IST); older than 8 days means at least one run was missed
EARLY_SHARE = 1 / 3     # an in-progress season with under a third of fixtures played is labelled "early season"
NEAR_ZERO_R = 0.1       # |r| below this is described as "near zero" (Claim 03)
T_CORR = '<button type="button" class="term" data-term="correlation">r</button>'
esc = html.escape


def fail(msg):
    sys.exit("build_live: " + msg)


def signed(x, d=1):
    return ("+" if x > 0 else "−" if x < 0 else "") + f"{abs(x):.{d}f}"


def findings(name):
    return (RS / "findings" / f"{name}.md").read_text()


def flat(text):
    return re.sub(r"\s+", " ", text)


def need(name, pattern):
    """Return the first match of pattern in a findings file; the build fails if the research no longer says it."""
    text = findings(name)
    for line in text.splitlines():
        if re.search(pattern, line):
            return line.strip()
    m = re.search(pattern, flat(text))   # phrases wrapped across lines
    if m:
        return m.group(0)
    fail(f"findings/{name}.md no longer contains /{pattern}/ — update the status board")


def slug(label):
    return label.replace("/", "-")


# ================================================================ frozen baseline (immutable, M6 §17)
def frozen_values(T):
    """Every frozen number the page shows, read from the frozen outputs. T (tracker) may be None if the live output is
    unavailable; its frozen copy is then not re-checked this build."""
    s2 = flat(findings("study2_individual_home_advantage"))
    m2 = re.search(r"([\d,]+) players with ≥900 home and ≥900 away minutes in both (2015/16–2018/19) and (2022/23–2024/25)\): "
                   r"correlation between the two periods (−?\d\.\d+)", s2)
    s3 = flat(findings("study3_opposition_effect"))
    m3 = re.search(r"Odd vs even seasons \(([\d,]+) players with ≥450 elite minutes in both\)", s3)
    if not m2 or not m3:
        fail("frozen player-level results (Study 2 out-of-sample r / Study 3 elite sample) not found in findings")
    v = {
        "opposition_seasons_xg": [{"season": f'{r["season"]}/{str(r["season"] + 1)[2:]}', "value": round(r["pct"], 2), "lo": round(r["lo"], 2), "hi": round(r["hi"], 2)}
                                  for r in sorted(R["s3_seasons"], key=lambda r: r["season"]) if r["metric"] == "xg"],
        "home_periods_xg": [{"period": r["period"], "value": round((r["v"] - 1) * 100, 1), "lo": round((r["lo"] - 1) * 100, 1), "hi": round((r["hi"] - 1) * 100, 1)}
                            for r in R["s2_periods"] if r["metric"] == "xg"],
        "home_persistence": {"r": float(m2.group(4).replace("−", "-")), "players": int(m2.group(1).replace(",", "")),
                             "method": f"raw home ÷ away xG/90 per player, {m2.group(2)} vs {m2.group(3)}"},
        "elite": {"players": int(m3.group(1).replace(",", "")), "method": "odd vs even seasons; elite = top 20% of opponents",
                  "r": {r["metric"]: {"overall": r["overall"], "past": r["past"]} for r in R["s3_elite"]}},
    }
    if T is not None:
        v["home"] = {m: round((T["frozen"]["home_ratio"][m] - 1) * 100, 1) for m in METRIC}
        v["opposition"] = {m: round(T["frozen"]["opp_pct_sd"][m], 1) for m in METRIC}
    return v


def digest(values):
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def frozen_baseline(T):
    current = frozen_values(T)
    if "--init-frozen" in sys.argv:
        if T is None:
            fail("--init-frozen needs a valid tracker (home/opposition frozen values come from it)")
        MANIFEST.write_text(json.dumps({"period": FROZEN_PERIOD, "createdAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                        "sha256": digest(current), "values": current}, ensure_ascii=False, indent=1) + "\n")
        print(f"frozen baseline manifest written · sha256 {digest(current)[:12]}")
    if not MANIFEST.exists():
        fail(f"{MANIFEST.relative_to(SITE)} is missing — create it once with --init-frozen")
    man = json.loads(MANIFEST.read_text())
    if digest(man["values"]) != man["sha256"]:
        fail("frozen_baseline.json was edited by hand (its sha256 no longer matches its values)")
    for k, val in current.items():
        if man["values"].get(k) != val:
            fail(f"frozen value '{k}' changed: manifest {json.dumps(man['values'].get(k))[:160]} vs now {json.dumps(val)[:160]}. "
                 "Frozen research is immutable — if this is a published correction, record it under Corrections in the "
                 "findings, then re-run with --init-frozen.")
    return man


# ================================================================ live output (validated)
class LiveUnavailable(Exception):
    pass


def finite(*xs):
    return all(isinstance(x, (int, float)) and math.isfinite(x) for x in xs)


def load_tracker():
    if "--simulate-failure" in sys.argv:
        raise LiveUnavailable("simulated failure (--simulate-failure)")
    T = R.get("tracker")
    if not T or not T.get("seasons"):
        raise LiveUnavailable("the tracker output is missing from the export")
    for sid, s in T["seasons"].items():
        if not s.get("matches"):
            raise LiveUnavailable(f"season {sid} has no processed matches")
        for kind, key in (("home_edge", "ratio"), ("opposition", "pct_sd")):
            e = (s.get(kind) or {}).get("xg")
            if not e or not finite(e[key], e["lo"], e["hi"]) or not e["lo"] <= e[key] <= e["hi"]:
                raise LiveUnavailable(f"season {sid} {kind} xG estimate failed validation")
    try:
        datetime.fromisoformat(T["generated_utc"])
    except (KeyError, ValueError):
        raise LiveUnavailable("the tracker has no valid generation timestamp")
    return T


def change(kind, frozen, v, lo, hi, status, hist=None):
    """Controlled-vocabulary label (M6 §12) from supplied numbers only: does this season's 95% interval contain zero,
    the frozen estimate; same sign?"""
    if lo <= 0 <= hi:
        word, why = "Insufficient evidence", "this season's 95% interval includes zero"
    elif (v > 0) != (frozen > 0):
        word, why = "Opposite direction", "the sign differs from the frozen estimate"
    elif lo <= frozen <= hi:
        word, why = "Broadly stable", "frozen estimate inside this season's 95% interval"
    else:
        bigger = abs(v) > abs(frozen)
        word = ("Higher than baseline" if bigger else "Lower than baseline") if kind == "home" else ("Stronger than baseline" if bigger else "Weaker than baseline")
        why = "frozen estimate outside this season's 95% interval"
    if hist:
        lo_h, hi_h = min(hist), max(hist)
        why += f"; {'inside' if lo_h <= v <= hi_h else 'outside'} the range of single frozen seasons ({signed(lo_h)}% to {signed(hi_h)}%)"
    return {"word": word, "why": why, "early": status != "complete"}


def live_part(T, base):
    fetch = json.loads((RS / "logs/live_fetch_summary.json").read_text())
    seasons = []
    for sid in sorted(T["seasons"]):
        s = T["seasons"][sid]
        fx = {lg: fetch.get(f"{lg}_{sid}", {}) for lg in LEAGUE}
        fixtures = sum(v.get("fixtures", 0) for v in fx.values())
        played = sum(v.get("played", 0) for v in fx.values())
        share = played / fixtures if fixtures else None
        status = "complete" if not s["in_progress"] else ("early" if share is not None and share < EARLY_SHARE else "current")
        seasons.append({"id": sid, "label": s["label"], "slug": slug(s["label"]), "status": status, "through": s["through"],
                        "matches": s["matches"], "player_matches": s["player_matches"], "fixtures": fixtures, "played": played,
                        "progress": round(share, 3) if share is not None else None,
                        "leagues": [{"league": lg, "processed": s["leagues"].get(lg, {}).get("matches"), "played": fx[lg].get("played"),
                                     "fixtures": fx[lg].get("fixtures"), "last": s["leagues"].get(lg, {}).get("last")} for lg in LEAGUE]})

    opp_hist = [r["value"] for r in base["opposition_seasons_xg"]]

    def metric(kind):
        out = []
        for m in METRIC:
            fz = base["home" if kind == "home" else "opposition"][m]
            rows = []
            for s in seasons:
                e = T["seasons"][s["id"]]["home_edge" if kind == "home" else "opposition"].get(m)
                if not e:
                    rows.append({"season": s["label"], "slug": s["slug"], "status": s["status"], "value": None, "note": "Not yet available for this season."})
                    continue
                v, lo, hi = ((e["ratio"] - 1) * 100, (e["lo"] - 1) * 100, (e["hi"] - 1) * 100) if kind == "home" else (e["pct_sd"], e["lo"], e["hi"])
                v, lo, hi = round(v, 1), round(lo, 1), round(hi, 1)
                rows.append({"season": s["label"], "slug": s["slug"], "status": s["status"], "value": v, "lo": lo, "hi": hi, "n_obs": e.get("n_obs"),
                             "change": change(kind, fz, v, lo, hi, s["status"], opp_hist if kind == "opp" and m == "xg" else None)})
            out.append({"id": f"{kind}_{m}", "metric": METRIC[m], "frozen": fz, "seasons": rows})
        return out

    checks = []
    for s in seasons:
        ph = T["seasons"][s["id"]].get("prediction_home") or {}
        pe = T["seasons"][s["id"]].get("prediction_elite") or {}
        elite = {m: v for m, v in pe.items() if isinstance(v, dict) and v.get("players", 0) > 0}
        checks.append({"season": s["label"], "slug": s["slug"], "status": s["status"],
                       "home": {"players": ph["players"], "r": round(ph["r_raw_past"], 3)} if ph.get("players", 0) > 0 and "r_raw_past" in ph else None,
                       "elite": {"players": max(v["players"] for v in elite.values()),
                                 "r": {m: {"overall": round(v["r_overall"], 2), "past": round(v["r_past_elite"], 2)} for m, v in elite.items()}} if elite else None})

    last_status = (RS / "logs/weekly/last_status.txt").read_text().strip() if (RS / "logs/weekly/last_status.txt").exists() else ""
    excluded = T.get("excluded_player_data") or []
    status_matches = re.search(r"(\d+) matches", last_status)
    cur = seasons[-1]
    partial = []
    if excluded:
        partial.append(f"{len(excluded)} {cur['label']} match{'es' if len(excluded) > 1 else ''} not processed in this snapshot ("
                       + "; ".join(sorted({f'{LEAGUE.get(e["league"], e["league"])}: {e["reason"]}' for e in excluded})) + ").")
    if last_status and not last_status.startswith("OK"):
        partial.append("The last weekly run did not finish: " + last_status)
    if status_matches and int(status_matches.group(1)) != cur["matches"]:
        partial.append(f"The weekly run reported {status_matches.group(1)} {cur['label']} matches; this snapshot has {cur['matches']}.")
    return {"generatedAt": T["generated_utc"], "seasons": seasons, "metrics": {"home": metric("home"), "opposition": metric("opp")},
            "checks": checks, "partial": partial, "weeklyStatus": last_status, "odds": T.get("odds_validation")}


# ================================================================ research status + open questions + log (from findings)
def research_part(live):
    s1 = findings("study1_environmental_conditions")
    open_sec = re.search(r"^## Open\n(.*?)(?=^## )", s1, re.S | re.M)
    if not open_sec:
        fail("findings/study1 has no '## Open' checklist — update the status board")
    # (done, short text, raw text) per checklist line
    s1_items = [(box == "x", re.sub(r"\s*\([^)]*\)$", "", t.strip()), t) for box, t in re.findall(r"^- \[( |x)\] (.+)$", open_sec.group(1), re.M)]
    if not s1_items:
        fail("findings/study1 '## Open' has no checklist items")
    s1_frozen = any(done and t.lower().startswith("freeze") for done, t, _ in s1_items)
    need("study1_environmental_conditions", r"crowd results final")
    updated = {i: re.search(r"Last updated: (\d{4}-\d{2}-\d{2})", findings(f)).group(1) for i, f in
               [(1, "study1_environmental_conditions"), (2, "study2_individual_home_advantage"), (3, "study3_opposition_effect"),
                (4, "study4_player_similarity"), (5, "study5_transferability")]}
    for f in ("study2_individual_home_advantage", "study3_opposition_effect", "study4_player_similarity", "study5_transferability"):
        need(f, r"Status: \*\*(complete|all six milestones complete)")
    s4_pairs = need("study4_player_similarity", r"Known similar pairs:\*\* not yet run")
    s5_next = need("study5_transferability", r"log-scale league effect is the next version")
    frozen_note = f"complete on the frozen {FROZEN_PERIOD} data"
    board = [
        {"id": 1, "study": "Environment", "slug": "environment", "updated": updated[1], "frozen": s1_frozen,
         "items": ([["final", "Frozen", frozen_note]] if s1_frozen else [["pending", "Not yet frozen", "its own freeze checklist is still open"]])
         + [["final", "Crowd results final", ""]]
         + [["final" if d else "pending", t, ""] for d, t, _ in s1_items if not (s1_frozen and t.lower().startswith("freeze"))]},
        {"id": 2, "study": "Home advantage", "slug": "home-advantage", "updated": updated[2], "frozen": True, "items": [["final", "Frozen", frozen_note]]},
        {"id": 3, "study": "Opposition", "slug": "opposition", "updated": updated[3], "frozen": True, "items": [["final", "Frozen", frozen_note]]},
        {"id": 4, "study": "Similarity", "slug": "similarity", "updated": updated[4], "frozen": True,
         "items": [["final", "Frozen", frozen_note], ["pending", "Known-pairs check pending", ""]]},
        {"id": 5, "study": "Transferability", "slug": "transferability", "updated": updated[5], "frozen": True,
         "items": [["final", "Frozen", frozen_note], ["pending", "League-effect improvement planned", ""]]},
    ]
    questions = []
    concl = next((t for d, t, _ in s1_items if not d and t.lower().startswith("final weather conclusion")), None)
    temp = re.search(r"Temperature is the one (weather effect that holds up|open lead)", flat(s1))
    if temp and concl and not s1_frozen:   # shown only while Study 1's own checklist leaves the conclusion open
        questions.append({"title": "Temperature", "q": "The small temperature effect survived the placebo check, mostly in Serie A. What does the reviewed final conclusion make of it?",
                          "source": temp.group(0)})
    questions += [
        {"title": "Similarity validation", "q": "Do known similar-player pairs behave as expected?", "source": s4_pairs},
        {"title": "Transfer model", "q": "Can a percentage-based league effect improve predictions for low-output central midfielders moving into the Premier League?", "source": s5_next},
    ]

    log = []
    if live:
        cur = live["seasons"][-1]
        log.append({"date": live["generatedAt"], "text": f"{cur['label']} live data updated · matches through " + datetime.fromisoformat(cur["through"]).strftime("%-d %b %Y")})
        for s in live["seasons"]:
            if s["status"] == "complete":
                log.append({"date": s["through"] + "T23:59:00+00:00", "text": f"{s['label']} season complete · last match processed"})
    for f in sorted((RS / "logs/weekly").glob("*.log")):
        m = re.match(r"(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})", f.stem)
        if m:
            ok = "FAILED at" not in f.read_text(errors="ignore")
            log.append({"date": f"{m.group(1)}T{m.group(2)}:{m.group(3)}:00+05:30", "text": "Weekly pipeline run " + ("completed" if ok else "failed")})
    for d, t, raw in s1_items:
        dm = re.search(r"finished (\d{4}-\d{2}-\d{2})", raw)
        if d and dm:
            log.append({"date": dm.group(1) + "T00:00:00+05:30", "text": f"Study 1: {t[0].lower() + t[1:]} finished"})
    corr = need("study1_environmental_conditions", r"^- (\d{4}-\d{2}-\d{2}): Understat")
    log.append({"date": re.search(r"\d{4}-\d{2}-\d{2}", corr).group(0) + "T00:00:00+05:30", "text": "Correction published: Understat's match “forecast” is post-match (never used in any model)"})
    log.sort(key=lambda e: datetime.fromisoformat(e["date"]), reverse=True)
    return board, questions, log


# ================================================================ snapshot
def build_snapshot():
    notices, state, reason = [], "ok", ""
    try:
        T = load_tracker()
    except LiveUnavailable as e:
        T, reason = None, str(e)
    man = frozen_baseline(T)
    base = man["values"]
    live = None
    if T is not None:
        try:
            live = live_part(T, base)
        except (OSError, KeyError, ValueError, TypeError) as e:
            what = Path(e.filename).name if isinstance(e, OSError) and e.filename else str(e)   # never publish local paths
            reason = f"the live outputs could not be read ({type(e).__name__}: {what})"
    if live is None:
        prev = json.loads(SNAPSHOT.read_text()) if SNAPSHOT.exists() else {}
        if prev.get("schema") == SCHEMA and prev.get("seasons") and prev.get("state") != "unavailable" and "--simulate-failure" not in sys.argv:
            live = {k: prev[k] for k in ("generatedAt", "seasons", "metrics", "checks", "partial", "weeklyStatus", "odds")}
            state = "fallback"
            notices.append({"kind": "fallback", "title": "Showing the last validated update",
                            "text": "This week's live output could not be used. The last validated snapshot is shown below; the historical baseline is unaffected.",
                            "detail": reason})
        else:
            state = "unavailable"
            notices.append({"kind": "unavailable", "title": "Live data temporarily unavailable", "text": "The historical baseline remains available.", "detail": reason})
    elif live["partial"]:
        state = "partial"
    board, questions, log = research_part(live)
    empty = lambda kind, key: [{"id": f"{kind}_{m}", "metric": METRIC[m], "frozen": base[key][m], "seasons": []} for m in METRIC]
    snap = {"schema": SCHEMA, "state": state, "notices": notices, "generatedAt": live["generatedAt"] if live else None,
            "builtAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "staleAfterDays": STALE_DAYS,
            "baseline": {"period": FROZEN_PERIOD, "sha256": man["sha256"], "createdAt": man["createdAt"], **base},
            "seasons": live["seasons"] if live else [],
            "metrics": live["metrics"] if live else {"home": empty("home", "home"), "opposition": empty("opp", "opposition")},
            "checks": live["checks"] if live else [], "partial": live["partial"] if live else [], "weeklyStatus": live["weeklyStatus"] if live else "",
            "researchStatus": board, "questions": questions, "log": log, "odds": live["odds"] if live else None,
            "sources": "Understat · football-data.co.uk (pre-match odds) · fixturedownload.com · openfootball"}
    SNAPSHOT.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")))
    return snap


# ================================================================ render (reads the snapshot only)
STATUS_LABEL = {"complete": "Complete", "current": "Current season", "early": "Early season", "frozen": "Frozen"}


def ist(iso, with_time=False):
    d = datetime.fromisoformat(iso).astimezone(IST)
    return d.strftime("%d %b %Y · %H:%M IST" if with_time else "%d %b %Y").lstrip("0")


def day(date):
    return ist(date + "T12:00:00+00:00")


def pill(status, stale_hook=False):
    cls = {"complete": "pill--final", "current": "pill--live", "early": "pill--pending", "frozen": "pill--frozen"}[status]
    extra = '<span class="pill pill--stale" data-stale-pill hidden>Data may be stale</span>' if stale_hook else ""
    return f'<span class="pill {cls}">{STATUS_LABEL[status]}</span>{extra}'


def axis_row(label_html, track, value_html, cls=""):
    return f'<div class="lv-row {cls}"><span class="lv-s">{label_html}</span><span class="lv-t">{track}</span><span class="lv-v">{value_html}</span></div>'


def axis(lo_ax, hi_ax):
    return lambda v: f"{(min(max(v, lo_ax), hi_ax) - lo_ax) / (hi_ax - lo_ax) * 100:.2f}%"


def comparison(m, lo_ax, hi_ax):
    """BaselineComparison: frozen baseline (distinct ◇) + each live season with its 95% interval."""
    x = axis(lo_ax, hi_ax)
    z = f'<span class="lv-zero" style="left:{x(0)}"></span>'
    out = [axis_row(f"Historical baseline<small>{FROZEN_PERIOD}</small>", z + f'<span class="lv-fz" style="left:{x(m["frozen"])}"></span>',
                    f'{signed(m["frozen"])}%', "lv-row--frozen")]
    for r in m["seasons"]:
        lab = f'{r["season"]}{pill(r["status"], r["status"] != "complete")}'
        if r["value"] is None:
            out.append(f'<div class="lv-row"><span class="lv-s">{lab}</span><span class="lv-na">{esc(r["note"])}</span><span></span></div>')
            continue
        out.append(axis_row(lab, z + f'<span class="lv-ref" style="left:{x(m["frozen"])}"></span><span class="lv-ci" style="left:{x(r["lo"])};width:calc({x(r["hi"])} - {x(r["lo"])})"></span>'
                            f'<span class="lv-dot" style="left:{x(r["value"])}"></span>', f'{signed(r["value"])}%<small>{signed(r["lo"], 0)} to {signed(r["hi"], 0)}</small>',
                            f'lv-row--{r["status"]}'))
    return '<div class="lv-cmp">' + "".join(out) + "</div>"


def phrase(m, r):
    w = r["change"]["word"]
    if w == "Broadly stable":
        return f"in line with the historical baseline ({signed(m['frozen'])}%, inside this season's 95% interval)"
    if w == "Insufficient evidence":
        return "too uncertain to compare yet (its 95% interval includes zero)"
    if w == "Opposite direction":
        return f"in the opposite direction to the historical baseline ({signed(m['frozen'])}%)"
    return f"{w[0].lower() + w[1:]} ({signed(m['frozen'])}% sits outside this season's 95% interval, {signed(r['lo'], 0)} to {signed(r['hi'], 0)})"


def interpretation(m, kind):
    unit = "home xG effect" if kind == "home" else "opposition effect on xG"
    t = []
    for r in m["seasons"]:
        if r["value"] is None:
            continue
        if r["status"] == "complete":
            t.append(f"The {r['season']} {unit} ({signed(r['value'])}%) is {phrase(m, r)}.")
        else:
            t.append(f"{r['season']} so far ({STATUS_LABEL[r['status']].lower()}): {signed(r['value'])}%, {phrase(m, r).split(' (')[0]}. "
                     "Provisional — its interval is wide and will narrow as matches are added.")
    if kind == "opp":
        t.append("Consistency, not proof.")
    return " ".join(t)


def hero_variants(m, kind, seasons):
    """One hero per selector option; the selector only shows/hides them (no values computed in the browser)."""
    unit = "home vs away, same player" if kind == "home" else "per +1 " + '<button type="button" class="term" data-term="sd">SD</button>' + " of opponent strength"
    out = [f'<div class="lv-hv" data-for="baseline" hidden><p class="lv-hero"><b class="lv-hero--fz">{signed(m["frozen"])}%</b>'
           f'<span>{pill("frozen")} historical baseline · {m["metric"]} · {unit}</span></p></div>']
    rows = {r["slug"]: r for r in m["seasons"]}
    for s in seasons:
        r = rows.get(s["slug"])
        hidden = "" if s is seasons[-1] else " hidden"
        if not r or r["value"] is None:
            out.append(f'<div class="lv-hv" data-for="{s["slug"]}"{hidden}><p class="lv-na">Not yet available for {s["label"]}.</p></div>')
            continue
        out.append(f'<div class="lv-hv lv-hv--{s["status"]}" data-for="{s["slug"]}"{hidden}><p class="lv-hero"><b>{signed(r["value"])}%</b>'
                   f'<span>{pill(s["status"], s["status"] != "complete")} {s["label"]} · {m["metric"]} · {unit}</span></p>'
                   f'<p class="lv-hero__base">Historical baseline <b>{signed(m["frozen"])}%</b> · this season\'s 95% interval {signed(r["lo"], 0)} to {signed(r["hi"], 0)}</p></div>')
    return "".join(out)


def history_html(kind, m, snap):
    base = snap["baseline"]
    live_rows = [r for r in m["seasons"] if r["value"] is not None]
    if kind == "opp":
        x = axis(-25, 0)
        z = f'<span class="lv-zero" style="left:{x(0)}"></span>'
        hist = base["opposition_seasons_xg"]
        ci = lambda r: f'<span class="lv-ci" style="left:{x(r["lo"])};width:calc({x(r["hi"])} - {x(r["lo"])})"></span>'
        rows = "".join(axis_row(r["season"], z + ci(r) + f'<span class="lv-dot lv-dot--hist" style="left:{x(r["value"])}"></span>', f'{signed(r["value"])}%') for r in hist)
        rows += axis_row("Frozen<small>pooled</small>", z + f'<span class="lv-fz" style="left:{x(m["frozen"])}"></span>', f'{signed(m["frozen"])}%', "lv-row--frozen lv-row--sep")
        rows += "".join(axis_row(f'{r["season"]}{pill(r["status"])}', z + ci(r) + f'<span class="lv-dot" style="left:{x(r["value"])}"></span>',
                                 f'{signed(r["value"])}%', f'lv-row--{r["status"]}') for r in live_rows)
        vals = [r["value"] for r in hist]
        live_s = "; ".join(f'{r["season"]}: {signed(r["value"])}%' for r in live_rows)
        return f"""<details class="lv-hist"><summary><span class="lv-hist__t">Show all historical seasons</span><span aria-hidden="true">+</span></summary>
      <figure class="chart lv-fig"><figcaption><p class="chart__title">Opposition effect on xG, season by season</p>
        <p class="chart__sub">Each frozen season (Study 3), the pooled frozen estimate, then the live seasons. 95% intervals.</p></figcaption>
        <div class="chart__plot" role="img" aria-label="Opposition effect per frozen season from {hist[0]["season"]} to {hist[-1]["season"]}, between {signed(min(vals))}% and {signed(max(vals))}%; pooled {signed(m["frozen"])}%"><div class="lv-cmp">{rows}</div></div>
        <p class="chart__summary">Single frozen seasons range from {signed(min(vals))}% to {signed(max(vals))}% per SD — the normal year-to-year variation.{f" Live: {live_s}." if live_s else ""}</p>
        <p class="source">Study 03 · per-season models (frozen) · live tracker</p></figure></details>"""
    lab = {"before": "With fans, before 2020", "closed": "Behind closed doors", "after": "Fans back"}
    hp = "".join(f'<li><span>{lab[r["period"]]}</span><b>{signed(r["value"])}%</b><small>{signed(r["lo"], 0)} to {signed(r["hi"], 0)}</small></li>' for r in base["home_periods_xg"])
    lv = "".join(f'<li><span>{r["season"]}</span><b>{signed(r["value"])}%</b><small>{STATUS_LABEL[r["status"]].lower()} · {signed(r["lo"], 0)} to {signed(r["hi"], 0)}</small></li>' for r in live_rows)
    return f"""<details class="lv-hist"><summary><span class="lv-hist__t">Show all historical seasons</span><span aria-hidden="true">+</span></summary>
      <p class="body">The frozen outputs have no season-by-season home estimate — Study 2 split the decade by crowd status instead, so that is what is shown here rather than invented single seasons.</p>
      <ul class="lv-changes lv-periods">{hp}<li class="lv-sep"><span>Frozen</span><b>{signed(m["frozen"])}%</b><small>with fans, pooled</small></li>{lv}</ul>
      <p class="source">Study 02 · same player, home ÷ away xG per minute</p></details>"""


def claim_block(n, kind, title, claim, m, snap, lo_ax, hi_ax):
    sid = "home" if kind == "home" else "opp"
    seasons = snap["seasons"]
    if seasons:
        body = hero_variants(m, kind, seasons) + f'<p class="body">{esc(interpretation(m, kind))}</p>'
    else:
        body = (f'<p class="lv-hero"><b class="lv-hero--fz">{signed(m["frozen"])}%</b><span>{pill("frozen")} historical baseline · {m["metric"]}</span></p>'
                '<p class="lv-na">Live estimates are temporarily unavailable. The historical baseline is unaffected.</p>')
    head = "".join(f'<th scope="col">{s["label"]}<small>{STATUS_LABEL[s["status"]]}</small></th>' for s in seasons)
    table = "".join(
        f'<tr><th scope="row">{x["metric"]}</th><td class="frozen">{signed(x["frozen"])}%</td>'
        + "".join((f'<td>{signed(r["value"])}%<small>{signed(r["lo"], 0)} to {signed(r["hi"], 0)}</small></td>' if r["value"] is not None
                   else '<td><small>Not yet available</small></td>') for r in x["seasons"]) + "</tr>"
        for x in snap["metrics"]["home" if kind == "home" else "opposition"])
    aria = f'{m["metric"]}: historical baseline {signed(m["frozen"])}%; ' + "; ".join(
        f'{r["season"]} {signed(r["value"])}%' if r["value"] is not None else f'{r["season"]} not yet available' for r in m["seasons"])
    tbl = (f'<details class="data"><summary>All five metrics</summary><div class="tscroll"><table class="ltable"><caption class="sr-only">{esc(title)}: baseline and live seasons, five metrics, with 95% intervals</caption>'
           f'<thead><tr><th scope="col">Metric</th><th scope="col">Baseline</th>{head}</tr></thead><tbody>{table}</tbody></table></div></details>') if seasons else ""
    return f"""<section class="lv-sec lv-claim" id="{sid}" aria-labelledby="{sid}-h">
  <div class="wrap">
    <p class="lv-kicker">Claim {n:02d} · {esc(title)}</p>
    <div class="lv-grid">
      <div>
        <h2 id="{sid}-h" class="h2-sm lv-claim__q"><span class="lv-claim__l">The research claimed</span>{esc(claim)}</h2>
        {body}
      </div>
      <figure class="chart lv-fig">
        <figcaption><p class="chart__title">{esc(m["metric"])} {"home edge" if kind == "home" else "opposition effect"} · baseline vs live seasons</p>
        <p class="chart__sub">Historical baseline {FROZEN_PERIOD} (◇) · live seasons with 95% <button type="button" class="term" data-term="interval">intervals</button>. Live seasons never change the baseline.</p></figcaption>
        <div class="chart__plot" role="img" aria-label="{esc(aria)}">{comparison(m, lo_ax, hi_ax)}</div>
        {tbl}
      </figure>
    </div>
    {history_html(kind, m, snap)}
  </div>
</section>"""


def player_claims(snap):
    base, checks = snap["baseline"], snap["checks"]
    hp, el = base["home_persistence"], base["elite"]
    near = lambda r: "near zero" if abs(r) < NEAR_ZERO_R else "not near zero"

    def row(label, status, value, note, cls=""):
        return (f'<li class="lv-pc {cls}"><span class="lv-pc__s">{label}{pill(status, status not in ("complete", "frozen"))}</span>'
                f'<span class="lv-pc__v">{value}</span><small>{note}</small></li>')

    h = [row("Historical", "frozen", f'{T_CORR} = {hp["r"]:.3f}', f'{hp["players"]:,} players · {esc(hp["method"])} · {near(hp["r"])}', "lv-pc--fz")]
    e = [row("Historical", "frozen", f'{el["r"]["xg"]["overall"]:.2f} <span class="muted">vs</span> {el["r"]["xg"]["past"]:.2f}',
             f'{el["players"]:,} players · {esc(el["method"])}', "lv-pc--fz")]
    for c in checks:
        if c["home"]:
            h.append(row(c["season"], c["status"], f'r = {c["home"]["r"]:.3f}',
                         f'{c["home"]["players"]:,} players · frozen-period home edge vs {c["season"]} · {near(c["home"]["r"])}'))
        else:
            h.append(row(c["season"], c["status"], '<span class="lv-na">Not yet recalculated for the live dataset.</span>', "Not enough players with a full home and away sample yet."))
        if c["elite"]:
            xg = c["elite"]["r"].get("xg")
            wins = sum(v["overall"] > v["past"] for v in c["elite"]["r"].values())
            e.append(row(c["season"], c["status"], f'{xg["overall"]:.2f} <span class="muted">vs</span> {xg["past"]:.2f}' if xg else '<span class="lv-na">xG not computed</span>',
                         f'{c["elite"]["players"]:,} players · frozen-period record vs {c["season"]} · overall level higher in {wins} of {len(c["elite"]["r"])} metrics'))
        else:
            e.append(row(c["season"], c["status"], '<span class="lv-na">Historical result · live validation pending</span>', "Not enough elite-opponent minutes yet."))
    if not checks:
        h.append(row("Live", "frozen", '<span class="lv-na">Live data temporarily unavailable.</span>', ""))
        e.append(row("Live", "frozen", '<span class="lv-na">Live data temporarily unavailable.</span>', ""))
    return f"""<section class="lv-sec" aria-labelledby="pc-h"><div class="wrap">
  <p class="lv-kicker">Claims 03 – 04 · Player level</p>
  <h2 id="pc-h" class="h2-sm">Two predictions about individual players</h2>
  <p class="body" style="max-width:46em">A live season appears here only once the pipeline has re-run the test. The live tests compare a player's frozen-period record with the new season, so the method differs slightly from the frozen test; each row says which.</p>
  <div class="lv-checks">
    <div class="lv-check"><p class="label">Claim 03 · Home specialists</p><p class="lv-check__q">Past home edge does not predict future home edge.</p>
      <ul class="lv-pcs" aria-label="Correlation between past and later home edge">{"".join(h)}</ul>
      <p class="source">Study 02 · out-of-sample check (frozen) · live tracker</p></div>
    <div class="lv-check"><p class="label">Claim 04 · Elite opponents</p><p class="lv-check__q">Overall adjusted level predicts elite-opponent output better than past elite-opponent record.</p>
      <ul class="lv-pcs" aria-label="xG correlation with elite-opponent output: overall adjusted level vs past elite record">{"".join(e)}</ul>
      <p class="source">xG correlation with elite-opponent output: overall adjusted level <span class="muted">vs</span> past elite record · Study 03 · live tracker</p></div>
  </div>
</div></section>"""


def forecasts_html():
    """Study 05 live: summer-2026 transfer forecasts registered before the season's output was known (research pipeline,
    src/live/study5_forecasts.py). Progress is descriptive; scoring happens after the season."""
    L = R.get("s5live")
    if not L:
        return ""
    rows = sorted(L["rows"], key=lambda r: -r["min"])
    judged = [r for r in rows if r["min"] >= 450 and r["status"].endswith("range")]
    inside = sum(r["status"] == "inside 80% range" for r in judged)
    f2 = lambda v: "—" if v is None else f"{v:.2f}"
    def key(r):   # search text: player, clubs, leagues — accents stripped so "odegaard" finds "Ødegaard"
        t = " ".join([r["player"], r["from"], r["to"], LEAGUE.get(r.get("ol"), ""), LEAGUE.get(r.get("dl"), "")])
        t = unicodedata.normalize("NFKD", t.replace("ø", "o").replace("Ø", "O").replace("ß", "ss"))
        return esc("".join(c for c in t if not unicodedata.combining(c)).lower())
    body = "".join(
        f'<tr data-q="{key(r)}"><th scope="row">{esc(r["player"])}<small>{esc(r["from"])} → {esc(r["to"])}</small></th><td>{f2(r["pre"])}</td>'
        f'<td>{f2(r["pred"])} <small class="muted">{f2(r["q10"])}–{f2(r["q90"])}</small></td><td>{r["min"]:,}</td>'
        f'<td>{f2(r["act"])}</td><td class="wrapok">{esc(r["status"])}</td></tr>' for r in rows)
    progress = (f"{len(judged)} have passed 450 minutes in their new league; {inside} of them are inside their 80% range."
                if judged else "None has passed 450 minutes in the new league yet.")
    return f"""<section class="lv-sec" aria-labelledby="tf-h"><div class="wrap">
  <p class="lv-kicker">Claim 05 · Transfers · pre-registered</p>
  <h2 id="tf-h" class="h2-sm">Summer 2026 transfers, forecast from last season's data</h2>
  <p class="body" style="max-width:46em">On {esc(L["registered"])} the frozen Study 05 model forecast every forward and midfielder who moved between the five leagues this summer: <strong>{len(rows)} moves</strong>. The forecasts use only data up to the end of 2025/26, never the 2026/27 matches already played when they were registered. They are locked, and each weekly run checks they have not changed. Through {esc(L["through"])}, {progress} They are scored after the season, on players with 900+ minutes; until then this is progress, not a result.</p>
  <div class="lv-tf">
    <div class="lv-tf__bar">
      <p class="lv-tf__t">All {len(rows)} forecasts <span class="muted">· xG + xA per 90 · most minutes first</span></p>
      <div class="lv-tf__search" hidden><label for="tf-q" class="sr-only">Search transfers by player, club or league</label>
        <input id="tf-q" type="search" placeholder="Search player, club or league" autocomplete="off" spellcheck="false" />
        <span class="lv-tf__n" id="tf-n" aria-live="polite">{len(rows)} of {len(rows)}</span></div>
    </div>
    <div class="tscroll lv-tf__scroll" tabindex="0" role="region" aria-label="Summer 2026 transfer forecasts table"><table class="ltable" id="tf-table"><caption class="sr-only">Summer 2026 cross-league moves: 2025/26 output, forecast with 80% range, minutes and output so far in 2026/27</caption>
    <thead><tr><th scope="col">Player</th><th scope="col">2025/26</th><th scope="col">Forecast · 80% range</th><th scope="col">Minutes</th><th scope="col">So far</th><th scope="col">Status</th></tr></thead><tbody>{body}</tbody></table>
    <p class="lv-tf__none" id="tf-none" hidden>No summer 2026 move matches that search. Only forwards and midfielders who moved between two of the five leagues are tracked.</p></div>
  </div>
  <p class="source">Study 05 · Model A refitted on 428 past moves · forecasts registered {esc(L["registered"])} · live tracker</p>
</div></section>"""


def selector_html(snap):
    seasons = snap["seasons"]
    if not seasons:
        return ""
    opts = "".join(f'<option value="{s["slug"]}"{" selected" if s is seasons[-1] else ""}>{s["label"]} · {STATUS_LABEL[s["status"]].lower()}</option>' for s in reversed(seasons))
    opts += f'<option value="baseline">Historical baseline · {FROZEN_PERIOD}</option>'
    panels = [f'<div class="lv-sp" data-for="baseline" hidden><p class="lv-sp__h"><b>Historical baseline</b>{pill("frozen")}</p>'
              f'<p class="body">{FROZEN_PERIOD}, ten seasons. Fixed at publication · manifest checksum <code>{snap["baseline"]["sha256"][:12]}</code>.</p></div>']
    for s in seasons:
        share = s["played"] / s["fixtures"] if s["fixtures"] else None
        lg = "".join(f'<li><span>{LEAGUE[l["league"]]}</span><span class="lv-pbar"><i style="width:{(l["played"] or 0) / (l["fixtures"] or 1) * 100:.1f}%"></i></span>'
                     f'<b>{l["processed"] if l["processed"] is not None else "—"}<small>/{l["fixtures"]}</small></b></li>' for l in s["leagues"])
        bar = (f'<div class="lv-pbar lv-pbar--big" role="img" aria-label="{share * 100:.0f}% of {s["fixtures"]:,} fixtures played"><i style="width:{share * 100:.1f}%"></i></div>'
               if share is not None else '<p class="lv-na">Fixture count not available from the pipeline.</p>')
        prog = f" · {share * 100:.0f}% of fixtures played" if share is not None else ""
        panels.append(
            f'<div class="lv-sp" data-for="{s["slug"]}"{"" if s is seasons[-1] else " hidden"}>'
            f'<p class="lv-sp__h"><b>{s["label"]}</b>{pill(s["status"], s["status"] != "complete")}</p>'
            f'<p class="label">Season progress{prog}</p>{bar}'
            f'<dl class="lv-dl"><div><dt>Matches processed</dt><dd>{s["matches"]:,}</dd></div><div><dt>Matches through</dt><dd>{day(s["through"])}</dd></div>'
            f'<div><dt>Last updated</dt><dd>{ist(snap["generatedAt"])}</dd></div></dl>'
            f'<details class="lv-leaguebox"><summary>By league</summary><ul class="lv-leagues">{lg}</ul>'
            f'<p class="source">Processed / fixtures · played share from the weekly Understat fetch</p></details></div>')
    return f"""<section class="lv-select wrap" aria-label="Season">
  <div class="lv-select__c" id="lv-selector" hidden><label class="label" for="lv-season">Season</label>
    <select id="lv-season">{opts}</select></div>
  {"".join(panels)}
</section>"""


def changed_html(snap):
    if not snap["seasons"]:
        return ""
    H, O = snap["metrics"]["home"][0], snap["metrics"]["opposition"][0]
    blocks = ['<div class="lv-hv" data-for="baseline" hidden><p class="body">This is the baseline itself. Choose a live season to compare it with.</p></div>']
    for s in snap["seasons"]:
        items = []
        for name, m in (("Home xG", H), ("Opposition", O)):
            r = next((r for r in m["seasons"] if r["slug"] == s["slug"]), None)
            if not r or r["value"] is None:
                items.append(f'<li><p class="label">{name}</p><p class="lv-ch__v">{signed(m["frozen"])}%</p><p class="lv-ch__w">Not yet available for this season</p></li>')
                continue
            w = ("Early · " if r["change"]["early"] else "") + r["change"]["word"]
            items.append(f'<li><p class="label">{name}</p><p class="lv-ch__v">{signed(m["frozen"])}% <span aria-hidden="true">→</span><span class="sr-only">to</span> {signed(r["value"])}%</p>'
                         f'<p class="lv-ch__w">{esc(w)}</p><p class="small muted">{esc(r["change"]["why"][0].upper() + r["change"]["why"][1:])}</p></li>')
        blocks.append(f'<div class="lv-hv" data-for="{s["slug"]}"{"" if s is snap["seasons"][-1] else " hidden"}><p class="small muted">Historical baseline → {s["label"]} '
                      f'({STATUS_LABEL[s["status"]].lower()})</p><ul class="lv-ch">{"".join(items)}</ul></div>')
    return f"""<section class="lv-sec" aria-labelledby="chg-h"><div class="wrap">
  <p class="lv-kicker">Summary</p><h2 id="chg-h" class="h2-sm">What's changed?</h2>
  {"".join(blocks)}
  <p class="source">Labels come from fixed rules, not judgement: <b>broadly stable</b> = the baseline sits inside the season's 95% interval; <b>higher / lower</b> (home) or <b>stronger / weaker</b> (opposition) = it sits outside; <b>insufficient evidence</b> = the interval includes zero; <b>early</b> = the season is in progress.</p>
</div></section>"""


def render(snap):
    seasons, base = snap["seasons"], snap["baseline"]
    H, O = snap["metrics"]["home"][0], snap["metrics"]["opposition"][0]
    cur = seasons[-1] if seasons else None
    notices = "".join(f'<div class="lv-alert lv-alert--{n["kind"]}" role="status"><p class="label">{esc(n["title"])}</p><p>{esc(n["text"])}</p>'
                      + (f'<p class="small muted">Reason: {esc(n["detail"])}</p>' if n.get("detail") else "") + "</div>" for n in snap["notices"])
    if snap["partial"]:
        notices += '<div class="lv-alert" role="status"><p class="label">Partial update</p>' + "".join(f"<p>{esc(p)}</p>" for p in snap["partial"]) + "</div>"
    last = ist(snap["generatedAt"], True) if snap["generatedAt"] else "Unavailable"
    stale = (f'<div class="lv-alert lv-alert--stale" id="lv-stale" hidden role="status"><p class="label">Data may be stale</p>'
             f'<p>Last successful update: {ist(snap["generatedAt"])}. The latest season data is not currently available.</p></div>') if snap["generatedAt"] else ""
    live_list = " · ".join(f'{s["label"]} <small>{STATUS_LABEL[s["status"]].lower()}</small>' for s in seasons) or "Temporarily unavailable"
    board_html = "".join(
        f'<li><a href="/football/research/{b["slug"]}"><span class="lv-b__n">0{b["id"]}</span><span class="lv-b__t">{esc(b["study"])}</span></a><ul>'
        + "".join(f'<li class="st-{st}"><span aria-hidden="true">{"●" if st == "final" else "◐"}</span> {esc(t)}{f"<small> · {esc(sub)}</small>" if sub else ""}</li>'
                  for st, t, sub in b["items"])
        + f'</ul><small>Findings updated {day(b["updated"])}</small></li>' for b in snap["researchStatus"])
    q_html = "".join(f'<li><p class="label">{esc(q["title"])}</p><p>{esc(q["q"])}</p></li>' for q in snap["questions"])
    log_html = "".join(f'<li><time datetime="{e["date"]}">{ist(e["date"])}</time><span>{esc(e["text"])}</span></li>' for e in snap["log"])
    od = snap["odds"] or {}
    odds = (f'<div><dt>Odds</dt><dd>{esc(od.get("live_odds", ""))} for live seasons; correlation with the frozen ratings {od.get("r_rating", 0):.4f} on {od.get("matches", 0):,} matches</dd></div>'
            if od else "")

    body = f"""<main id="main" class="lv">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li aria-current="page">Live</li></ol></nav>

<header class="lv-head wrap">
  <div class="lv-head__l">
    <p class="lv-flag"><span class="lv-dotlive" aria-hidden="true"></span>Live data · updated weekly</p>
    <h1>Does the research still hold?</h1>
    <p class="lede">The original analysis is frozen. New seasons are added separately to see whether the patterns continue.</p>
  </div>
  <dl class="lv-panel">
    <div class="lv-panel__u"><dt>Last updated</dt><dd id="lv-updated" data-generated="{snap["generatedAt"] or ""}" data-stale-days="{snap["staleAfterDays"]}">{last}</dd></div>
    <div><dt>Latest match</dt><dd>{day(cur["through"]) if cur else "—"}</dd></div>
  </dl>
</header>

<div class="wrap"><div class="lv-split" role="group" aria-label="Frozen and live data">
  <div class="lv-split__fz"><p class="label">Frozen</p><p class="lv-split__v">{FROZEN_PERIOD}</p><p class="small">The published research. Never changes.</p></div>
  <div class="lv-split__lv"><p class="label">Live</p><p class="lv-split__v">{live_list}</p><p class="small">New seasons, estimated the same way and shown beside it.</p></div>
</div></div>

<div class="wrap lv-alerts" aria-live="polite">{stale}{notices}</div>

{selector_html(snap)}

<section class="lv-sec lv-intro" aria-labelledby="rv-h"><div class="wrap">
  <p class="lv-kicker">Research vs reality</p>
  <h2 id="rv-h" class="h2-sm">The research made a set of claims. New seasons give us a chance to see whether those claims survive.</h2>
  <div class="lv-legend" aria-label="How to read this page"><span><i class="lv-sw lv-sw--fz"></i>Historical baseline · never changes</span><span><i class="lv-sw lv-sw--live"></i>Live season estimate</span><span><i class="lv-sw lv-sw--ci"></i>95% interval</span><span>{pill("complete")} {pill("current")} {pill("early")}</span></div>
</div></section>

{claim_block(1, "home", "Home advantage", "Players produce more attacking output at home.", H, snap, -5, 40)}
{claim_block(2, "opp", "Opposition", "Players produce less attacking output against stronger opponents.", O, snap, -25, 5)}
{player_claims(snap)}
{forecasts_html()}
{changed_html(snap)}

<section class="lv-sec lv-immutable" aria-labelledby="imm-h"><div class="wrap lv-grid">
  <div><p class="lv-kicker">Frozen research protection</p><h2 id="imm-h" class="h2-sm">The historical baseline is immutable.</h2></div>
  <div><p class="body">New seasons are evaluated separately and do not change previously published estimates. Every frozen number on this page is read from a fixed manifest; each weekly rebuild recomputes it from the frozen outputs and stops if anything has moved.</p>
    <p class="small muted">Manifest checksum <code>{base["sha256"][:16]}</code> · fixed {ist(base["createdAt"])} · corrections are published in the findings, never applied silently.</p></div>
</div></section>

<section class="lv-sec" aria-labelledby="st-h"><div class="wrap lv-grid">
  <div><p class="lv-kicker">Research status</p><h2 id="st-h" class="h2-sm">Where each study stands</h2>
    <ul class="lv-board">{board_html}</ul>
    <p class="source">From each study's findings file · open items stay visible until the research closes them</p></div>
  <div><p class="lv-kicker">Open questions</p><h2 id="q-h" class="h2-sm">What are we investigating next?</h2>
    <ul class="lv-qs" aria-labelledby="q-h">{q_html}</ul>
    <p class="source">From the research's open items · nothing here is a result yet</p></div>
</div></section>

<section class="lv-sec" aria-labelledby="log-h"><div class="wrap lv-grid">
  <div><p class="lv-kicker">Update log</p><h2 id="log-h" class="h2-sm">This is maintained</h2>
    <ol class="lv-log">{log_html}</ol>
    <p class="source">Events recorded by the pipeline (weekly run logs, snapshot timestamp) and dated entries in the findings files</p></div>
  <div><p class="lv-kicker">Data provenance</p>
    <dl class="lv-dl lv-prov"><div><dt>Live data</dt><dd>Updated weekly (Tuesday pipeline → validation → snapshot → this page)</dd></div><div><dt>Frozen baseline</dt><dd>{FROZEN_PERIOD}</dd></div>
      <div><dt>Current seasons</dt><dd>{" · ".join(s["label"] for s in seasons) or "2025/26+"}</dd></div>{odds}
      <div><dt>Sources</dt><dd>{esc(snap["sources"])}</dd></div></dl>
    <p><a class="link-arrow" href="/football/methodology">How the research works <span class="arr" aria-hidden="true">→</span></a></p></div>
</div></section>
</main>

<script>
// Live page behaviour. Nothing statistical happens here: the snapshot's age is compared with today's date, and the
// season selector shows/hides blocks that were rendered at build time.
(function () {{
  var el = document.getElementById("lv-updated");
  if (el && el.getAttribute("data-generated")) {{
    var age = (Date.now() - Date.parse(el.getAttribute("data-generated"))) / 864e5;
    if (age > +el.getAttribute("data-stale-days")) {{
      var w = document.getElementById("lv-stale"); if (w) w.hidden = false;
      document.documentElement.classList.add("lv-is-stale");
      document.querySelectorAll("[data-stale-pill]").forEach(function (p) {{ p.hidden = false; }});
    }}
  }}
  var tq = document.getElementById("tf-q");
  if (tq) {{
    var rows = document.querySelectorAll("#tf-table tbody tr"), n = document.getElementById("tf-n"), none = document.getElementById("tf-none");
    var norm = function (t) {{ return t.toLowerCase().replace(/ø/g, "o").replace(/ß/g, "ss").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").trim(); }};
    tq.closest(".lv-tf__search").hidden = false;
    tq.addEventListener("input", function () {{
      var q = norm(tq.value), shown = 0;
      rows.forEach(function (r) {{ var ok = !q || r.getAttribute("data-q").indexOf(q) !== -1; r.hidden = !ok; if (ok) shown++; }});
      n.textContent = shown + " of " + rows.length; none.hidden = shown > 0;
    }});
  }}
  var sel = document.getElementById("lv-season");
  if (!sel) return;
  document.getElementById("lv-selector").hidden = false;
  function show(v) {{
    document.querySelectorAll("[data-for]").forEach(function (n) {{ n.hidden = n.getAttribute("data-for") !== v; }});
  }}
  var q = new URLSearchParams(location.search).get("season");
  if (q && sel.querySelector('option[value="' + q.replace(/[^\\w-]/g, "") + '"]')) {{ sel.value = q; show(q); }}
  sel.addEventListener("change", function () {{
    show(sel.value);
    var u = new URL(location.href);
    if (sel.value === sel.options[0].value) u.searchParams.delete("season"); else u.searchParams.set("season", sel.value);
    history.replaceState(null, "", u);
  }});
}})();
</script>"""

    META = json.loads((FB / "data/meta.json").read_text())
    h25 = next((r for r in H["seasons"] if r["status"] == "complete" and r["value"] is not None), None)
    o25 = next((r for r in O["seasons"] if r["status"] == "complete" and r["value"] is not None), None)
    desc = (f"Live tracker: does the research still hold? Home xG edge {signed(h25['value'])}% in {h25['season']} vs {signed(H['frozen'])}% frozen; "
            f"opposition effect {signed(o25['value'])}% vs {signed(O['frozen'])}%. Frozen 2015/16–2024/25 baseline, live seasons beside it, updated weekly."
            if h25 and o25 else "Live tracker: the frozen 2015/16–2024/25 research baseline, with new seasons tracked beside it weekly.")
    ld = {"@context": "https://schema.org", "@type": "Dataset", "name": "Home Turf & Hard Opponents — live research tracker", "url": fb_chrome.SITE + "/football/live",
          "description": desc, "dateModified": snap["generatedAt"] or snap["builtAt"], "temporalCoverage": f"2015-08/{cur['through'] if cur else '2025-05'}",
          "isPartOf": {"@id": "https://iyush.dev/football#site"}, "creator": {"@id": "https://iyush.dev/#person"}}
    doc = (fb_chrome.head("/football/live", "Live tracker · Does the research still hold? · Home Turf & Hard Opponents", desc, "Does the research still hold?", "live.png", ld, "website")
           + "\n<body>\n" + fb_chrome.header("/football/live") + "\n\n" + body + "\n\n"
           + fb_chrome.footer(datetime.fromisoformat(META["tracker_generated_utc"]).strftime("%b %Y")) + "\n</body>\n</html>\n")
    (FB / "live.html").write_text(doc)
    return doc


if __name__ == "__main__":
    snap = build_snapshot()
    doc = render(snap)
    print(f"live: state {snap['state']} · snapshot {SNAPSHOT.stat().st_size / 1024:.1f} KB · page {len(doc) / 1024:.1f} KB · seasons "
          + (", ".join(f'{s["label"]} {s["status"]} ({s["played"]}/{s["fixtures"]})' for s in snap["seasons"]) or "none")
          + f" · partial: {len(snap['partial'])} · log: {len(snap['log'])} events · baseline {snap['baseline']['sha256'][:12]}")
