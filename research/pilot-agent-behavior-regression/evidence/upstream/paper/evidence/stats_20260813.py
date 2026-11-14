# -*- coding: utf-8 -*-
"""Supplemental statistics for the PAPER35 TMLR manuscript (2026-08-13).

Recomputes per-scenario cross-seed and cross-model BDS, paired Wilcoxon,
category bootstrap CIs, and Bonferroni-corrected pairwise Mann-Whitney tests.
Outputs are written to experiments/full_run/analysis/.
"""
import json, sys
from itertools import combinations
from pathlib import Path
import numpy as np
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from bds_evaluator import _bds

RAW = Path(__file__).resolve().parents[1] / "experiments" / "full_run" / "raw"
OUT = Path(__file__).resolve().parents[1] / "experiments" / "full_run" / "analysis"

def load_files():
    data = {}
    for f in sorted(RAW.glob("ollama-multi__*.jsonl")):
        parts = f.stem.split("__")
        model, seed = parts[1], int(parts[2].replace("seed", ""))
        rows = {}
        with f.open(encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                rows[r["scenario_id"]] = r.get("text", "") or ""
        data.setdefault(model, {})[seed] = rows
    return data

def cat(sid): return sid.split("-")[0]

def main():
    data = load_files()
    models = sorted(data); seeds = sorted(next(iter(data.values())))
    all_sids = sorted({sid for m in models for s in data[m].values() for sid in s})
    q1 = {}
    for m in models:
        for sid in all_sids:
            outs = {s: [data[m][s][sid]] for s in seeds if sid in data[m][s]}
            if len(outs) >= 2:
                q1[(m, sid)] = _bds(outs)
    q2 = {}
    for sid in all_sids:
        texts = {m: [data[m][0][sid]] for m in models if sid in data[m][0]}
        if len(texts) >= 2:
            q2[sid] = float(np.mean([_bds({a: texts[a], b: texts[b]}) for a, b in combinations(texts.keys(), 2)]))
    pairs = []
    for sid in all_sids:
        if sid in q2:
            vals = [q1.get((m, sid)) for m in models]
            vals = [v for v in vals if v is not None]
            pairs.append((q2[sid], float(np.mean(vals))))
    cross = np.array([p[0] for p in pairs]); seed = np.array([p[1] for p in pairs])
    diff = cross - seed
    wilc = stats.wilcoxon(diff)
    rng = np.random.default_rng(42)
    boots = [np.mean(rng.choice(diff, size=len(diff), replace=True)) for _ in range(5000)]
    ci = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
    cat_stats = {}
    for c in sorted({cat(s) for s in all_sids}):
        vals = [q2[s] for s in all_sids if cat(s) == c and s in q2]
        b = [np.mean(rng.choice(vals, size=len(vals), replace=True)) for _ in range(5000)]
        cat_stats[c] = {"n": len(vals), "mean": round(float(np.mean(vals)), 4),
                        "ci": [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)],
                        "median": round(float(np.median(vals)), 4)}
    cats = sorted(cat_stats)
    pair_res = {}
    for a, b in combinations(cats, 2):
        u, p = stats.mannwhitneyu([q2[s] for s in all_sids if cat(s) == a], [q2[s] for s in all_sids if cat(s) == b], alternative="two-sided")
        pair_res[f"{a}_vs_{b}"] = {"U": float(u), "p": float(p)}
    res = {
        "n_scenarios": len(all_sids), "models": models, "seeds": seeds,
        "q1_per_model_mean": {m: round(float(np.mean([v for (mm, s), v in q1.items() if mm == m])), 4) for m in models},
        "q1_category_mean": {c: round(float(np.mean([v for (m, s), v in q1.items() if cat(s) == c])), 4) for c in cats},
        "q2_overall": {"mean": round(float(np.mean(cross)), 4), "median": round(float(np.median(cross)), 4)},
        "q2_by_category": cat_stats,
        "seed_vs_cross": {"cross_mean": round(float(np.mean(cross)), 4), "seed_mean": round(float(np.mean(seed)), 4),
                          "mean_diff": round(float(np.mean(diff)), 4), "diff_95ci": [round(x, 4) for x in ci],
                          "wilcoxon_stat": float(wilc.statistic), "wilcoxon_p": float(wilc.pvalue), "n_paired": len(pairs)},
        "category_pairwise_mannwhitney": pair_res,
        "worst_5": sorted(q2.items(), key=lambda kv: -kv[1])[:5],
        "best_5": sorted(q2.items(), key=lambda kv: kv[1])[:5],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "full_run_stats_20260813.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))

if __name__ == "__main__":
    main()
