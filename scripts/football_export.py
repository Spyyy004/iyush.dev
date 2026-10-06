"""Split the research pipeline's site/data.json into the frontend datasets under football/data/.

The frontend never reproduces the pipeline (M0 §22): it only reads these precomputed outputs.
Source: ~/dev/weather_football/site/data.json (rebuilt weekly by that project's pipeline).

    python3 scripts/football_export.py [path/to/data.json]

Stdlib only. Values are copied as-is; nothing is recomputed or rounded for display here.
"""
import json
import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else Path.home() / "dev/weather_football/site/data.json")
OUT = Path(__file__).resolve().parents[1] / "football" / "data"

d = json.loads(SRC.read_text())
s4, s5 = d["s4"], d["s5"]


def dump(name, obj):
    path = OUT / name
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    print(f"{name:18} {path.stat().st_size / 1024:8.1f} KB")


OUT.mkdir(parents=True, exist_ok=True)

# Research pages, live tracker, homepage live strip: every Study 2/3 table + the small Study 4/5 tables.
research = {k: v for k, v in d.items() if k.startswith(("s2_", "s3_"))}
research["tracker"] = d.get("tracker")
research["s4"] = {k: s4[k] for k in ("season", "season_label", "through", "metrics", "roles", "bruno", "creators",
                                     "role_codes", "retrieval", "validation")}
research["s5"] = {k: v for k, v in s5.items() if k not in ("params", "players", "clubs", "board", "moves")}
dump("research.json", research)

# Similarity tool (M3): precomputed by scripts/build_similarity.py with the Study 4 engine — not exported here.

# Transfer calculator (M4): precomputed by scripts/build_transfer.py with the Study 5 production model — not exported here.

# Manchester United 2024 case study: the leakage-free recruitment board.
dump("case-study.json", {"board": s5["board"]})

meta = {"source": str(SRC.name), "tracker_generated_utc": (d.get("tracker") or {}).get("generated_utc"),
        "profiles_through": s4["through"], "profiles_season": s4["season_label"],
        "transfer_inputs_season": s5["pre_season"]}
dump("meta.json", meta)
