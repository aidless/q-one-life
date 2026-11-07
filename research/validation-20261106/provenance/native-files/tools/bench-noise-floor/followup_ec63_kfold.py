#!/usr/bin/env python3
"""E-C #63: k-fold version of the leave-one-out floor (Tier 2 item 63).

Question under test
-------------------
Reviewer's question: replace the leave-one-out (LOO) generator pool with
k-fold and compare the resulting verdicts and intervals — is k-fold more
stable / looser, and does any verdict flip?

Reading of the request (documented, not silent)
-----------------------------------------------
eq:loo's floor is defined over the GENERATOR pool: for each generator g the
gold is rebuilt without g's own vote (c^-_g) and g is scored against it. The
k-fold generalisation therefore folds the generator pool: with k=4 the 25
generators are partitioned into 4 folds; for each fold F the gold c^-_F is
rebuilt from the votes of the OTHER folds, and every g in F is scored against
c^-_F. Folds are assigned round-robin over the sorted judge names
(deterministic; fold sizes 7/6/6/6 on m=25). The case-cluster bootstrap
convention is unchanged (seed 20261001, B=2000, percentile CI) — "case 整簇"
is preserved on the resampling axis, which is the axis the intervals live on.

What is compared, per m25 corpus
--------------------------------
* baseline: the carrier-anchored LOO chain (fc.validate_m25_arm must
  reproduce evidence/m25_<t>.json first);
* k-fold arm: full chain (main gold -> leaderboard; c^-_F -> per-generator
  hits; floor = max over generators; verdict chain) on the k-fold common
  domain, with its own margin CI;
* paired LOO-on-same-domain arm: the LOO floor restricted to the SAME k-fold
  common domain, sharing the SAME bootstrap draw sequence — so the paired
  difference (kfold margin - LOO margin) has a round-level CI;
* verdict flip table: carrier LOO verdict vs k-fold verdict.

Scope
-----
* m25 four corpora only: the m=2 jev corpora have no 4-fold generator pool
  (k=4 > m=2 is undefined for leave-a-fold-out), the human-gold arm has no
  generator pool at all (its floor is the actor median, not LOO), and the
  public 17-judge panel substrate is not redistributable (no license) —
  reported as N/A, not forced.
* k = n_generators reduces each fold to a single judge, i.e. k-fold collapses
  to LOO; the selftest uses exactly that identity as a known-answer fixture.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit  # noqa: E402
import followup_common as fc  # noqa: E402

OUT_JSON = os.path.join(fc.OUTDIR, "EC63_kfold_vs_loo.json")
OUT_MD = os.path.join(fc.OUTDIR, "EC63_kfold_vs_loo.md")

K_FOLD = 4


# ---------------------------------------------------------------- folds

def assign_folds(judges: list, k: int) -> dict:
    """Round-robin fold assignment over the sorted judge names.
    Returns {judge: fold_id}; every judge in exactly one fold; all k folds
    non-empty (else the fold gold would equal the full gold)."""
    js = sorted(judges)
    if k < 2:
        raise ValueError(f"k={k} < 2 is not a fold split")
    if k > len(js):
        raise ValueError(f"k={k} > n_generators={len(js)}: an empty fold would make "
                         "c^-_F the full gold — refuse")
    return {j: i % k for i, j in enumerate(js)}


def fold_gold(jdf: pd.DataFrame, fold_of: dict, fold: int) -> dict:
    """c^-_F: majority gold (unmeasured) from the votes of all judges NOT in
    `fold`. Cross-checked against audit.build_gold (production) in selftest."""
    sub = jdf[jdf["actor"].map(lambda a: fold_of.get(audit.norm_actor(a), -1) != fold)]
    gold, _ = fc.build_gold_variant(sub, "unmeasured")
    return gold


# ---------------------------------------------------------------- k-fold arm

def run_judge_gold_arm_kfold(votes_csv: str, k: int = K_FOLD, n_boot: int = 2000):
    """Full judge-gold chain with a k-fold floor, mirroring
    fc.run_judge_gold_arm line-for-line except that each generator is scored
    against its FOLD's c^- instead of its own LOO c^-."""
    df, have_prob = audit.load(votes_csv)
    jdf = df[df["role"] == "judge"].copy()
    gold_map, gold_counts = fc.build_gold_variant(jdf, "unmeasured")
    judges = sorted({audit.norm_actor(a) for a in jdf["actor"].tolist()})
    fold_of = assign_folds(judges, k)
    fold_maps = {f: fold_gold(jdf, fold_of, f) for f in range(k)}

    # common domain: items where every generator's own fold-c^- is defined AND
    # the main gold is defined — the both-sides-measurable set, same alignment
    # convention as run_one (floor and leaderboard restricted to one common
    # domain U). A fold-c^- can be defined where the all-votes gold is a tie
    # (fewer voters -> easier majority); without the gold intersection such
    # items would spuriously trip the domain-membership gate (measured:
    # 3 relevance items). The count is reported, not hidden.
    per_gen_domain = {j: set(fold_maps[fold_of[j]]) for j in judges}
    common = set.intersection(*[per_gen_domain[j] for j in judges]) if judges else set()
    n_fold_defined_main_gold_undefined = len(common - set(gold_map))
    common = common & set(gold_map)

    # floor side: per-generator hits on the common domain against its fold c^-
    floor_mats = {}
    fold_u_raw = {}
    for j in judges:
        sub = jdf[jdf["actor"].map(lambda a: audit.norm_actor(a) == j)]
        sub_u = sub[sub["item_id"].isin(common)]
        hitu = audit.agreement(sub_u, fold_maps[fold_of[j]])
        mau, _ = audit.macro_micro(hitu, sub_u["slice"])
        fold_u_raw[j] = float(mau)
        floor_mats[j] = (sub_u["slice"].to_numpy(), sub_u["case_id"].to_numpy(),
                         np.asarray(hitu, dtype=float))

    # leaderboard on the common domain against the main gold (production caliber)
    lb_df = df[df["item_id"].isin(common)] if common else df
    lb_sdf = lb_df[lb_df["role"] == "system"]
    rows, _ = audit._leaderboard(lb_df, lb_sdf, gold_map)
    top = rows[0]
    ceiling = max(fold_u_raw.values()) if fold_u_raw else float("nan")
    same_domain = audit.domain_membership_ok(rows, set(common)) if common else False
    verdict = fc.verdict_judge_chain(float(top["macro"]), ceiling, same_domain, len(judges))

    # paired bootstrap: shared draw sequence across leader and all floor arms
    cases = np.unique(np.concatenate([r["case"] for r in rows]))
    case_index = {c: i for i, c in enumerate(cases)}
    slice_levels = list(np.unique(np.concatenate([r["slice"] for r in rows])))
    boot_idx = fc.make_boot_idx(len(cases), n_boot)
    S_top, N_top = fc.cells_matrices(top["slice"], top["case"], top["hit"],
                                     slice_levels, case_index)
    b_top = fc.boot_macro_rounds(S_top, N_top, boot_idx)
    stack = []
    for j in sorted(floor_mats):
        sl, cs, ht = floor_mats[j]
        S, N = fc.cells_matrices(sl, cs, ht, slice_levels, case_index)
        stack.append(fc.boot_macro_rounds(S, N, boot_idx))
    stack = np.vstack(stack)
    with np.errstate(invalid="ignore"):
        floor_b = np.nanmax(stack, axis=0)
    margin_b = (b_top - floor_b) * 100.0
    lo, hi = fc.percentile_ci(margin_b)
    return {
        "k": k, "fold_sizes": [int(sum(1 for v in fold_of.values() if v == f))
                               for f in range(k)],
        "fold_of": {j: int(f) for j, f in fold_of.items()},
        "n_items": int(df["item_id"].nunique()),
        "n_generators": len(judges),
        "kfold_domain_size": len(common),
        "n_fold_defined_main_gold_undefined": int(n_fold_defined_main_gold_undefined),
        "per_fold_gold_items": {f: len(fold_maps[f]) for f in sorted(fold_maps)},
        "leaderboard_scored_items": int(top["n"]),
        "same_domain_as_floor": bool(same_domain),
        "leader": top["system"],
        "leader_macro_raw": float(top["macro"]),
        "floor_max_raw": float(ceiling),
        "pool_kfold_macro_u": {j: round(v, 6) for j, v in sorted(fold_u_raw.items())},
        "margin_vs_floor_points": float(top["macro"]) - float(ceiling),
        "ci_floor": {"lo95": lo, "hi95": hi, "n_boot": n_boot, "seed": fc.SEED,
                     "n_dropped_rounds": int(np.sum(~np.isfinite(margin_b)))},
        "verdict": verdict,
        "_rows": rows, "_cases": cases, "_boot_idx": boot_idx,
        "_floor_mats": floor_mats, "_b_top": b_top, "_floor_b": floor_b,
    }


def loo_margin_on_domain(votes_csv: str, domain: set, boot_idx: np.ndarray,
                         slice_levels: list) -> dict:
    """LOO floor chain restricted to an externally given domain, sharing the
    given bootstrap draws — the paired counterpart of the k-fold arm."""
    df, _ = audit.load(votes_csv)
    jdf = df[df["role"] == "judge"].copy()
    gold_map, _ = fc.build_gold_variant(jdf, "unmeasured")
    loo_maps = fc.leave_one_out_variant(jdf, "unmeasured")
    judges = sorted({audit.norm_actor(a) for a in jdf["actor"].tolist()})
    floor_mats = {}
    loo_u_raw = {}
    for j in judges:
        sub = jdf[jdf["actor"].map(lambda a: audit.norm_actor(a) == j)]
        sub_u = sub[sub["item_id"].isin(domain)]
        hitu = audit.agreement(sub_u, loo_maps[j])
        mau, _ = audit.macro_micro(hitu, sub_u["slice"])
        loo_u_raw[j] = float(mau)
        floor_mats[j] = (sub_u["slice"].to_numpy(), sub_u["case_id"].to_numpy(),
                         np.asarray(hitu, dtype=float))
    lb_df = df[df["item_id"].isin(domain)]
    lb_sdf = lb_df[lb_df["role"] == "system"]
    rows, _ = audit._leaderboard(lb_df, lb_sdf, gold_map)
    top = rows[0]
    cases = np.unique(np.concatenate([r["case"] for r in rows]))
    case_index = {c: i for i, c in enumerate(cases)}
    S_top, N_top = fc.cells_matrices(top["slice"], top["case"], top["hit"],
                                     slice_levels, case_index)
    b_top = fc.boot_macro_rounds(S_top, N_top, boot_idx)
    stack = []
    for j in sorted(floor_mats):
        sl, cs, ht = floor_mats[j]
        S, N = fc.cells_matrices(sl, cs, ht, slice_levels, case_index)
        stack.append(fc.boot_macro_rounds(S, N, boot_idx))
    stack = np.vstack(stack)
    with np.errstate(invalid="ignore"):
        floor_b = np.nanmax(stack, axis=0)
    margin_b = (b_top - floor_b) * 100.0
    lo, hi = fc.percentile_ci(margin_b)
    ceiling = max(loo_u_raw.values())
    return {
        "floor_max_raw": float(ceiling),
        "pool_loo_macro_u_restricted": {j: round(v, 6) for j, v in sorted(loo_u_raw.items())},
        "margin_vs_floor_points": float(top["macro"]) - float(ceiling),
        "ci_floor": {"lo95": lo, "hi95": hi, "n_boot": int(boot_idx.shape[0]),
                     "seed": fc.SEED,
                     "n_dropped_rounds": int(np.sum(~np.isfinite(margin_b)))},
        "leader": top["system"], "leader_macro_raw": float(top["macro"]),
        "_b_top": b_top, "_floor_b": floor_b, "_rows": rows,
    }


def paired_difference(kf: dict, lo_restricted: dict) -> dict:
    """Round-level paired difference of margins (kfold - LOO, same domain,
    same draws) with its percentile CI."""
    # recompute both margin rounds from the stored matrices
    kf_m = (kf["_b_top"] - kf["_floor_b"]) * 100.0
    lo_m = (lo_restricted["_b_top"] - lo_restricted["_floor_b"]) * 100.0
    d = kf_m - lo_m
    lo, hi = fc.percentile_ci(d)
    return {"mean_points": float(np.nanmean(d)),
            "ci_lo95": lo, "ci_hi95": hi, "n_boot": int(len(d)),
            "n_dropped_rounds": int(np.sum(~np.isfinite(d))),
            "positive_share": float(np.nanmean((d > 0).astype(float)))}


# ---------------------------------------------------------------- per task

def task_arm(task: str) -> dict:
    td = tempfile.mkdtemp(prefix=f"ec63_{task}_")
    import make_m25_votes
    rec = make_m25_votes.build(task, td, fc.EXAMPLES)
    votes_csv = rec["path"]

    base = fc.run_judge_gold_arm(votes_csv)
    base["task"] = task                 # run_judge_gold_arm names the arm by the
    fc.validate_m25_arm(base)           # CSV basename; validate_m25_arm keys on task

    kf = run_judge_gold_arm_kfold(votes_csv, k=K_FOLD)

    slice_levels = list(np.unique(np.concatenate([r["slice"] for r in kf["_rows"]])))
    lo_r = loo_margin_on_domain(votes_csv, _domain_set(kf, votes_csv),
                                kf["_boot_idx"], slice_levels)
    diff = paired_difference(kf, lo_r)
    return {
        "task": task,
        "loo_baseline": arm_a(base, carrier=True),
        "kfold": {k2: v for k2, v in kf.items() if not k2.startswith("_")},
        "loo_on_kfold_domain": {k2: v for k2, v in lo_r.items()
                                if not k2.startswith("_")},
        "paired_margin_difference_kfold_minus_loo": diff,
        "domain_shrink": base["loo_domain_size"] - kf["kfold_domain_size"],
        "verdict_flipped": base["verdict_max_floor"] != kf["verdict"],
        "_tmpdir": td,
    }


def _domain_set(kf: dict, votes_csv: str) -> set:
    """Recover the k-fold common domain as the item set actually scored by the
    floor arms (leaderboard rows' items ∩ per-generator domains)."""
    df, _ = audit.load(votes_csv)
    jdf = df[df["role"] == "judge"]
    judges = sorted({audit.norm_actor(a) for a in jdf["actor"].tolist()})
    fold_of = kf["fold_of"]
    fold_maps = {f: fold_gold(jdf, fold_of, f) for f in range(kf["k"])}
    gold_map, _ = fc.build_gold_variant(jdf, "unmeasured")
    dom = None
    for j in judges:
        d = set(fold_maps[fold_of[j]])
        dom = d if dom is None else (dom & d)
    return (dom or set()) & set(gold_map)


def arm_a(arm: dict, carrier: bool = False) -> dict:
    return {
        "verdict": arm["verdict_max_floor"],
        "leader": arm["leader"],
        "leader_macro_raw": round(arm["leader_macro_raw"], 4),
        "floor_max_raw": round(arm["floor_max_raw"], 4),
        "margin_vs_floor_points": round(arm["margin_vs_floor_points"], 4),
        "ci_floor": {"lo95": arm["ci_floor"]["lo95"], "hi95": arm["ci_floor"]["hi95"],
                     "n_boot": arm["ci_floor"]["n_boot"], "seed": arm["ci_floor"]["seed"]},
        "loo_domain_size": arm["loo_domain_size"],
        "carrier_anchored": carrier,
    }


# ---------------------------------------------------------------- selftest

def selftest() -> int:
    fails = []

    def ok(name, cond):
        if not cond:
            fails.append(name)

    # -- fold assignment -------------------------------------------------------
    fo = assign_folds([f"j{i}" for i in range(25)], 4)
    ok("fold sizes 7/6/6/6",
       sorted([sum(1 for v in fo.values() if v == f) for f in range(4)]) == [6, 6, 6, 7])
    ok("partition covers exactly once", len(fo) == 25 and len(set(fo.values())) == 4)
    try:
        assign_folds(["a", "b"], 4)
        ok("k>n refused", False)
    except ValueError:
        ok("k>n refused", True)
    try:
        assign_folds(["a", "b", "c"], 1)
        ok("k<2 refused", False)
    except ValueError:
        ok("k<2 refused", True)

    # -- fold_gold equals audit.build_gold on the complement (production) -----
    rows = []
    judges = ["j1", "j2", "j3", "j4", "j5"]
    items = ["i1", "i2", "i3", "i4"]
    ans = {"j1": ["x", "x", "y", "x"], "j2": ["x", "x", "y", "y"],
           "j3": ["x", "y", "y", "x"], "j4": ["x", "x", "x", "y"],
           "j5": ["y", "x", "y", "y"]}
    for j in judges:
        for it, v in zip(items, ans[j]):
            rows.append({"item_id": it, "case_id": it, "slice": "s", "role": "judge",
                         "actor": j, "answer": v})
            rows.append({"item_id": it, "case_id": it, "slice": "s", "role": "system",
                         "actor": j, "answer": v})
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "fx.csv")
        pd.DataFrame(rows).to_csv(p, index=False)
        df, _ = audit.load(p)
        jdf = df[df["role"] == "judge"].copy()
        fo2 = assign_folds(judges, 2)
        for f in range(2):
            mine = fold_gold(jdf, fo2, f)
            sub = jdf[jdf["actor"].map(lambda a: fo2.get(audit.norm_actor(a), -1) != f)]
            ref, _ = fc.build_gold_variant(sub, "unmeasured")
            ok(f"fold_gold == audit.build_gold(complement) fold{f}", mine == ref)
        # mutation: a fold that ACCIDENTALLY includes its own members must differ
        broken = dict(fo2)
        j_first = sorted(judges)[0]
        broken_wrong = {**broken, j_first: broken[j_first]}  # unchanged on purpose
        sub_wrong = jdf[jdf["actor"].map(lambda a: True)]    # no exclusion at all
        wrong_gold, _ = fc.build_gold_variant(sub_wrong, "unmeasured")
        ok("mutation: no-exclusion gold differs from fold gold",
           wrong_gold != fold_gold(jdf, fo2, 0))

        # -- k = n_generators collapses to LOO (known-answer identity) ----------
        fx_all = pd.concat([df], ignore_index=True)
        p_all = os.path.join(td, "fx_all.csv")
        fx_all.to_csv(p_all, index=False)
        kf = run_judge_gold_arm_kfold(p_all, k=5, n_boot=50)
        base = fc.run_judge_gold_arm(p_all, n_boot=50)
        ok("k=n reduces to LOO: floor equal",
           abs(kf["floor_max_raw"] - base["floor_max_raw"]) < 1e-12)
        ok("k=n reduces to LOO: margin equal",
           abs(kf["margin_vs_floor_points"] - base["margin_vs_floor_points"]) < 1e-12)
        ok("k=n reduces to LOO: CI equal (same seed, same domain)",
           abs(kf["ci_floor"]["lo95"] - base["ci_floor"]["lo95"]) < 1e-12
           and abs(kf["ci_floor"]["hi95"] - base["ci_floor"]["hi95"]) < 1e-12)
        # mutation: with k < n the fold c^- has fewer voters -> floor must move
        kf2 = run_judge_gold_arm_kfold(p_all, k=2, n_boot=50)
        ok("mutation: k=2 (folds of >1) is NOT the LOO number on this fixture",
           abs(kf2["floor_max_raw"] - base["floor_max_raw"]) > 1e-9)

        # -- domain alignment: an item defined in every fold-c^- but TIED in the
        #    full gold must be excluded from the chain domain (run_one's
        #    both-sides-measurable convention), and must not trip the
        #    domain-membership gate when systems answer everything.
        rows2 = []
        # 5 judges, k=2: fold0={j1,j3,j5}, fold1={j2,j4} (round-robin on sorted)
        # it1: j1=A j2=B j3=A j4=B j5="" -> full gold tie (unmeasured), but
        # fold1's c^- (from fold0: A,A) = A and fold0's c^- (from fold1: B,B) = B
        # -> fold-defined on both folds, main-gold undefined -> must be dropped.
        it1 = {"j1": "A", "j2": "B", "j3": "A", "j4": "B", "j5": ""}
        norm = {f"j{i}": ["x", "x", "y", "y", "y"][i - 1] for i in range(1, 6)}
        items2 = ["i1", "i2", "i3", "i4", "it1"]
        ans2 = {"j1": ["x", "x", "y", "x"], "j2": ["x", "x", "y", "y"],
                "j3": ["x", "y", "y", "x"], "j4": ["x", "x", "x", "y"],
                "j5": ["y", "x", "y", "y"]}
        for j in judges:
            for it, v in zip(items2, ans2[j] + [it1[j]]):
                for role in ("judge", "system"):
                    rows2.append({"item_id": it, "case_id": it, "slice": "s",
                                  "role": role, "actor": j, "answer": v})
        p2 = os.path.join(td, "fx2.csv")
        pd.DataFrame(rows2).to_csv(p2, index=False)
        kf3 = run_judge_gold_arm_kfold(p2, k=2, n_boot=30)
        ok("gold-tied but fold-defined item excluded from domain",
           "it1" not in _domain_set(kf3, p2))
        ok("domain gate not tripped when systems answer all items",
           kf3["same_domain_as_floor"] is True)
        ok("fold-defined-but-gold-tied count recorded", 
           kf3["n_fold_defined_main_gold_undefined"] == 1)

    print(f"followup_ec63_kfold selftest: {'PASS' if not fails else 'FAIL'}")
    for f in fails:
        print("  -", f)
    return 0 if not fails else 1


# ---------------------------------------------------------------- main

def run() -> dict:
    arms = [task_arm(t) for t in fc.TASKS]
    inputs = ([os.path.join(fc.EVIDENCE, f"m25_{t}.json") for t in fc.TASKS])
    out = {
        "schema": "ec63-kfold-vs-loo/1",
        "provenance": fc.provenance(inputs),
        "k": K_FOLD,
        "tasks": [{k2: v for k2, v in a.items() if k2 != "_tmpdir"} for a in arms],
        "interpretation": {
            "reading": "k-fold generalises leave-one-out over the GENERATOR pool "
                       "(eq:loo's held-out unit is a generator's vote): k=4 folds by "
                       "round-robin over sorted judges; c^-_F = majority gold from the "
                       "other folds; each g scored against its fold's c^-. The case-"
                       "cluster bootstrap convention is unchanged (seed 20261001, "
                       "B=2000, percentile CI).",
            "paired_ci": "LOO is additionally recomputed on the SAME k-fold common "
                         "domain with the SAME bootstrap draws, so the paired margin "
                         "difference has a round-level CI.",
            "scope": "m25 four corpora; m=2 corpora (k=4 > m undefined), the human-gold "
                     "arm (no generator pool; floor = actor median) and the 17-judge "
                     "panel (substrate not redistributable) are N/A.",
        },
    }
    return out


def write_outputs(out: dict) -> None:
    os.makedirs(fc.OUTDIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    lines = ["# E-C #63 — k-fold 版留一地板（k=4）", ""]
    lines += [
        "问题（Tier 2 #63）：把留一法（LOO）生成器池换成 k-fold 重跑判决链，判决与区间如何变？"
        "读法：eq:loo 的留一单位是**生成器的那一票**，所以 k-fold 折的是生成器池——k=4 按排序名次轮转分折"
        "（25 人 → 7/6/6/6），c^-_F 由其余折的票重建，g 对自己折的 c^- 打分；case 整簇 bootstrap 约定不变"
        "（seed 20261001、B=2000、percentile CI）。",
        "",
        "| 语料 | LOO（载体验证）判决/margin [CI95] | k-fold 判决/margin [CI95] | 配对差（k-fold−LOO，同域同抽样）[CI95] | 折后域收缩 | 判决翻转 |",
        "|---|---|---|---|---|---|",
    ]
    for a in out["tasks"]:
        b, kf, d = a["loo_baseline"], a["kfold"], a["paired_margin_difference_kfold_minus_loo"]
        lines.append(
            f"| {a['task']} | {b['verdict']} / {b['margin_vs_floor_points']:+.2f} "
            f"[{b['ci_floor']['lo95']:+.2f}, {b['ci_floor']['hi95']:+.2f}] | "
            f"{kf['verdict']} / {kf['margin_vs_floor_points']:+.2f} "
            f"[{kf['ci_floor']['lo95']:+.2f}, {kf['ci_floor']['hi95']:+.2f}] | "
            f"{d['mean_points']:+.2f} [{d['ci_lo95']:+.2f}, {d['ci_hi95']:+.2f}] | "
            f"{a['domain_shrink']} 题 | {'**是**' if a['verdict_flipped'] else '否'} |")
    lines += [
        "",
        "读法：配对差 > 0 = k-fold 地板更低（margin 更松）；区间含 0 = 两读数统计上不可分。",
        "",
        "## 诚实边界",
        "",
        "- 适用域：m25 四语料。m=2 语料（question/decision）没有 4 折生成器池（k=4 > m=2）；人类金标臂没有生成器池（地板=actor 中位数，非 LOO）；17-judge 公开 panel 底物不可再分发——均 N/A，不硬凑。",
        "- k-fold 折的 c^- 支撑更少（每折少 6-7 票）→ 金标定义的题更少（域收缩已在表中单列）；LOO 与 k-fold 的区间各在自己的公共域上算，配对差在**同一** k-fold 域 + **同一**抽样序列上算。",
        "- 基线经 `fc.validate_m25_arm` 对 `evidence/m25_<t>.json` 逐字段复现后才写任何比较数。",
        "- 自检含恒等式夹具：k=n_generators 时 k-fold 必须逐位退化为 LOO（floor/margin/CI 全等），k<n 时必须不等（变异检查）。",
        "",
        "## 复算命令",
        "",
        "```bash",
        "python3 tools/bench-noise-floor/followup_ec63_kfold.py --selftest",
        "python3 tools/bench-noise-floor/followup_ec63_kfold.py",
        "```",
        "",
        "载体：`evidence/strict_review_followup/EC63_kfold_vs_loo.json`",
    ]
    with open(OUT_MD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    out = run()
    write_outputs(out)
    print(f"[ok] wrote {OUT_JSON}")
    print(f"[ok] wrote {OUT_MD}")
