#!/usr/bin/env python3
"""Precompute every Transfer Calculator prediction with the Study 5 production model (M4 §26).

Runs inside the research project's environment, because it imports the research code:

    ~/dev/weather_football/.venv/bin/python scripts/build_transfer.py

Nothing is re-implemented: the model is src/study5/site_export.production() (Model A refitted on all 428 primary moves,
uncertainty from its out-of-sample errors), players and destination clubs come from the same module's players() and
clubs(), predictions from the fitted statsmodels object and transferability_model.predictive(). The "why" breakdown is
the model's own terms (site_export.engine_params) and the build fails unless the terms add up to the prediction.

Writes football/data/transfer/: index.json (players, clubs, model facts) and p/<key>.json (one per player:
predictions for every club in the other four leagues + the player's model terms).
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
import pandas as pd  # noqa: E402
from src.study5 import audit as A  # noqa: E402
from src.study5 import recruitment as RC  # noqa: E402
from src.study5 import site_export as SE  # noqa: E402
from src.study5 import transferability_model as M  # noqa: E402

OUT = SITE / "football/data/transfer"
LEAGUES = SE.LEAGUES
FEATS = ["pre", "pre3", "n_hist", "age_c", "log_pre_min", "origin_strength"]


def slugify(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def r4(x):
    return None if x is None or pd.isna(x) else round(float(x), 4)


def main():
    t0 = time.time()
    d, fit, em = SE.production()
    pm, roles = A.load()
    P = SE.players(pm, roles).reset_index(drop=True)
    C = pd.DataFrame(SE.clubs(pm))
    prm = SE.engine_params(fit, em)

    # ---- every player x every club outside his league: one batch through the fitted model ----
    pairs = []
    for i, pl in P.iterrows():
        for j, cl in C[C["l"] != pl["origin_league"]].iterrows():
            pairs.append((i, j))
    pi, ci = map(np.array, zip(*pairs))
    X = P.iloc[pi].reset_index(drop=True).copy()
    for col in FEATS:
        X[col] = X[col].astype(float)
    X["destination_league"] = C["l"].to_numpy()[ci]
    X["dest_strength"] = C["s"].to_numpy()[ci].astype(float)
    X["promoted"] = C["p"].to_numpy()[ci].astype(int)
    pred = fit.predict(X).reset_index(drop=True)
    pq = M.predictive(pred, X["rg"].reset_index(drop=True), X["pre"].reset_index(drop=True), em)
    p75 = pq["p_ret75"].where(X["pre"].reset_index(drop=True) >= RC.RET_FLOOR)   # research rule: not shown below the floor

    # ---- the model's own terms (engine_params): player part + destination part, checked against fit.predict ----
    def player_terms(r):
        g, ac = r["rg"], float(r["age_c"])
        return {"role": prm["rg"][g], "last": prm["pre"][g] * float(r["pre"]), "level3": prm["pre3"][g] * float(r["pre3"]),
                "history": prm["nhist"] * float(r["n_hist"]), "origin": prm["origin"][r["origin_league"]],
                "age": prm["age"] * ac + prm["age2"] * ac * ac, "minutes": prm["logmin"] * float(r["log_pre_min"]),
                "origin_club": prm["ostr"] * float(r["origin_strength"])}

    def club_terms(c):
        return {"dest": prm["dest"][c["l"]], "dest_club": prm["dstr"] * float(c["s"]) + prm["promoted"] * int(c["p"])}

    PT = [player_terms(r) for _, r in P.iterrows()]
    CT = [club_terms(c) for _, c in C.iterrows()]
    total = np.array([sum(PT[a].values()) + sum(CT[b].values()) for a, b in zip(pi, ci)])
    err = np.abs(total - pred.to_numpy()).max()
    if err > 1e-9:
        sys.exit(f"model terms do not add up to the prediction (max error {err:.2e})")

    # ---- cross-check against the research's own engine fixture (Python predictions for random pairs) ----
    fx_path = SE.T / "m9_engine_fixture.json"
    fx_note = "fixture not found"
    if fx_path.exists():
        fx = json.load(open(fx_path))
        look = {(a, b): k for k, (a, b) in enumerate(zip(pi, ci))}
        diffs = []
        for case in fx["cases"]:
            k = look.get((case["player"], case["club"]))
            if k is not None:
                diffs += [abs(pred[k] - case["pred"]), abs(pq["q10"][k] - case["q10"]), abs(pq["q90"][k] - case["q90"])]
        fx_note = f"{len(diffs) // 3} fixture cases, max abs diff {max(diffs):.2e}" if diffs else "no overlapping fixture cases"
        if diffs and max(diffs) > 1e-6:
            sys.exit("predictions differ from the research fixture: " + fx_note)

    # ---- slugs: reuse the Similarity Explorer's where the same player-league exists, so the tools link ----
    sim = SITE / "football/data/sim-2025/players.json"  # same season as the calculator's inputs
    sim_slug = {r[0]: r[5] for r in json.load(open(sim))} if sim.exists() else {}
    used, slugs = set(), []
    for _, r in P.iterrows():
        key = f'{int(r["player_id"])}-{r["origin_league"]}'
        s = sim_slug.get(key) or slugify(r["player"])
        if s in used:
            s = f'{s}-{slugify(r["origin_league"])}'
        used.add(s)
        slugs.append(s)

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "p").mkdir(parents=True)
    by_player = {}
    for k, (a, b) in enumerate(zip(pi, ci)):
        by_player.setdefault(a, {})[int(b)] = [r4(pred[k]), r4(pq["q10"][k]), r4(pq["q90"][k]), r4(p75[k])]
    players = []
    for a, r in P.iterrows():
        key = f'{int(r["player_id"])}-{r["origin_league"]}'
        doc = {"key": key, "pre": r4(r["pre"]), "pre3": r4(r["pre3"]), "xg": r4(r["xg90"]), "xa": r4(r["xa90"]),
               "age": r4(r["age_at_move"]), "terms": {k: r4(v) for k, v in PT[a].items()}, "pred": by_player[a]}
        (OUT / "p" / f"{key}.json").write_text(json.dumps(doc, separators=(",", ":"), ensure_ascii=False))
        players.append([key, r["player"], str(r["origin_club"]), r["origin_league"], r["role"], slugs[a],
                        int(r["n_hist"]), int(r["pre_minutes"]), r4(r["pre"])])
    players.sort(key=lambda x: x[1])
    clubs = [[c["l"], c["c"], r4(c["s"]), int(c["p"]), {k: r4(v) for k, v in CT[j].items()}] for j, c in C.iterrows()]
    index = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": "Study 5 Model A, refitted on all primary moves (src/study5/site_export.production)",
        "n_fit": int(len(d)), "pre_season": SE.config.season_label(SE.PRE_SEASON), "dest_season": SE.config.season_label(SE.DEST_SEASON),
        "min_minutes": A.PRIMARY_MIN, "scope_roles": A.SCOPE_ROLES, "ret_floor": RC.RET_FLOOR, "leagues": LEAGUES,
        "players": players, "clubs": clubs, "checks": {"terms_max_error": float(err), "fixture": fx_note},
    }
    (OUT / "index.json").write_text(json.dumps(index, separators=(",", ":"), ensure_ascii=False))
    size = sum(f.stat().st_size for f in OUT.rglob("*.json"))
    print(f"transfer: {len(players)} players × {len(C)} clubs → {len(pairs):,} predictions; terms check {err:.1e}; {fx_note}; "
          f"{size / 1e6:.1f} MB; {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
