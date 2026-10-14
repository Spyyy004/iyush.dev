#!/usr/bin/env python3
"""Independent check of the season rankings and club insights pages' data (gallery M4).

Recomputes, from the gallery's own season export (football/data/gallery/<season>.json: one row per rated match),
every club's sample size, complete/partial split, mean, median, 4-star count, label counts and best match; every
leaderboard's membership, order, ranks and ties; and the membership and order of the discovery lists. Then compares
them with football/data/gallery/{rankings,clubs}_<season>.json (copied from the research build). Stdlib only.

    python3 scripts/check_gallery_insights.py
"""
import json
import statistics
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "football" / "data" / "gallery"
LABELS = ["Thriller", "Goal Fest", "Late Drama", "Comeback", "Chaos", "Hidden Gem", "One-Sided"]
BOARDS = {"entertaining": None, "chaotic": "Chaos", "late_drama": "Late Drama", "one_sided": "One-Sided",
          "hidden_gems": "Hidden Gem"}
problems = []


def need(cond, what):
    if not cond:
        problems.append(what)


def neg_date(d):
    return tuple(-int(x) for x in d.split("-"))


def tail(m):
    return (-m["sc"], neg_date(m["d"]), m["k"])


def check_season(season):
    rows = json.loads((DATA / f"{season}.json").read_text())
    rank = json.loads((DATA / f"rankings_{season}.json").read_text())
    clubs = json.loads((DATA / f"clubs_{season}.json").read_text())
    th = clubs["meta"]["thresholds"]
    need(th == {"average": 10, "label_rate": 15, "list": 5}, f"{season}: thresholds changed: {th}")
    need(rank["meta"]["season"] == clubs["meta"]["season"] == season, f"{season}: files are for another season")
    rated = rows["matches"]
    unrated_keys = {u["k"] for u in rows["unrated"]}
    for scope_name, sc in clubs["scopes"].items():
        ms = [m for m in rated if scope_name == "all" or m["c"] == scope_name]
        tag = f"{season}/{scope_name}"
        need(sc["rated"] == len(ms), f"{tag}: rated count {sc['rated']} vs {len(ms)}")
        per = {}
        for m in ms:
            need(m["hc"] != m["ac"], f"{m['k']}: same club both sides")
            for cid in {m["hc"], m["ac"]}:
                per.setdefault(cid, []).append(m)
        got = {c["club_id"]: c for c in sc["clubs"]}
        need(set(got) == set(per), f"{tag}: club set differs ({len(got)} vs {len(per)})")
        for cid, cm in per.items():
            c = got.get(cid)
            if not c:
                continue
            scores = [m["sc"] for m in cm]
            exp = {"n": len(cm), "n_partial": sum(m["p"] is not None for m in cm),
                   "n_complete": sum(m["p"] is None for m in cm), "mean": round(statistics.fmean(scores), 2),
                   "median": round(statistics.median(scores), 2), "n_4plus": sum(m["st"] >= 4 for m in cm)}
            for k, v in exp.items():
                need(c[k] == v, f"{tag} {cid} {k}: {c[k]} vs {v}")
            for lab in LABELS:
                need(c["labels"][lab] == sum(lab in m["lb"] for m in cm), f"{tag} {cid} label {lab}")
            need(c["best"]["k"] == min(cm, key=tail)["k"], f"{tag} {cid} best match")
            need(c["european_only"] == cid.startswith("espn:"), f"{tag} {cid} european_only")
        # leaderboards, recomputed
        for key, lab in BOARDS.items():
            b = sc["leaderboards"][key]
            t = th["average"] if lab is None else th["label_rate"]
            need(b["threshold"] == t, f"{tag} {key} threshold")
            cs = [got[c] for c in per]
            excluded = [c for c in cs if scope_name == "all" and c["european_only"] and c["n"] >= t]
            need({x["club_id"] for x in b["european_only_excluded"]} == {c["club_id"] for c in excluded},
                 f"{tag} {key} european-only exclusions")
            q = [c for c in cs if c["n"] >= t and c not in excluded]
            if lab is None:
                q.sort(key=lambda c: (-c["mean"], -c["n"], c["club_id"]))
                prim = lambda c: c["mean"]
            else:
                q.sort(key=lambda c: (-(c["labels"][lab] / c["n"]), -c["labels"][lab], -c["n"], c["club_id"]))
                prim = lambda c: c["labels"][lab] / c["n"]
            need([r["club_id"] for r in b["rows"]] == [c["club_id"] for c in q], f"{tag} {key} order")
            ranks, prev, r_ = [], None, 0
            for i, c in enumerate(q, 1):
                if prim(c) != prev:
                    r_, prev = i, prim(c)
                ranks.append(r_)
            need([r["rank"] for r in b["rows"]] == ranks, f"{tag} {key} ranks")
            for r in b["rows"]:
                need(r["tied"] == (ranks.count(r["rank"]) > 1), f"{tag} {key} tie flag {r['club_id']}")
                if lab is not None:
                    need(r["count"] == got[r["club_id"]]["labels"][lab] and r["n"] == got[r["club_id"]]["n"],
                         f"{tag} {key} numerator/denominator {r['club_id']}")
            need({x["club_id"] for x in b["below"]} == {c["club_id"] for c in cs if c["n"] < t}, f"{tag} {key} below")
            need(b["n_qualifying"] == len(q) and b["matches_used"] == sum(c["n"] for c in q), f"{tag} {key} totals")
    for scope_name, sc in rank["scopes"].items():
        ms = [m for m in rated if scope_name == "all" or m["c"] == scope_name]
        tag = f"{season}/{scope_name}"
        lists = sc["lists"]
        expect = {
            "highest_rated": sorted(ms, key=tail),
            "highest_scoring": sorted(ms, key=lambda m: (-(m["hg"] + m["ag"]),) + tail(m)),
            "comebacks_late_drama": sorted((m for m in ms if {"Comeback", "Late Drama"} & set(m["lb"])), key=tail),
            "hidden_gems": sorted((m for m in ms if "Hidden Gem" in m["lb"]), key=tail),
        }
        for key, exp in expect.items():
            l = lists[key]
            need(l["n_eligible"] == len(exp), f"{tag} {key} eligible {l['n_eligible']} vs {len(exp)}")
            need(l["available"] == (len(exp) >= 5), f"{tag} {key} availability")
            if l["available"]:
                need([m["k"] for m in l["shown"]] == [m["k"] for m in exp[:25]], f"{tag} {key} order")
        for key, lab in (("most_chaotic", "Chaos"), ("most_one_sided", "One-Sided")):
            need(lists[key]["n_eligible"] == sum(lab in m["lb"] for m in ms), f"{tag} {key} eligible")
        need(lists["closest_finishes"]["n_eligible"] == sum(abs(m["hg"] - m["ag"]) <= 1 for m in ms),
             f"{tag} closest eligible")
        for l in lists.values():
            for m in l["shown"]:
                need(m["k"] not in unrated_keys, f"{tag}: unrated match {m['k']} in a ranking")
                need(scope_name == "all" or m["c"] == scope_name, f"{tag}: other competition in list")
                need(m["k"].split("-")[1] == season, f"{tag}: other season's match {m['k']}")


for s in ("2026", "2025"):
    check_season(s)
if problems:
    print("\n".join(problems[:40]))
    sys.exit(f"check_gallery_insights: {len(problems)} problems")
print("check_gallery_insights: every club figure, leaderboard and list matches an independent recomputation")
