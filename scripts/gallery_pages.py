"""Match pages for the Football Match Gallery (M3): /football/gallery/match/<id>.

Rendered by scripts/build_gallery.py from the canonical M1 records (research project, data/processed/GALLERY).
Everything on a page is read from the record: stars, components, the points breakdown (M1's `contributions`, which
the research build reconciles with the stored score), labels with their triggers, statistics and the goal timeline.
No rating logic lives here. The only arithmetic is presentational: running score along the stored goal list, and
aggregate = first leg + this leg for two-legged ties.
"""
import html

import fb_chrome

esc = html.escape
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
PERIOD_END = {1: 45, 2: 90, 3: 105, 4: 120}
MISSING_TEXT = {"shots_on_target": ("Shots on target", "Entertainment"), "red_cards": ("Red cards", "Drama"),
                "penalties": ("Penalties awarded", "Drama")}
DRAMA_NAMES = {"late_goal": "Late result-changing goal", "comeback": "Comeback", "equalisers": "Equalisers",
               "red_cards": "Red cards", "penalties": "Penalties awarded", "shootout": "Penalty shootout"}
UNRATED_REASON = {
    "not_played": "The fixture date has passed but no result has been recorded. The match was postponed, abandoned "
                  "or cancelled, so there is nothing to rate.",
    "source_conflict": "Our data sources disagree about this match, so it is not rated until they agree. A rating is "
                       "never guessed from conflicting records.",
    "invalid_source_record": "The source record for this match is incomplete, so it is not rated.",
    "goal_timeline_does_not_match_score": "The recorded goals do not add up to the final score, so the match is not "
                                          "rated.",
}
FLAG_TEXT = {
    "home_away_flipped_in_understat": "Understat lists this fixture with home and away reversed.",
    "score_conflict_understat_vs_football_data": "Understat and football-data.co.uk record different final scores.",
    "half_time_score_conflict": "Understat and football-data.co.uk record different half-time scores.",
    "fixture_date_passed_without_result": "The scheduled date has passed with no result recorded.",
    "aggregate_unresolved": "The two-legged tie's aggregate score could not be reconciled.",
    "understat_player_rows_excluded": "Understat's player rows for this match were excluded from player research "
                                      "(match-level data is unaffected).",
}


CRESTS = set()   # club ids with a crest in football/crests/ (set by build_gallery.py from crests.json)
CREST_NOTE = "Club crests are trademarks of their clubs; images via ESPN."


def crest(club_id, name, size, cls=""):
    """A club's crest beside its name (decorative: the name is always next to it), or an initials disc."""
    if club_id and club_id in CRESTS:
        return (f'<img class="crest {cls}" src="/football/crests/{club_id.replace(":", "-")}.png" width="{size}" '
                f'height="{size}" alt="" loading="lazy" decoding="async" />')
    initials = "".join(w[0] for w in (name or "?").replace(".", " ").split()[:2]).upper()
    return f'<span class="crest crest--none {cls}" style="width:{size}px;height:{size}px" aria-hidden="true">{esc(initials)}</span>'


def match_id(key):
    """Canonical match_key -> URL id: 'La_Liga-2026-us:30844' -> 'la-liga-2026-us-30844'."""
    return key.lower().replace("_", "-").replace(":", "-")


def long_date(d):
    return f"{int(d[8:10])} {MONTHS[int(d[5:7]) - 1]} {d[:4]}" if d else "Date unknown"


def minute_label(period, minute):
    end = PERIOD_END[period]
    return f"{end}+{minute - end}′" if minute > end else f"{minute}′"


def stars_html(st, cls="gm-stars"):
    return (f'<span class="gx-stars {cls}" role="img" aria-label="{st:.1f} out of 5 stars">'
            f'<span class="gx-stars__on" style="width:{st / 5 * 100:g}%"></span></span>')


def fmt(x, nd=1):
    return f"{x:.{nd}f}"


def sot_rank(value):
    """The stored mid-rank percentile in words (ties count half, so it is not 'the share with fewer')."""
    pct = round(100 * value)
    if pct < 1:
        return "among the lowest counts of 2025/26"
    if pct >= 100:
        return "among the highest counts of 2025/26"
    suffix = "th" if 10 <= pct % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(pct % 10, "th")
    return f"{pct}{suffix} percentile of 2025/26 matches"


def plural(n, word, many=None):
    return f"{n} {word if n == 1 else (many or word + 's')}"


# ---------------------------------------------------------------- explanation (grounded in stored fields only)
def why_sentences(r):
    """Sentences built from the record's stored contributions and stats, ranked by the points each explains.
    Nothing is said about a field that is missing."""
    c, d, st, sc = r["contributions"], r["details"], r["stats"], r["score"]
    goals = sc["home"] + sc["away"]
    out = []   # (points, sentence, component)
    add = lambda pts, text, comp: out.append((pts, text, comp))
    g = c["entertainment"]["parts"]["goals"]
    if goals == 0:
        out.append((0.5, "There were no goals, so goals added nothing to the entertainment score.", "ent"))
    else:
        strength = ("contributed strongly to" if g["value"] >= 0.75 else "contributed to" if g["value"] >= 0.4
                    else "added a little to")
        add(g["points"], f"{plural(goals, 'goal').capitalize()} {strength} the entertainment score "
                         f"({fmt(g['points'])} points).", "ent")
    s = c["entertainment"]["parts"]["shots_on_target"]
    sot = st["shots_on_target"]
    if s and None not in sot:
        tone = "a high count" if s["value"] >= 0.75 else "a low count" if s["value"] <= 0.25 else "a typical count"
        add(s["points"], f"{plural(sum(sot), 'shot').capitalize()} on target, {tone}: {sot_rank(s['value'])} "
                         f"({fmt(s['points'])} points).", "ent")
    share = d["share_within_one_goal"]
    close = c["competitiveness"]["parts"]["within_one_goal"]
    if share >= 0.999:
        add(close["points"], f"The score was never more than one goal apart ({fmt(close['points'])} points).", "comp")
    elif share >= 0.5:
        add(close["points"], f"The score stayed within one goal for {round(100 * share)}% of the match "
                             f"({fmt(close['points'])} points).", "comp")
    else:
        add(close["points"] + 0.01, f"One side was two or more goals clear for {round(100 * (1 - share))}% "
                                    f"of the match, which kept competitiveness down.", "comp")
    mp = c["competitiveness"]["parts"]["margin"]
    margin = abs(sc["home"] - sc["away"])
    if sc["shootout"]:
        add(mp["points"], "It was level after extra time and went to penalties.", "comp")
    elif margin == 0:
        add(mp["points"], f"It finished level ({fmt(mp['points'])} points for the final margin).", "comp")
    elif margin >= 3:
        add(mp["points"] + 0.01, f"The {margin}-goal winning margin earned {fmt(mp['points'])} of a possible "
                                 f"{fmt(c['competitiveness']['max_points'] / 2)} points for a close finish.", "comp")
    for k, f in c["drama"]["factors"].items():
        base = k.replace("aggregate_", "")
        on_agg = " on aggregate" if k.startswith("aggregate_") else ""
        late = (d.get("aggregate") or {}).get("late_goal") if on_agg else d["late_goal"]
        pts = fmt(f["points"])
        if base == "late_goal" and late:
            text = f"A result-changing goal{on_agg} at {minute_label(late['period'], late['minute'])} added {pts} drama points."
        elif base == "comeback":
            text = f"A comeback{on_agg} added {pts} drama points."
        elif base == "equalisers":
            n_eq = (d.get("aggregate") or {}).get("equalisers") if on_agg else d["equalisers"]
            text = f"{plural(n_eq, 'equaliser').capitalize()}{on_agg} added {pts} drama points."
        elif base == "red_cards" and None not in st["red_cards"]:
            text = f"{plural(sum(st['red_cards']), 'red card').capitalize()} added {pts} drama points."
        elif base == "penalties" and st["penalties_awarded"] is not None:
            text = (f"{plural(st['penalties_awarded'], 'penalty', 'penalties').capitalize()} awarded during play "
                    f"added {pts} drama points.")
        elif base == "shootout":
            text = f"The penalty shootout added {pts} drama points."
        else:
            continue
        add(f["points"], text, "drama")
    # the strongest point from each component, in component order, then the next strongest overall, up to four
    out.sort(key=lambda x: -x[0])
    picked = [next(x for x in out if x[2] == comp) for comp in ("ent", "comp", "drama") if any(x[2] == comp for x in out)]
    picked += [x for x in out if x not in picked][:max(0, 4 - len(picked))]
    order = {"ent": 0, "comp": 1, "drama": 2}
    chosen = [t for _, t, _ in sorted(picked, key=lambda x: (order[x[2]], -x[0]))]
    dr = c["drama"]
    if dr["capped"]:
        chosen.append(f"Drama reached its maximum of {fmt(dr['max_points'], 0)} points: its events add up to more "
                      f"than the cap.")
    elif dr["points"] == 0:
        chosen.append("Nothing in the match earned drama points: no late result-changing goal, comeback, equaliser, "
                      "red card, penalty or shootout.")
    if r["quality"]["partial"]:
        miss = [MISSING_TEXT[x] for x in r["quality"]["missing_inputs"]]
        chosen.append("This is a partial rating: " + "; ".join(f"{a.lower()} were not available, which affects "
                                                               f"{b.lower()}" for a, b in miss) + ".")
    return chosen


# ---------------------------------------------------------------- sections
def score_notes(r):
    sc = r["score"]
    notes = []
    if sc["shootout"]:
        notes.append(f"After extra time · {sc['shootout'][0]}–{sc['shootout'][1]} on penalties")
    elif sc["aet"]:
        notes.append("After extra time")
    if sc["first_leg"]:
        fl = sc["first_leg"]
        notes.append(f"Second leg · first leg {r['home']} {fl[0]}–{fl[1]} {r['away']} · aggregate "
                     f"{fl[0] + sc['home']}–{fl[1] + sc['away']}")
    return notes


def _meter(label, value, maximum, text):
    return (f'<div class="gm-meter"><span class="gm-meter__l">{label}</span>'
            f'<span class="gm-meter__track" aria-hidden="true"><span class="gm-meter__fill" '
            f'style="width:{100 * value / maximum:.1f}%"></span></span><span class="gm-meter__v num">{text}</span></div>')


def _part(name, detail, calc, points):
    return (f'<li><span class="gm-parts__n">{name}</span><span class="gm-parts__d">{detail}</span>'
            f'<span class="gm-parts__x num">{calc}</span><span class="gm-parts__p num">{fmt(points)} pts</span></li>')


def breakdown_html(r):
    c, comps, st, d, sc = r["contributions"], r["components"], r["stats"], r["details"], r["score"]
    seg = "".join(f'<span class="gm-bar__seg gm-bar__seg--{k}" style="width:{c[k]["points"]:g}%"></span>'
                  for k in ("entertainment", "competitiveness", "drama"))
    aria = (f'Entertainment {fmt(c["entertainment"]["points"])}, competitiveness {fmt(c["competitiveness"]["points"])}, '
            f'drama {fmt(c["drama"]["points"])}: {fmt(r["match_score"])} of 100 points')
    total = (f'<div class="gm-total"><p class="gm-total__n"><span class="num">{fmt(r["match_score"])}</span>'
             f'<span class="gm-total__of"> / 100 match score</span></p>'
             f'<div class="gm-bar" role="img" aria-label="{aria}">{seg}</div>'
             f'<ul class="gm-key"><li class="gm-key--entertainment">Entertainment</li><li class="gm-key--competitiveness">'
             f'Competitiveness</li><li class="gm-key--drama">Drama</li></ul></div>')

    def block(key, title, desc, parts, caveat=""):
        cc = c[key]
        return (f'<section class="gm-comp gm-comp--{key}" aria-labelledby="gm-{key}-h"><header class="gm-comp__head">'
                f'<h3 id="gm-{key}-h">{title}</h3><span class="gm-comp__w">{round(cc["weight"] * 100)}% weight</span></header>'
                f'<p class="gm-comp__d">{desc}</p>'
                + _meter("Component score", comps[key], 1, f"{comps[key]:.2f}<small> of 1.00</small>")
                + _meter("Points added", cc["points"], cc["max_points"], f"{fmt(cc['points'])}<small> of {fmt(cc['max_points'], 0)}</small>")
                + f'<ul class="gm-parts">{parts}</ul>{caveat}</section>')

    goals = sc["home"] + sc["away"]
    e = c["entertainment"]["parts"]
    ent = _part("Goals", plural(goals, "goal") + (" (shootout kicks not counted)" if sc["shootout"] else ""),
                f"{e['goals']['value']:.2f} × {round(100 * e['goals']['share'])}%", e["goals"]["points"])
    ent_cav = ""
    if e["shots_on_target"]:
        s = e["shots_on_target"]
        scaled = " (scaled to 90 minutes)" if sc["aet"] else ""
        ent += _part("Shots on target", f"{sum(st['shots_on_target'])} in the match{scaled}; {sot_rank(s['value'])}",
                     f"{s['value']:.2f} × {round(100 * s['share'])}%", s["points"])
    else:
        ent_cav = ('<p class="gm-caveat">Shots on target were not available for this match, so entertainment is '
                   'based on goals alone.</p>')
    k = c["competitiveness"]["parts"]
    margin = abs(sc["home"] - sc["away"])
    comp = _part("Final margin", "level" if margin == 0 else f"decided by {plural(margin, 'goal')}",
                 f"{k['margin']['value']:.2f} × {round(100 * k['margin']['share'])}%", k["margin"]["points"])
    comp += _part("Within one goal", f"for {round(100 * k['within_one_goal']['value'])}% of the "
                                     f"{120 if sc['aet'] else 90} minutes (stoppage time not counted)",
                  f"{k['within_one_goal']['value']:.2f} × {round(100 * k['within_one_goal']['share'])}%",
                  k["within_one_goal"]["points"])
    dr = c["drama"]
    dparts = ""
    for key, f in dr["factors"].items():
        base = key.replace("aggregate_", "")
        on_agg = key.startswith("aggregate_")
        name = DRAMA_NAMES.get(base, base) + (" (aggregate)" if on_agg else "")
        src = (d.get("aggregate") or {}) if on_agg else d
        detail = ""
        if base == "late_goal" and src.get("late_goal"):
            detail = "at " + minute_label(src["late_goal"]["period"], src["late_goal"]["minute"])
        elif base == "equalisers":
            detail = plural(src["equalisers"], "equaliser")
        elif base == "red_cards" and None not in st["red_cards"]:
            detail = plural(sum(st["red_cards"]), "red card") + "; counts up to 2"
        elif base == "penalties" and st["penalties_awarded"] is not None:
            detail = plural(st["penalties_awarded"], "penalty", "penalties") + " awarded during play; counts up to 2"
        elif base == "shootout":
            detail = "{}–{}".format(*sc["shootout"])
        elif base == "comeback" and f["value"] > 0.4:
            detail = "won after trailing late, and recovered from two down"
        dparts += _part(name, detail, f"+{f['value']:.2f}", f["points"])
    if not dparts:
        dparts = ('<li class="gm-parts__none">No drama events: no late result-changing goal, comeback, equaliser, '
                  'red card, penalty or shootout.</li>')
    dcav = ""
    if dr["capped"]:
        dcav += (f'<p class="gm-caveat">These events add up to {dr["uncapped_total"]:.2f}. Drama is capped at 1.00, '
                 f'so it adds its maximum {fmt(dr["max_points"], 0)} points.</p>')
    if dr["basis"] == "aggregate":
        dcav += ('<p class="gm-caveat">Second leg: drama was scored on the aggregate score, because that was higher '
                 'than this match on its own.</p>')
    miss = [x for x in r["quality"]["missing_inputs"] if MISSING_TEXT[x][1] == "Drama"]
    if miss:
        dcav += ('<p class="gm-caveat">Not available for this match: '
                 + ", ".join(MISSING_TEXT[x][0].lower() for x in miss) + '. They could not add drama points.</p>')
    return (total + '<div class="gm-comps">'
            + block("entertainment", "Entertainment", "Goals and shots on target.", ent, ent_cav)
            + block("competitiveness", "Competitiveness", "How close the final score was, and how long the match "
                                                          "stayed within one goal.", comp)
            + block("drama", "Drama", "Late result-changing goals, comebacks, equalisers, red cards, penalties and "
                                      "shootouts.", dparts, dcav)
            + '</div><p class="gm-note">A component score runs from 0 to 1. Points added are its share of the '
              '100-point match score (score × weight). The stars come from the match score, using cutoffs fixed on '
              'the 2025/26 season.</p>')


def stats_html(r):
    st, sc = r["stats"], r["score"]

    def row(label, pair, note=""):
        cells = ('<td colspan="2" class="gm-na">Not available</td>' if pair is None or None in pair
                 else f'<td class="num">{pair[0]}</td><td class="num">{pair[1]}</td>')
        return f'<tr><th scope="row">{label}{note}</th>{cells}</tr>'
    rows = row("Goals", [sc["home"], sc["away"]])
    rows += row("Shots on target", st["shots_on_target"])
    rows += row("Red cards", st["red_cards"])
    if st["xg"] is not None:
        rows += row("xG", [f"{st['xg'][0]:.2f}", f"{st['xg'][1]:.2f}"],
                    '<small>Understat · context only, not in the rating</small>')
    else:
        rows += ('<tr><th scope="row">xG<small>context only, never in the rating</small></th>'
                 '<td colspan="2" class="gm-na">Not available for this competition</td></tr>')
    pens = st["penalties_awarded"]
    rows += (f'<tr><th scope="row">Penalties awarded<small>both teams, during play</small></th>'
             f'<td colspan="2" class="num gm-span">{pens if pens is not None else "Not available"}</td></tr>')
    if sc["shootout"]:
        rows += (f'<tr><th scope="row">Penalty shootout<small>not counted as goals</small></th>'
                 f'<td class="num">{sc["shootout"][0]}</td><td class="num">{sc["shootout"][1]}</td></tr>')
    return (f'<div class="gm-tw"><table class="gm-stats"><thead><tr><th scope="col"><span class="sr-only">Statistic'
            f'</span></th><th scope="col">{crest(r.get("home_club_id"), r["home"], 20, "crest--th")}{esc(r["home"])}</th>'
            f'<th scope="col">{crest(r.get("away_club_id"), r["away"], 20, "crest--th")}{esc(r["away"])}</th></tr></thead>'
            f'<tbody>{rows}</tbody></table></div>')


def timeline_html(r):
    """Goals in order with the running score. Omitted, with the reason, unless the goals reproduce the final score."""
    sc, d = r["score"], r["details"]
    goals = sorted(r["stats"]["goals"], key=lambda g: (g["period"], g["minute"]))  # stable: same-minute keeps source order
    if (sum(g["side"] == "h" for g in goals), sum(g["side"] == "a" for g in goals)) != (sc["home"], sc["away"]):
        return '<p class="gm-note">The recorded goals do not add up to the final score, so no timeline is shown.</p>'
    if not goals:
        extra = (" The shootout ended {}–{}; shootout kicks are not goals.".format(*sc["shootout"])
                 if sc["shootout"] else "")
        return f'<p class="gm-note">No goals were scored.{extra}</p>'
    late, agg_late, fl = d["late_goal"], (d.get("aggregate") or {}).get("late_goal"), sc["first_leg"]
    names = {"h": r["home"], "a": r["away"]}
    kinds = {"penalty": "Penalty", "own_goal": "Own goal", "goal": "Goal"}
    ends = {1: "Half-time", 2: "End of normal time" if sc["aet"] else "Full time", 3: "Extra time, half-time",
            4: "End of extra time"}
    h = a = 0
    items = []
    for p in ([1, 2, 3, 4] if sc["aet"] else [1, 2]):
        for g in (x for x in goals if x["period"] == p):
            h, a = h + (g["side"] == "h"), a + (g["side"] == "a")
            kind = kinds.get(g.get("type"), "Goal")
            cid = r.get("home_club_id") if g["side"] == "h" else r.get("away_club_id")
            badge = crest(cid, names[g["side"]], 18, "crest--tl")
            who = f"credited to {badge}{esc(names[g['side']])}" if kind == "Own goal" else badge + esc(names[g["side"]])
            tag = ""
            if late and (late["period"], late["minute"]) == (g["period"], g["minute"]):
                tag = ' <span class="gx-tag">Late Drama</span>'
            elif agg_late and (agg_late["period"], agg_late["minute"]) == (g["period"], g["minute"]):
                tag = ' <span class="gx-tag">Late Drama · aggregate</span>'
            agg = f'<span class="gm-tl__agg num">agg {fl[0] + h}–{fl[1] + a}</span>' if fl else ""
            items.append(f'<li class="gm-tl__ev gm-tl__ev--{g["side"]}"><span class="gm-tl__min num">'
                         f'{minute_label(g["period"], g["minute"])}</span><span class="gm-tl__what"><b>{kind}</b> · '
                         f'{who}{tag}</span><span class="gm-tl__sc num">{h}–{a}</span>{agg}</li>')
        items.append(f'<li class="gm-tl__mark"><span>{ends[p]} · {h}–{a}</span></li>')
    if sc["shootout"]:
        items.append(f'<li class="gm-tl__mark"><span>Penalty shootout · {sc["shootout"][0]}–{sc["shootout"][1]} '
                     f'(not goals)</span></li>')
    src = "ESPN" if r["source"] == "espn" else "Understat"
    return (f'<ol class="gm-tl" aria-label="Goals in order">{"".join(items)}</ol>'
            f'<p class="gm-note">Goals only, from {src}. Minutes can differ by one from broadcast graphics. Red cards '
            + ('are counted in the statistics but not placed here: the league data has no card times.</p>'
               if r["source"] != "espn" else
               'are counted in the statistics but not placed here, so timelines read the same across competitions '
               '(the domestic league data has no card times).</p>'))


def labels_html(r, rules):
    if not r["labels"]:
        return '<p class="gm-note">No match-type labels apply to this match.</p>'
    out = []
    for lab in r["labels"]:
        b, name = lab["because"], lab["label"]
        if name == "Goal Fest":
            here = plural(b["goals"], "goal")
        elif name == "Thriller":
            here = f"{b['stars']:.1f} stars, margin of {b['margin']}, {plural(b['goals'], 'goal')}"
        elif name == "Late Drama":
            here = f"goal at {minute_label(b['period'], b['minute'])}" + (" on aggregate" if b.get("on_aggregate") else "")
        elif name == "Comeback":
            here = "on aggregate" if b.get("on_aggregate") else "within this match"
        elif name == "One-Sided":
            here = f"margin of {b['margin']}"
        elif name == "Chaos":
            here = (f"{plural(b['red_cards'], 'red card')}, {plural(b['penalties'], 'penalty', 'penalties')}, "
                    f"{plural(b['equalisers'], 'equaliser')}, {plural(b['lead_changes'], 'lead change')}")
        elif name == "Hidden Gem":
            here = f"{b['stars']:.1f} stars with {plural(b['goals'], 'goal')}"
        elif name == "Upset":
            here = f"the winner's pre-match chance was {round(100 * b['winner_pre_match_probability'])}% (average closing odds)"
        else:
            here = ""
        q = ("season=" + r["season"] + "&amp;" if r["season"] != "2026" else "") + "label=" + esc(name).replace(" ", "%20")
        out.append(f'<div class="gm-lab"><dt><a class="gx-tag gm-lab__t" href="/football/gallery?{q}" '
                   f'aria-label="{esc(name)}: see all {esc(r["season_label"])} matches with this label">{esc(name)}</a></dt>'
                   f'<dd><span class="gm-lab__rule">{esc(rules.get(name, "").capitalize())}.</span> '
                   f'<span class="gm-lab__here">Here: {esc(here)}.</span></dd></div>')
    return f'<dl class="gm-labs">{"".join(out)}</dl><p class="gm-note">Labels describe the match; they never change its score.</p>'


def details_html(r):
    rows = [("Match ID", r["match_key"]), ("Source record", f"{r['source']} · {r.get('source_id')}")]
    if r.get("rated"):
        rows += [("Rating method", r["method_version"]), ("Calibration", f"{r['calibration_version']} (2025/26, frozen)"),
                 ("Input fingerprint", r["input_hash"]),
                 ("Revision", f"{r['revision']} · rated {r['rated_at_utc'][:10]}")]
    if r["source_flags"]:
        rows.append(("Source notes", " ".join(FLAG_TEXT.get(f, f) for f in r["source_flags"])))
    dl = "".join(f'<div><dt>{esc(k)}</dt><dd>{esc(str(v))}</dd></div>' for k, v in rows)
    return f'<details class="gm-tech"><summary>Technical details</summary><dl>{dl}</dl></details>'


def back_link(r):
    href = "/football/gallery" + ("" if r["season"] == "2026" else f"?season={r['season']}")
    # coming from the gallery: return to the same filters and sort
    return (f'<a class="gm-back" href="{href}" data-back>← Back to the gallery</a>'
            '<script>(function(){var a=document.querySelector("[data-back]");try{var u=new URL(document.referrer);'
            'if(u.origin===location.origin&&u.pathname==="/football/gallery")a.href=u.pathname+u.search;}catch(e){}})();'
            '</script>')


# ---------------------------------------------------------------- pages
def _page(path, title, desc, og_title, ld, body, crumb, footer_date, index=True):
    return (fb_chrome.head(path, title, desc, og_title, "gallery.png", ld, og_type="article", crumb_name=crumb, index=index)
            + "\n<body>\n" + fb_chrome.header(path) + "\n\n" + body + "\n\n" + fb_chrome.footer(footer_date)
            + "\n</body>\n</html>\n")


def _crumbs(season, name):
    q = "" if season == "2026" else f"?season={season}"
    return (f'<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li>'
            f'<li><a href="/football/gallery{q}">Match Gallery</a></li><li aria-current="page">{esc(name)}</li></ol></nav>')


def render_match(r, rules):
    mid = match_id(r["match_key"])
    path = f"/football/gallery/match/{mid}"
    sc = r["score"]
    name = f"{r['home']} {sc['home']}–{sc['away']} {r['away']}"
    date = long_date(r["date"])
    why = why_sentences(r)
    partial = r["quality"]["partial"]
    miss = [MISSING_TEXT[x] for x in r["quality"]["missing_inputs"]]
    badge = (f'<p class="gx-partial gm-partial"><span aria-hidden="true">◐</span> Partial rating · missing '
             f'{esc(", ".join(a.lower() for a, _ in miss))}</p>' if partial else "")
    labels = "".join(f'<li class="gx-tag">{esc(x["label"])}</li>' for x in r["labels"])
    notes = "".join(f'<p class="gm-scorenote">{esc(n)}</p>' for n in score_notes(r))
    so = sc["shootout"]
    hw = so[0] > so[1] if so else sc["home"] > sc["away"]
    aw = so[1] > so[0] if so else sc["away"] > sc["home"]
    status = (f"<b>Partial rating.</b> Missing: " + "; ".join(f"{a.lower()} (affects {b.lower()})" for a, b in miss)
              + ". The rating uses what was available, so it is less certain than a complete one."
              if partial else "<b>Complete rating.</b> Every rating input was available for this match.")
    body = f"""<main id="main" class="gx gm">
{_crumbs(r['season'], name)}
<article class="wrap" aria-labelledby="gm-title">
<header class="gm-head">
  <p class="eyebrow">{esc(r['competition_name'])} <b>·</b> {esc(r['season_label'])} <b>·</b> <time datetime="{esc(r['date'])}">{date}</time></p>
  <h1 id="gm-title" class="gm-score">
    <span class="gm-score__team{' is-win' if hw else ''}">{crest(r.get('home_club_id'), r['home'], 72, 'gm-crest')}<span class="gm-score__name">{esc(r['home'])}</span></span>
    <span class="gm-score__n num"><span class="sr-only">{sc['home']} to {sc['away']}</span><span aria-hidden="true">{sc['home']}–{sc['away']}</span></span>
    <span class="gm-score__team gm-score__team--a{' is-win' if aw else ''}">{crest(r.get('away_club_id'), r['away'], 72, 'gm-crest')}<span class="gm-score__name">{esc(r['away'])}</span></span>
  </h1>
  {notes}
  <div class="gm-rate">{stars_html(r['stars'])}<span class="gm-rate__n num" aria-hidden="true">{r['stars']:.1f}</span><span class="gm-rate__t">Match Entertainment Rating</span></div>
  {badge}
  {f'<ul class="gx-tags gm-tags" aria-label="Match types">{labels}</ul>' if labels else ''}
  {back_link(r)}
</header>

<section class="gm-sec gm-why" aria-labelledby="gm-why-h">
  <h2 id="gm-why-h" class="gx-h2">Why {r['stars']:.1f} stars</h2>
  <ul class="gm-why__list">{''.join(f'<li>{esc(s)}</li>' for s in why)}</ul>
</section>

<section class="gm-sec" aria-labelledby="gm-break-h">
  <h2 id="gm-break-h" class="gx-h2">How the rating adds up</h2>
  {breakdown_html(r)}
</section>

<div class="gm-two">
<section class="gm-sec" aria-labelledby="gm-tl-h">
  <h2 id="gm-tl-h" class="gx-h3">Goals</h2>
  {timeline_html(r)}
</section>
<section class="gm-sec" aria-labelledby="gm-st-h">
  <h2 id="gm-st-h" class="gx-h3">Match statistics</h2>
  {stats_html(r)}
</section>
</div>

<section class="gm-sec" aria-labelledby="gm-lab-h">
  <h2 id="gm-lab-h" class="gx-h3">Labels</h2>
  {labels_html(r, rules)}
</section>

<section class="gm-sec gm-data" aria-labelledby="gm-data-h">
  <h2 id="gm-data-h" class="gx-h3">About this rating</h2>
  <ul class="gm-data__list">
    <li>{status}</li>
    <li>The stars are a data-driven entertainment heuristic built from goals, shots on target, how close the score stayed and match events. They are not a judgement of football quality.</li>
    <li>xG is shown for context only and is not part of the rating.</li>
    <li>Data: {esc(r['attribution'])}. {CREST_NOTE}</li>
  </ul>
  {details_html(r)}
</section>
</article>
</main>"""
    desc = (f"{name} · {r['competition_name']}, {date}. Rated {r['stars']:.1f} of 5 for entertainment. "
            + " ".join(why[:2]))
    ld = {"@context": "https://schema.org", "@type": "SportsEvent", "name": f"{r['home']} v {r['away']}",
          "startDate": r.get("kickoff_utc") or r["date"], "sport": "Football",
          "homeTeam": {"@type": "SportsTeam", "name": r["home"]}, "awayTeam": {"@type": "SportsTeam", "name": r["away"]},
          "superEvent": {"@type": "SportsEvent", "name": f"{r['competition_name']} {r['season_label']}"},
          "url": fb_chrome.SITE + path}
    title = f"{name} · {r['competition_name']}, {date} · {r['stars']:.1f}★ Match Gallery"
    return mid, _page(path, title, desc, f"{name} · {r['stars']:.1f}★", ld, body, name, long_date(r["rated_at_utc"][:10]))


def render_unrated(r):
    mid = match_id(r["match_key"])
    path = f"/football/gallery/match/{mid}"
    name = f"{r['home']} v {r['away']}"
    date = long_date(r["date"])
    why = r["eligibility"].split(":", 1)[1]
    flags = "".join(f"<li>{esc(FLAG_TEXT.get(f, f))}</li>" for f in r["source_flags"])
    body = f"""<main id="main" class="gx gm">
{_crumbs(r['season'], name)}
<article class="wrap" aria-labelledby="gm-title">
<header class="gm-head">
  <p class="eyebrow">{esc(r['competition_name'])} <b>·</b> {esc(r['season_label'])} <b>·</b> <time datetime="{esc(r['date'])}">{date}</time></p>
  <h1 id="gm-title" class="gm-score gm-score--unrated">
    <span class="gm-score__team">{crest(r.get('home_club_id'), r['home'], 72, 'gm-crest')}<span class="gm-score__name">{esc(r['home'])}</span></span><span class="gm-score__v">v</span><span class="gm-score__team gm-score__team--a">{crest(r.get('away_club_id'), r['away'], 72, 'gm-crest')}<span class="gm-score__name">{esc(r['away'])}</span></span>
  </h1>
  <p class="gm-unrated-badge">Not rated</p>
  {back_link(r)}
</header>
<section class="gm-sec" aria-labelledby="gm-un-h">
  <h2 id="gm-un-h" class="gx-h3">Why this match has no rating</h2>
  <p class="gm-lead">{esc(UNRATED_REASON.get(why, 'This match is not rated.'))}</p>
  {f'<ul class="gm-data__list">{flags}</ul>' if flags else ''}
  <p class="gm-note">No score, statistics or rating are shown, because they are not reliable for this match. It is not included in any ranking. If the sources are corrected, it will be rated in a later update.</p>
  {details_html(r)}
</section>
</article>
</main>"""
    desc = f"{name} · {r['competition_name']}, {date}. Not rated: {UNRATED_REASON.get(why, '')}"
    ld = {"@context": "https://schema.org", "@type": "SportsEvent", "name": name, "startDate": r["date"],
          "sport": "Football", "url": fb_chrome.SITE + path}
    return mid, _page(path, f"{name} · {r['competition_name']}, {date} · Match Gallery", desc, name, ld, body, name,
                      long_date(r["rated_at_utc"][:10]), index=False)


def render_not_found():
    path = "/football/gallery/match-not-found"
    body = r"""<main id="main" class="gx gm">
<nav class="crumbs wrap" aria-label="Breadcrumb"><ol><li><a href="/football">Home</a></li><li><a href="/football/gallery">Match Gallery</a></li><li aria-current="page">Match not found</li></ol></nav>
<article class="wrap gm-nf" aria-labelledby="gm-nf-h">
  <h1 id="gm-nf-h" class="gx-h2">We can’t find that match</h1>
  <p class="gm-lead" id="gm-nf-id">There is no match at this address in the gallery.</p>
  <p class="gm-note">Match addresses look like <code>/football/gallery/match/la-liga-2026-us-30844</code>. The link may be mistyped, or the match may not have been played and rated yet.</p>
  <p><a class="btn" href="/football/gallery">Browse the gallery <span class="arr" aria-hidden="true">→</span></a></p>
</article>
</main>
<script>(function(){var m=location.pathname.match(/\/football\/gallery\/match\/([^/]+)/);if(m){var t=m[1];try{t=decodeURIComponent(t)}catch(e){}document.getElementById("gm-nf-id").textContent="There is no match “"+t.slice(0,80)+"” in the gallery.";}})();</script>"""
    ld = {"@context": "https://schema.org", "@type": "WebPage", "name": "Match not found", "url": fb_chrome.SITE + path}
    return _page(path, "Match not found · Match Gallery", "This match is not in the Football Match Gallery.",
                 "Match not found", ld, body, "Match not found", "—", index=False)
