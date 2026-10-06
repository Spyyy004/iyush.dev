#!/usr/bin/env python3
"""Precompute every Similarity Explorer result with the Study 4 engine itself (M3 §28–29).

Runs inside the research project's environment, because it imports the research code:

    ~/dev/weather_football/.venv/bin/python scripts/build_similarity.py

Nothing is re-implemented here: rankings, scores and robustness come from src/study4/similarity.Engine (the four-window x
cosine/Euclidean engine of the Bruno case study, src/study4/bruno.py), per-metric z-scores from the same engine's
standardised profiles, and the match language from the case study's own rules (|Δz| ≤ 0.5 similar, ≤ 1.0 moderately
similar, else different; a group is "close" when its mean |Δz| ≤ 0.5; "higher/lower" when the group's mean Δz > 0.75).
The browser only looks results up.

Ranking (per player × destination league × profile window) follows Engine.find's own sort: profiles that are robust
across all eight checks first, then the median similarity score under the chosen window's two algorithms.

Writes football/data/sim/: meta.json, players.json (search index), z/<league>_<window>.json (profiles shown in
comparisons) and r/<key>.json (one small file per player with every league × window result).
"""
import json
import os
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
RESEARCH = Path(os.environ.get("FB_RESEARCH", Path.home() / "dev/weather_football"))
sys.path.insert(0, str(RESEARCH))
os.chdir(RESEARCH)

import numpy as np  # noqa: E402
from src.study4 import bruno as B  # noqa: E402  (case-study GROUPS + engine settings)
from src.study4 import similarity as S  # noqa: E402

SEASON = "2025"            # profiles as of 2025/26: the last complete season, as in the frozen Study 4 case study
SEASON_LABEL = "2025/26"
ENGINE_WINDOWS = ("w3", "w2", "recent2500", "w1")   # bruno.py main(): all four windows x cosine / Euclidean = 8 checks
UI_WINDOWS = {"w1": 1, "w2": 2, "w3": 3}            # M3 §5: 1, 2 or 3 seasons
MIN_MINUTES = 900                                    # Engine pool threshold; also required of the query profile
K = 10
LEAGUES = ["EPL", "La_Liga", "Serie_A", "Bundesliga", "Ligue_1"]
OUT = SITE / "football/data/sim"


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def r2(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 2)


def main():
    t0 = time.time()
    e = S.Engine(windows=ENGINE_WINDOWS)
    roles = sorted({r for win in UI_WINDOWS for r in e.w[win]["role"].unique()})

    # ---- every 2025/26 profile with >= 900 minutes, per window: the population shown in comparisons ----
    keyed, z_tables = {}, {}
    for win in UI_WINDOWS:
        w, z = e.w[win], e.z[win]
        sel = w[(w["season"] == SEASON) & (w["minutes"] >= MIN_MINUTES)]
        for i, row in sel.iterrows():
            key = f'{int(row["player_id"])}-{row["league"]}'
            p = keyed.setdefault(key, {"pid": int(row["player_id"]), "league": row["league"], "name": row["player"],
                                       "team": str(row["team"]).split(" / ")[-1], "role": row["role"], "win": {}})
            p["win"][win] = {"minutes": int(row["minutes"]), "idx": int(i)}
            if win == "w3" or "role_w" not in p:
                p["role"], p["role_w"] = row["role"], win
            z_tables.setdefault((row["league"], win), {})[key] = [r2(v) for v in z.loc[i].to_numpy()]

    # ---- slugs for shareable URLs: name, then name + league / id when needed ----
    by_slug = {}
    for key, p in sorted(keyed.items(), key=lambda kv: -max(x["minutes"] for x in kv[1]["win"].values())):
        s = slugify(p["name"])
        if s in by_slug:
            s = f'{s}-{slugify(p["league"])}'
        if s in by_slug:
            s = f'{s}-{p["pid"]}'
        by_slug[s] = key
        p["slug"] = s

    # ---- results: Engine.find for every query player x destination league ----
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "r").mkdir(parents=True)
    (OUT / "z").mkdir()
    n_q = 0
    for key, p in keyed.items():
        res = {}
        for tgt in LEAGUES:
            g = e.find(p["pid"], p["league"], SEASON, tgt, k=K)
            if g.empty:
                res[tgt] = {"pool": 0}
                continue
            st = g.attrs["spec_table"]
            robust = dict(zip(g["player_id"], g["robust"]))
            limited = dict(zip(g["player_id"], g["evidence"] != "full"))
            team = dict(zip(g["player_id"], g["team"]))
            out = {"pool": int(g.attrs["pool"]), "checks": int(g.attrs["specs"]), "small": bool(g["small_pool"].iloc[0])}
            for win in UI_WINDOWS:
                if win not in p["win"]:
                    continue
                sw = st[st["spec"].str.startswith(win + "/")]
                if sw.empty:
                    out[win] = []
                    continue
                agg = sw.groupby("player_id").agg(med=("score", "median"), mn=("score", "min"), pool=("pool", "max"))
                agg["robust"] = agg.index.map(lambda i: bool(robust.get(i, False)))
                agg = agg.sort_values(["robust", "med", "mn"], ascending=False).head(K)
                rows = []
                for cid, a in agg.iterrows():
                    ck = f"{int(cid)}-{tgt}"
                    if ck not in keyed or win not in keyed[ck]["win"]:
                        continue  # candidate lacks a >=900-min profile in this window (cannot happen for pool members)
                    rows.append([ck, round(float(a["med"]), 1), round(float(a["mn"]), 1), int(a["robust"]), int(limited.get(cid, False))])
                out[win] = rows
                out[win + "_pool"] = int(agg["pool"].max()) if len(agg) else 0
            res[tgt] = out
        (OUT / "r" / f"{key}.json").write_text(json.dumps({"key": key, "res": res}, separators=(",", ":"), ensure_ascii=False))
        n_q += 1

    for (lg, win), tab in z_tables.items():
        (OUT / "z" / f"{lg}_{win}.json").write_text(json.dumps(tab, separators=(",", ":")))

    players = [[k, p["name"], p["team"], p["league"], roles.index(p["role"]), p["slug"],
                {w: p["win"][w]["minutes"] for w in UI_WINDOWS if w in p["win"]}] for k, p in keyed.items()]
    players.sort(key=lambda r: r[1])
    (OUT / "players.json").write_text(json.dumps(players, separators=(",", ":"), ensure_ascii=False))

    meta = {
        "season": SEASON_LABEL, "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "engine": "src/study4/similarity.py Engine, windows " + ", ".join(ENGINE_WINDOWS) + " × cosine, Euclidean",
        "metrics": S.NAMES, "groups": {g: [S.NAMES.index(m) for m in ms] for g, ms in B.GROUPS.items()},
        "roles": roles, "leagues": LEAGUES, "windows": UI_WINDOWS, "min_minutes": MIN_MINUTES, "k": K,
        "rules": {"similar": 0.5, "moderate": 1.0, "group_close": 0.5, "group_diff": 0.75, "robust_score": 90},
        "players": len(players),
    }
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1, ensure_ascii=False))
    size = sum(f.stat().st_size for f in OUT.rglob("*.json"))
    print(f"similarity: {n_q} players × {len(LEAGUES)} leagues × {len(UI_WINDOWS)} windows; "
          f"{size / 1e6:.1f} MB in {OUT.relative_to(SITE)}; {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
