"""analyze_full_run.py — Analyze PAPER35 full_run (4 local models x 3 seeds x 100 scenarios).

Questions:
 Q1 seed-level reproducibility (BDS across seeds, temperature=0 => near-zero = stable)
 Q2 cross-model heterogeneity (BDS between model families per scenario)
 Q3 category-level patterns (L/A/M/T)
"""
from __future__ import annotations
import json, csv
from collections import defaultdict
from itertools import combinations
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from bds_evaluator import _bds

RAW = Path(r"F:\Research\PAPER35_FRONT_DRIFT\experiments\full_run\raw")
OUT = Path(r"F:\Research\PAPER35_FRONT_DRIFT\experiments\full_run\analysis")
OUT.mkdir(parents=True, exist_ok=True)

def load_files():
    # model -> seed -> scenario_id -> text
    data = {}
    for f in sorted(RAW.glob("ollama-multi__*.jsonl")):
        parts = f.stem.split("__")  # ollama-multi, model, seedN
        model = parts[1]
        seed = int(parts[2].replace("seed", ""))
        rows = {}
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                rows[r["scenario_id"]] = r.get("text", "") or ""
        data.setdefault(model, {})[seed] = rows
    return data

def category_of(sid):
    return sid.split("-")[0]

def main():
    data = load_files()
    models = sorted(data)
    seeds = sorted(next(iter(data.values())))
    all_sids = sorted({sid for m in models for s in data[m].values() for sid in s})
    print(f"models={models} seeds={seeds} scenarios={len(all_sids)}")

    # Q1: seed reproducibility BDS per model per scenario (3 pairs of seeds)
    q1 = {}
    for m in models:
        per_sid = {}
        for sid in all_sids:
            outs = {s: [data[m][s][sid]] for s in seeds if sid in data[m][s]}
            if len(outs) >= 2:
                per_sid[sid] = _bds(outs)
        q1[m] = per_sid
    q1_means = {m: float(np.mean(list(v.values()))) for m, v in q1.items() if v}
    print("\nQ1 seed-reproducibility mean BDS per model:", q1_means)

    # Q2: cross-model BDS per scenario (seed0), mean over 6 model pairs
    q2 = {}
    for sid in all_sids:
        texts = {}
        for m in models:
            if sid in data[m][0]:
                texts[m] = [data[m][0][sid]]
        if len(texts) >= 2:
            kls = []
            for a, b in combinations(texts.keys(), 2):
                kls.append(_bds({a: texts[a], b: texts[b]}))
            q2[sid] = float(np.mean(kls))
    q2_by_cat = defaultdict(list)
    for sid, v in q2.items():
        q2_by_cat[category_of(sid)].append(v)
    print("\nQ2 cross-model heterogeneity:")
    for c in sorted(q2_by_cat):
        vals = q2_by_cat[c]
        print(f"  {c}: n={len(vals)} mean={np.mean(vals):.4f} median={np.median(vals):.4f}")

    # Q3: per-category reproducibility (Q1 aggregated)
    cats = sorted({category_of(sid) for sid in all_sids}); q1_by_cat = {c: [] for c in cats}
    for m in models:
        for sid, v in q1[m].items():
            q1_by_cat[category_of(sid)].append(v)

    result = {
        "q1_seed_reproducibility": {m: {"mean_bds": q1_means[m], "n": len(q1[m])} for m in models},
        "q1_by_category": {c: {"mean_bds": float(np.mean(v)), "median_bds": float(np.median(v)), "n": len(v)} for c, v in q1_by_cat.items() if v},
        "q2_cross_model": {
            "mean_bds": float(np.mean(list(q2.values()))) if q2 else None,
            "by_category": {c: {"mean_bds": float(np.mean(v)), "median_bds": float(np.median(v)), "n": len(v)} for c, v in q2_by_cat.items()},
            "worst_scenarios": sorted(q2.items(), key=lambda kv: -kv[1])[:10],
            "most_similar_scenarios": sorted(q2.items(), key=lambda kv: kv[1])[:10],
        },
    }
    with (OUT / "full_run_analysis.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    with (OUT / "cross_model_bds.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["scenario_id", "category", "cross_model_bds"])
        for sid in sorted(q2):
            w.writerow([sid, category_of(sid), f"{q2[sid]:.4f}"])
    print(f"\nwrote {OUT / 'full_run_analysis.json'} and cross_model_bds.csv")

if __name__ == "__main__":
    main()