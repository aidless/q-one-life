#!/usr/bin/env python3
"""A2 runner: split the margin bootstrap into two estimands and test replicate-invariance.

Independent review finding A2 states that the manuscript's zero-margin identity
(Proposition 4) and the non-degenerate bootstrap interval printed by the native
tool are not the same statistic.  This runner separates them on the *real* m25
carriers and on two preregistered controls:

  theta_fixed(b) = macro of the point-estimate winner (fixed) - macro of the
                    per-round best generator      [what the native tool prints]
  theta_both(b)  = macro of the per-round best leaderboard system - macro of the
                    per-round best generator      [the Proposition 4 identity]

Under Proposition 4's hypotheses (plurality labels, ranked field == generating
pool, each generator's ballot == its own answer, both sides on the shared
leave-one-out domain U) the identity is *replicate-invariant*: every admissible
bootstrap round gives theta_both(b) == 0 exactly, so the identity's percentile
interval is the degenerate [0, 0].  The native interval is not an interval for
that estimand; it belongs to theta_fixed, whose negative lower bound is
produced by the asymmetric selection (winner frozen, floor re-selected).

The runner is deliberately fail-closed: it verifies pinned hashes, checks the
native statistic against recorded evidence, and runs controls in which the
hypotheses fail so that the degeneracy check is known to be able to fail.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

TASKS = ("factuality", "coherence", "relevance", "preference")
TOL = 1e-3  # points; the native evidence rounds its interval to 4 decimals


# --------------------------------------------------------------------------- io
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_audit(path: str):
    spec = importlib.util.spec_from_file_location("qone_native_audit", path)
    if spec is None or spec.loader is None:
        raise SystemExit(f"[FATAL] 无法加载 native audit.py: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_json(path: str, payload: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


# ------------------------------------------------------- native-algorithm ports
def cells_from_triple(trip: Dict[str, np.ndarray], slice_index, case_index,
                      n_slice: int, n_case: int) -> Tuple[np.ndarray, np.ndarray]:
    """Port of audit.py [4b] cells_from_triple (same cells, same grouping)."""
    tmp = pd.DataFrame({"s": np.asarray(trip["slice"]),
                        "c": np.asarray(trip["case"]),
                        "h": np.asarray(trip["hit"], dtype=float)})
    g = tmp.groupby(["s", "c"], sort=True)["h"].agg(["sum", "count"])
    S = np.zeros((n_slice, n_case))
    N = np.zeros_like(S)
    for (sname, cname), row in g.iterrows():
        if sname in slice_index and cname in case_index:
            S[slice_index[sname], case_index[cname]] = float(row["sum"])
            N[slice_index[sname], case_index[cname]] = float(row["count"])
    return S, N


def boot_macro(S: np.ndarray, N: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Port of audit.py boot_macro (case-cluster resampling, NaN rounds kept NaN)."""
    num = S @ W.T
    den = N @ W.T
    sl_mean = np.divide(num, den, out=np.full_like(num, np.nan), where=den > 0)
    with np.errstate(invalid="ignore"):
        valid = np.isfinite(sl_mean).any(axis=0)
        out = np.full(W.shape[0], np.nan, dtype=float)
        if valid.any():
            out[valid] = np.nanmean(sl_mean[:, valid], axis=0)
    return out


def interval(values: np.ndarray) -> Dict[str, Any]:
    ok = np.isfinite(values)
    v = values[ok]
    if v.size == 0:
        return {"n_valid_rounds": 0, "n_dropped_rounds": int(values.size)}
    lo, hi = np.percentile(v, [2.5, 97.5])
    return {
        "lo95": float(lo),
        "hi95": float(hi),
        "n_valid_rounds": int(v.size),
        "n_dropped_rounds": int(values.size - v.size),
        "crosses_zero": bool(lo <= 0 <= hi),
        "n_positive_rounds": int(np.sum(v > 0)),
        "n_zero_rounds": int(np.sum(v == 0)),
        "n_negative_rounds": int(np.sum(v < 0)),
        "max": float(np.max(v)),
        "min": float(np.min(v)),
    }


# ------------------------------------------------------------------ analysis
def analyse(audit, df: pd.DataFrame, have_prob: bool,
            n_boot: int, seed: int) -> Dict[str, Any]:
    """Recompute both estimands on one corpus with the native algorithm."""
    jdf = df[df["role"] == "judge"].copy()
    gold = audit.build_gold(jdf, have_prob, "unmeasured")
    gold_map = gold.majority
    votes = {(r.item_id, r.actor): r.answer_n for r in jdf.itertuples()}
    probs = {(r.item_id, r.actor): float("nan") for r in jdf.itertuples()}
    loo_maps = audit.leave_one_out(gold, "majority", votes, probs)
    loo_domain = set.intersection(*[set(m) for m in loo_maps.values()])

    floor_rows: List[Dict[str, Any]] = []
    floor_u_rows: Dict[str, Dict[str, np.ndarray]] = {}
    for j in gold.judges:
        sub = jdf[jdf["actor"] == j]
        hit = audit.agreement(sub, gold_map)
        ma, _mi = audit.macro_micro(hit, sub["slice"])
        hitl = audit.agreement(sub, loo_maps[j])
        mal, _ = audit.macro_micro(hitl, sub["slice"])
        sub_u = sub[sub["item_id"].isin(loo_domain)]
        hitu = audit.agreement(sub_u, loo_maps[j])
        mau, _ = audit.macro_micro(hitu, sub_u["slice"])
        floor_rows.append({"judge": j, "macro": float(ma),
                           "loo_macro": float(mal), "loo_macro_u": float(mau)})
        floor_u_rows[j] = {"hit": np.asarray(hitu, dtype=float),
                           "slice": sub_u["slice"].to_numpy(),
                           "case": sub_u["case_id"].to_numpy()}
    ceiling = max(r["loo_macro_u"] for r in floor_rows)

    lb_df = df[df["item_id"].isin(loo_domain)]
    lb_sdf = lb_df[lb_df["role"] == "system"]
    rows, _ = audit._leaderboard(lb_df, lb_sdf, gold_map)
    top = rows[0]

    cases = np.unique(np.concatenate([r["case"] for r in rows]))
    case_index = {c: i for i, c in enumerate(cases)}
    slice_levels = list(np.unique(np.concatenate([r["slice"] for r in rows])))
    slice_index = {s: i for i, s in enumerate(slice_levels)}
    rng = np.random.default_rng(seed)
    boot_idx = rng.integers(0, len(cases), size=(n_boot, len(cases)))
    W = np.zeros((n_boot, len(cases)), dtype=float)
    np.add.at(W, (np.repeat(np.arange(n_boot), len(cases)), boot_idx.ravel()), 1.0)

    lb_boot: Dict[str, np.ndarray] = {}
    for r in rows:
        S, N = cells_from_triple(r, slice_index, case_index, len(slice_levels), len(cases))
        lb_boot[r["system"]] = boot_macro(S, N, W)
    floor_boot: Dict[str, np.ndarray] = {}
    for j, trip in floor_u_rows.items():
        S, N = cells_from_triple(trip, slice_index, case_index, len(slice_levels), len(cases))
        floor_boot[j] = boot_macro(S, N, W)

    lb_stack = np.vstack([lb_boot[r["system"]] for r in rows])
    fl_stack = np.vstack([floor_boot[j] for j in sorted(floor_boot)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        with np.errstate(invalid="ignore"):
            b_max_sys = np.nanmax(lb_stack, axis=0)
            b_max_floor = np.nanmax(fl_stack, axis=0)

    b_top = lb_boot[top["system"]]
    theta_fixed = (b_top - b_max_floor) * 100.0
    theta_both = (b_max_sys - b_max_floor) * 100.0

    max_sys_point = max(r["macro"] for r in rows)
    return {
        "n_generators": len(gold.judges),
        "n_systems": len(rows),
        "loo_domain_size": len(loo_domain),
        "leaderboard_domain_size": int(lb_sdf["item_id"].nunique()),
        "point_leader": top["system"],
        "point_leader_macro": float(top["macro"]),
        "floor_loo_macro_u": float(ceiling),
        "point_leader_max_macro": float(max_sys_point),
        "theta_fixed_point": float(top["macro"] - ceiling),
        "theta_both_point": float(max_sys_point - ceiling),
        "theta_fixed_interval": interval(theta_fixed),
        "theta_both_interval": interval(theta_both),
        "floor_per_generator": [
            {"judge": r["judge"], "macro": r["macro"],
             "loo_macro": r["loo_macro"], "loo_macro_u": r["loo_macro_u"]}
            for r in sorted(floor_rows, key=lambda x: x["judge"])
        ],
    }


# ------------------------------------------------------------------ controls
def control_nonproducer_leader(df: pd.DataFrame, audit, actor_name: str) -> pd.DataFrame:
    """Break Proposition 4 hypothesis (ii): add a leaderboard system that is not a generator.

    The added system answers every item with the plurality gold label, so it is
    not among the gold generators and has no leave-one-out floor of its own.
    """
    jdf = df[df["role"] == "judge"].copy()
    gold = audit.build_gold(jdf, False, "unmeasured")
    gold_map = gold.majority
    sysdf = df[df["role"] == "system"]
    out_rows = []
    for item, grp in sysdf.groupby("item_id", sort=True):
        r = grp.iloc[0].copy()
        r["actor"] = actor_name
        label = gold_map.get(item)
        if label:
            r["answer"] = label
        out_rows.append(r)
    ctrl = pd.DataFrame(out_rows)
    ctrl = ctrl[df.columns]
    return pd.concat([df, ctrl], ignore_index=True)


def control_unranked_generator(df: pd.DataFrame, actor: str) -> pd.DataFrame:
    """Break Proposition 4 hypothesis (ii) the other way: a generator is not ranked."""
    keep = ~((df["role"] == "system") & (df["actor"] == actor))
    return df[keep].copy()


# ------------------------------------------------------------------- runner
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="A2 bootstrap estimand split")
    ap.add_argument("--preregistration", required=True)
    ap.add_argument("--external-root", required=True,
                    help="native repository root (read-only)")
    ap.add_argument("--votes-dir", required=True,
                    help="directory holding the derived m25 vote tables")
    ap.add_argument("--output", required=True)
    ap.add_argument("--native-rerun", dest="native_rerun", action="store_true", default=True)
    ap.add_argument("--no-native-rerun", dest="native_rerun", action="store_false")
    args = ap.parse_args(argv)

    prereg_path = os.path.abspath(args.preregistration)
    prereg = json.load(open(prereg_path, encoding="utf-8"))
    root = args.external_root
    tools_dir = os.path.join(root, "tools", "bench-noise-floor")
    audit_path = os.path.join(tools_dir, "audit.py")
    ev_dir = os.path.join(root, "papers", "bench_noise_floor", "evidence")

    # ---- pinned hash gate -------------------------------------------------
    hash_checks: List[Dict[str, Any]] = []

    def check(label: str, path: str, expected: str) -> None:
        actual = sha256_file(path)
        hash_checks.append({"label": label, "path": path, "expected": expected,
                            "actual": actual, "match": actual == expected})

    check("runner", os.path.abspath(__file__), prereg["implementation"]["sha256"])
    check("native_audit", audit_path, prereg["native_tool"]["sha256"])
    for label, rel, expected in prereg["native_inputs"]:
        check(label, os.path.join(root, rel), expected)
    for label, rel, expected in prereg["recorded_evidence"]:
        check(label, os.path.join(root, rel), expected)

    votes_dir = os.path.abspath(args.votes_dir)
    os.makedirs(votes_dir, exist_ok=True)
    for label, name, expected in prereg["derived_vote_tables"]:
        check(label, os.path.join(votes_dir, name), expected)

    if not all(c["match"] for c in hash_checks):
        failed = [c for c in hash_checks if not c["match"]]
        write_json(args.output, {"status": "hash_gate_failed", "hash_checks": hash_checks})
        print("[FATAL] 钉住的摘要与盘上不符：")
        for c in failed:
            print(f"  {c['label']}: expected {c['expected']} actual {c['actual']} ({c['path']})")
        return 3

    # rebuild the derived tables if they are not there yet
    missing = [name for _, name, _ in prereg["derived_vote_tables"]
               if not os.path.exists(os.path.join(votes_dir, name))]
    if missing:
        cmd = [sys.executable, os.path.join(tools_dir, "make_m25_votes.py"),
               "--out-dir", votes_dir, "--task", "all"]
        subprocess.run(cmd, check=True, cwd=tools_dir)
        for label, name, expected in prereg["derived_vote_tables"]:
            check(label, os.path.join(votes_dir, name), expected)
        if not all(c["match"] for c in hash_checks):
            write_json(args.output, {"status": "derived_table_hash_failed",
                                      "hash_checks": hash_checks})
            print("[FATAL] 派生输入表摘要与钉值不符")
            return 3

    audit = load_audit(audit_path)
    n_boot = int(prereg["bootstrap"]["n_boot"])
    seed = int(prereg["bootstrap"]["seed"])

    # ---- main conditions (the four m25 carriers) --------------------------
    recorded = {}
    for task in TASKS:
        with open(os.path.join(ev_dir, f"m25_{task}.json"), encoding="utf-8") as fh:
            recorded[task] = json.load(fh)

    tasks_out: Dict[str, Any] = {}
    for task in TASKS:
        csv_path = os.path.join(votes_dir, f"judgesense_{task}_m25.csv")
        df, have_prob = audit.load(csv_path)
        res = analyse(audit, df, have_prob, n_boot, seed)
        rec = recorded[task]
        rec_ci = rec.get("margin_ci") or {}
        res["recorded_native"] = {
            "verdict": rec.get("verdict"),
            "margin_vs_floor": rec.get("margin_vs_floor"),
            "margin_ci": rec_ci,
            "ceiling_loo_macro": rec.get("ceiling_loo_macro"),
            "loo_domain_size": rec.get("loo_domain_size"),
        }
        res["fidelity_vs_recorded"] = {
            "margin_fixed_point_matches": abs(res["theta_fixed_point"] - float(rec.get("margin_vs_floor", 0.0))) <= 1e-9,
            "ceiling_matches": abs(res["floor_loo_macro_u"] - float(rec.get("ceiling_loo_macro", float("nan")))) <= TOL,
            "ci_lo_matches": abs(res["theta_fixed_interval"]["lo95"] - float(rec_ci.get("lo95", float("nan")))) <= TOL,
            "ci_hi_matches": abs(res["theta_fixed_interval"]["hi95"] - float(rec_ci.get("hi95", float("nan")))) <= TOL,
            "n_valid_rounds_matches": res["theta_fixed_interval"]["n_valid_rounds"] == int(rec_ci.get("n_valid_rounds", -1)),
        }
        tasks_out[task] = res
        print(f"[task] {task}: theta_fixed_point={res['theta_fixed_point']:+.6f} "
              f"theta_both_point={res['theta_both_point']:+.6f} "
              f"fixed_ci=[{res['theta_fixed_interval']['lo95']:+.4f},{res['theta_fixed_interval']['hi95']:+.4f}] "
              f"both_ci=[{res['theta_both_interval']['lo95']:+.4f},{res['theta_both_interval']['hi95']:+.4f}]")

    # ---- controls ----------------------------------------------------------
    ctrl_task = prereg["controls"]["task"]
    ctrl_csv = os.path.join(votes_dir, f"judgesense_{ctrl_task}_m25.csv")
    df, have_prob = audit.load(ctrl_csv)
    controls: Dict[str, Any] = {}

    c1 = control_nonproducer_leader(df, audit, prereg["controls"]["nonproducer_actor"])
    controls["nonproducer_leader"] = analyse_from_frame(audit, c1, have_prob, n_boot, seed)

    c2 = control_unranked_generator(df, prereg["controls"]["unranked_generator"])
    controls["unranked_generator"] = analyse_from_frame(audit, c2, have_prob, n_boot, seed)

    # ---- optional native rerun on the rebuilt table ------------------------
    native_rerun: Dict[str, Any] = {"ran": False}
    if args.native_rerun:
        task = prereg["native_rerun"]["task"]
        out_json = os.path.join(os.path.dirname(os.path.abspath(args.output)),
                                f"native-rerun-{task}.json")
        log_path = os.path.join(os.path.dirname(os.path.abspath(args.output)),
                                f"native-rerun-{task}.log")
        cmd = [sys.executable, "-u", audit_path,
               os.path.join(votes_dir, f"judgesense_{task}_m25.csv"),
               "--gold", "majority", "--n-boot", str(n_boot), "--json", out_json]
        with open(log_path, "w", encoding="utf-8") as lf:
            proc = subprocess.run(cmd, cwd=tools_dir, stdout=lf, stderr=subprocess.STDOUT)
        rec_ci = (recorded[task].get("margin_ci") or {})
        native_payload = {}
        if os.path.exists(out_json):
            with open(out_json, encoding="utf-8") as fh:
                native_payload = json.load(fh)
        nci = native_payload.get("margin_ci") or {}
        native_rerun = {
            "ran": True,
            "task": task,
            "returncode": proc.returncode,
            "command": cmd,
            "log": os.path.basename(log_path),
            "json": os.path.basename(out_json),
            "margin_ci": nci,
            "margin_vs_floor": native_payload.get("margin_vs_floor"),
            "ceiling_loo_macro": native_payload.get("ceiling_loo_macro"),
            "verdict": native_payload.get("verdict"),
            "matches_recorded": (
                abs(float(nci.get("lo95", float("nan"))) - float(rec_ci.get("lo95", float("nan")))) <= TOL
                and abs(float(nci.get("hi95", float("nan"))) - float(rec_ci.get("hi95", float("nan")))) <= TOL
                and abs(float(native_payload.get("margin_vs_floor", float("nan"))) - float(recorded[task].get("margin_vs_floor", 0.0))) <= 1e-9
            ),
        }

    # ---- gates -------------------------------------------------------------
    gates = evaluate_gates(prereg, tasks_out, controls, native_rerun)

    payload = {
        "schema": "q-one-bootstrap-estimand-split-v1",
        "status": "completed" if all(g["pass"] for g in gates) else "gate_failed",
        "preregistration": {"path": os.path.basename(prereg_path),
                            "sha256": sha256_file(prereg_path)},
        "hash_checks": hash_checks,
        "bootstrap": {"n_boot": n_boot, "seed": seed,
                      "unit": "points", "cluster": "case"},
        "estimands": {
            "theta_fixed": "macro of the point-estimate winner (fixed across rounds) minus macro of the per-round best generator; this is what the native tool prints as margin_ci",
            "theta_both": "macro of the per-round best leaderboard system minus macro of the per-round best generator; this is the Proposition 4 identity statistic",
        },
        "tasks": tasks_out,
        "controls": controls,
        "native_rerun": native_rerun,
        "gates": gates,
    }
    write_json(args.output, payload)
    for g in gates:
        print(f"[gate] {g['id']}: {'PASS' if g['pass'] else 'FAIL'} - {g['detail']}")
    print(f"[out] {args.output}")
    return 0 if all(g["pass"] for g in gates) else 4


def analyse_from_frame(audit, df: pd.DataFrame, have_prob: bool,
                        n_boot: int, seed: int) -> Dict[str, Any]:
    return analyse(audit, df, have_prob, n_boot, seed)


def evaluate_gates(prereg, tasks_out, controls, native_rerun) -> List[Dict[str, Any]]:
    gates: List[Dict[str, Any]] = []

    fid_ok = all(all(v for k, v in t["fidelity_vs_recorded"].items())
                 for t in tasks_out.values())
    gates.append({"id": "F1_fidelity_vs_recorded_native",
                  "pass": fid_ok,
                  "detail": "recomputed fixed-winner statistic equals the recorded native "
                            "margin point estimate, ceiling, and 95% interval for all four m25 tasks"})

    both_zero = all(
        t["theta_both_interval"].get("n_zero_rounds") == t["theta_both_interval"].get("n_valid_rounds")
        and t["theta_both_interval"].get("n_valid_rounds", 0) > 0
        and t["theta_both_interval"].get("lo95") == 0.0
        and t["theta_both_interval"].get("hi95") == 0.0
        and abs(t["theta_both_point"]) <= 1e-12
        for t in tasks_out.values())
    gates.append({"id": "F2_identity_replicate_invariance",
                  "pass": both_zero,
                  "detail": "theta_both is exactly zero in every valid bootstrap round and its "
                            "percentile interval is the degenerate [0, 0] on all four m25 tasks"})

    fixed_nonpos = all(
        t["theta_fixed_interval"].get("n_positive_rounds") == 0
        and t["theta_fixed_interval"].get("n_valid_rounds", 0) > 0
        for t in tasks_out.values())
    gates.append({"id": "F3_fixed_winner_never_positive",
                  "pass": fixed_nonpos,
                  "detail": "theta_fixed is never positive in any valid round: the frozen winner "
                            "cannot exceed the per-round best generator"})

    teeth = []
    for name, sign in (("nonproducer_leader", 1), ("unranked_generator", -1)):
        c = controls.get(name)
        if not c:
            teeth.append(False)
            continue
        ci = c["theta_both_interval"]
        ok = (ci.get("n_valid_rounds", 0) > 0 and ci["lo95"] != ci["hi95"]
              and (sign > 0 and ci["lo95"] > 0 or sign < 0 and ci["hi95"] < 0)
              and (sign > 0 and c["theta_both_point"] > 0 or sign < 0 and c["theta_both_point"] < 0))
        teeth.append(bool(ok))
    gates.append({"id": "F4_controls_have_teeth",
                  "pass": all(teeth) and len(teeth) == 2,
                  "detail": "both preregistered controls (a leader that is not a generator; a "
                            "generator that is not ranked) produce a non-degenerate, strictly "
                            "signed theta_both interval, so the degeneracy check can fail"})

    native_ok = (not native_rerun.get("ran")) or bool(native_rerun.get("matches_recorded"))
    gates.append({"id": "F5_native_rerun_matches_recorded",
                  "pass": native_ok,
                  "detail": "an unmodified rerun of the native tool on the rebuilt table "
                            "reproduces the recorded margin interval"})

    return gates


if __name__ == "__main__":
    raise SystemExit(main())
