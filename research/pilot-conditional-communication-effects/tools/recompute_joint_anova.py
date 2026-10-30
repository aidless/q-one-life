"""Re-derive the joint-experiment ANOVA from the carrier's own sessions.

Purpose
-------
`joint_full_F_v10_results.json` stores a summary ANOVA block (`SS_within` 2.8975,
`F_alpha` 8.16, `F_T` 7.845, `F_interaction` 15.37).  Several manuscripts print
those numbers.  This script asks two questions and answers each separately:

  Q1  Is the stored block internally consistent (SS == MS*df, F == MS/MS_within)?
  Q2  Can it be reproduced from the raw sessions stored in the same file?

Q1 and Q2 have different meanings and must not be collapsed into one verdict.
A block can be perfectly self-consistent (Q1 yes) and still have no derivation
inside the delivered evidence (Q2 no) -- the second is the more serious defect,
because the number then has no traceable source at all.

Q2 is answered with an exact rational-arithmetic reachability test, not a
numerical fit.  Each cell's `final_ECE` takes only a few distinct values, so the
sum of squares a 15-per-cell subset can contribute is a *finite* set of exact
rationals.  Enumerating that set turns "we could not reproduce it" into
"no such subset exists", which no amount of extra floating-point precision could
ever establish.

Method notes (each of these was a real bug during development)
---------------------------------------------------------------
* The ANOVA block lives at `summary.anova_ECE`, not at the top level.  Reading
  the top level reports "absent" and silently passes everything.
* The manuscript documents the subset as "the first 15 completed sessions in
  ascending archive order (cell index, then seed)".  Sorting by `seed` alone, or
  by `task_id`, gives a different subset and a different F -- in this carrier
  F_alpha ranges from 0.012 to 6.61 across orderings, all of them "plausible"
  looking and all mutually inconsistent.
* SS decomposition must close: SS_A + SS_T + SS_AB + SS_w == total SS, residual
  ~1e-16.  A routine that fails this is wrong whatever F it prints.
* The cell formulas below are the *balanced* two-way forms.  The real carrier is
  unbalanced (25/25/20/15/15/15), so they are applied only to the documented
  balanced subset, and the actual cell sizes are reported alongside.
* `SS_w` is always computed from the subset's own cell means, never copied from
  the stored block.
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

from scipy import stats

TOL_REL = 0.005  # 0.5% relative tolerance, matching the printed precision
T_LEVELS = (10, 20)


def _decimals(x) -> int:
    """Number of significant decimals a stored p-value was printed with.

    `0.0006` -> 4, `0.0` -> 0 (underflow print, so its true value may be anything
    below the printing threshold).  Used to set the absolute tolerance that
    `internal_consistency` compares p-values on.
    """
    if x is None or x == 0:
        return 0
    s = repr(float(x))
    if "e" in s or "E" in s:
        return 6  # already in exponential form: assume ample precision
    if "." not in s:
        return 0
    return len(s.split(".")[1].rstrip("0"))


def anova2_balanced(cells: dict) -> dict:
    """Two-way ANOVA with interaction, balanced forms.

    cells: dict[(a, t)] -> list of float observations (equal length per cell).
    within-df = N - number_of_cells.
    """
    ks = sorted({k[0] for k in cells})
    ts = sorted({k[1] for k in cells})
    allv = [x for k in cells for x in cells[k]]
    n = len(allv)
    gm = sum(allv) / n
    cm = {k: sum(v) / len(v) for k, v in cells.items()}
    am = {a: sum(cm[(a, t)] for t in ts) / len(ts) for a in ks}
    tm = {t: sum(cm[(a, t)] for a in ks) / len(ks) for t in ts}
    ss_a = sum(len(cells[k]) * (am[k[0]] - gm) ** 2 for k in cells)
    ss_t = sum(len(cells[k]) * (tm[k[1]] - gm) ** 2 for k in cells)
    ss_ab = sum(len(cells[k]) * (cm[k] - am[k[0]] - tm[k[1]] + gm) ** 2 for k in cells)
    ss_w = sum(sum((x - cm[k]) ** 2 for x in cells[k]) for k in cells)
    closure = abs((ss_a + ss_t + ss_ab + ss_w) - sum((x - gm) ** 2 for x in allv))
    df_w = n - len(cells)
    ms_w = ss_w / df_w
    df_a, df_t, df_i = len(ks) - 1, len(ts) - 1, (len(ks) - 1) * (len(ts) - 1)
    f_a, f_t, f_i = (ss_a / df_a) / ms_w, (ss_t / df_t) / ms_w, (ss_ab / df_i) / ms_w
    return {
        "N": n, "cells": len(cells),
        "SS_A": ss_a, "SS_T": ss_t, "SS_AB": ss_ab, "SS_w": ss_w, "MS_w": ms_w,
        "df_w": df_w,
        "F_A": f_a, "p_A": float(stats.f.sf(f_a, df_a, df_w)),
        "F_T": f_t, "p_T": float(stats.f.sf(f_t, df_t, df_w)),
        "F_AB": f_i, "p_AB": float(stats.f.sf(f_i, df_i, df_w)),
        "closure_residual": closure,
        "cell_means": {f"{k[0]}|{k[1]}": v for k, v in cm.items()},
        "alpha_marginals": {str(k): v for k, v in am.items()},
        "T_marginals": {str(k): v for k, v in tm.items()},
    }


def documented_subset(rows: list, n_per_cell: int) -> dict:
    """The manuscript's subset: first n_per_cell per cell, ascending (cell_idx, seed)."""
    rows = sorted(rows, key=lambda r: (r.get("cell_idx", 0), r.get("seed", 0)))
    by = defaultdict(list)
    for s in rows:
        by[(s["alpha_eval"], s["T"])].append(s["final_ECE"])
    return {k: v[:n_per_cell] for k, v in by.items()}


def ordering_sensitivity(rows: list, n_per_cell: int) -> list:
    """Same 15-per-cell size under different plausible orderings.

    Reported because the documented ordering is a convention, not a fact: if the
    result swings wildly across equally defensible orderings, the subset is
    carrying the conclusion rather than the other way round.
    """
    orders = {
        "documented_cell_idx_then_seed": lambda r: (r.get("cell_idx", 0), r.get("seed", 0)),
        "seed_ascending": lambda r: r.get("seed", 0),
        "seed_descending": lambda r: -r.get("seed", 0),
        "task_id_then_seed": lambda r: (str(r.get("task_id", "")), r.get("seed", 0)),
        "archive_list_order": None,  # None = preserve input order
    }
    out = []
    for name, key in orders.items():
        seq = rows if key is None else sorted(rows, key=key)
        by = defaultdict(list)
        for s in seq:
            by[(s["alpha_eval"], s["T"])].append(s["final_ECE"])
        if min(len(v) for v in by.values()) < n_per_cell:
            continue
        got = anova2_balanced({k: v[:n_per_cell] for k, v in by.items()})
        out.append({"ordering": name, "SS_w": got["SS_w"], "MS_w": got["MS_w"],
                    "F_A": got["F_A"], "p_A": got["p_A"],
                    "F_T": got["F_T"], "p_T": got["p_T"],
                    "F_AB": got["F_AB"], "p_AB": got["p_AB"]})
    return out


def exact_reachability(rows: list, n_per_cell: int, target_ss_w: float) -> dict:
    """Can ANY n_per_cell-per-cell subset give the stored `SS_within`?

    Exhaustive over the value-count vectors of each cell.  `final_ECE` takes few
    distinct values, so the achievable set of per-cell sums of squares is small
    and exactly computable in rational arithmetic.  A target outside that set is
    unreachable by ANY subset, which is stronger than "we failed to find one".

    The comparison is made at the precision the carrier actually STORES, not at
    exact equality.  Demanding exact equality between a rounded stored float and
    an exact rational would make Q3 contradict Q2: Q2 reproduces a block to within
    TOL_REL while Q3 calls the same block unreachable, purely because
    2.391666666666666 != 2.8975 at the 16th digit.  Both questions are asked about
    the same printed number, so both must be asked at printed precision.
    """
    by = defaultdict(list)
    for s in rows:
        by[(s["alpha_eval"], s["T"])].append(s["final_ECE"])

    # Cells that have exactly n_per_cell rows are forced in; their SS is fixed.
    forced = [k for k in by if len(by[k]) == n_per_cell]
    optional = [k for k in by if len(by[k]) > n_per_cell]
    forced_ss = Fraction(0)
    for k in forced:
        vals = [Fraction(str(x)) for x in by[k]]
        m = sum(vals) / len(vals)
        forced_ss += sum((v - m) ** 2 for v in vals)

    per_cell_sets = {}
    for k in optional:
        cnt = Counter(Fraction(str(x)) for x in by[k])
        keys = sorted(cnt)
        reach = set()
        for combo in itertools.product(*[range(cnt[v] + 1) for v in keys]):
            if sum(combo) != n_per_cell:
                continue
            vals = [v for c, v in zip(combo, keys) for _ in range(c)]
            m = sum(vals) / len(vals)
            reach.add(sum((v - m) ** 2 for v in vals))
        per_cell_sets[k] = reach

    target = Fraction(str(target_ss_w))
    prec = _decimals(target_ss_w)          # decimals the carrier stored
    tgt_rounded = round(target, prec)

    def _matches(r: Fraction) -> bool:
        return round(r, prec) == tgt_rounded

    if not per_cell_sets:
        # Every cell has exactly n_per_cell rows: there is ONE possible subset, so
        # the question is decided, not indeterminate.  Reporting INDETERMINATE here
        # would be wrong -- a perfectly balanced carrier is the easy case, not the
        # unanswerable one.
        ok = _matches(forced_ss)
        return {
            "target_SS_w": float(target), "target_precision_decimals": prec,
            "forced_cells": [f"{k[0]}|{k[1]}" for k in forced],
            "forced_SS_w": float(forced_ss), "optional_cells": [],
            "required_from_optional_cells": float(target - forced_ss),
            "n_reachable_sums": 1,
            "verdict": "REACHABLE" if ok else "UNREACHABLE",
            "nearest_reachable": float(forced_ss),
            "nearest_distance": float(abs(forced_ss - target)),
            "method": ("single possible subset (all cells exactly n_per_cell); "
                       "reachability decided directly"),
        }

    pool = [per_cell_sets[k] for k in optional]
    totals = sorted({sum(combo, Fraction(0)) + forced_ss
                     for combo in itertools.product(*pool)})
    hit = [r for r in totals if _matches(r)]
    nearest = min(totals, key=lambda v: abs(v - target)) if totals else None

    return {
        "target_SS_w": float(target), "target_precision_decimals": prec,
        "forced_cells": [f"{k[0]}|{k[1]}" for k in forced],
        "forced_SS_w": float(forced_ss),
        "optional_cells": [f"{k[0]}|{k[1]}" for k in optional],
        "required_from_optional_cells": float(target - forced_ss),
        "n_reachable_sums": len(totals),
        "verdict": "REACHABLE" if hit else "UNREACHABLE",
        "nearest_reachable": float(nearest) if nearest is not None else None,
        "nearest_distance": (float(abs(nearest - target))
                             if nearest is not None else None),
        "method": ("exact rational enumeration over per-cell value-count "
                   f"vectors, matched at {prec} decimals (the carrier's stored "
                   "precision)"),
    }


def internal_consistency(stored: dict) -> dict:
    """Q1: do the stored SS / MS / df / F / p agree with each other?"""
    checks = []

    def chk(name, s_val, g_val):
        if s_val is None or g_val is None:
            checks.append({"quantity": name, "stored": s_val, "recomputed": g_val,
                           "rel_err": None, "matches": None})
            return
        rel = abs(g_val - s_val) / abs(s_val) if s_val else float("inf")
        checks.append({"quantity": name, "stored": s_val, "recomputed": g_val,
                       "rel_err": rel, "matches": bool(rel <= TOL_REL)})

    msw = stored.get("MS_within")
    for q, fq, pq in (("alpha", "F_alpha", "p_alpha"),
                      ("T", "F_T", "p_T"),
                      ("interaction", "F_interaction", "p_interaction")):
        ss, ms, df = stored.get(f"SS_{q}"), stored.get(f"MS_{q}"), stored.get(f"df_{q}")
        if ms is not None and df is not None:
            chk(f"SS_{q}_vs_MS_df", ss, ms * df)
        if ms is not None and msw:
            chk(f"{fq}_vs_MS_ratio", stored.get(fq), ms / msw)
        if stored.get(fq) is not None:
            p = float(stats.f.sf(stored[fq], stored.get(f"df_{q}", 0),
                                 stored.get("df_within", 0)))
            # p-values are stored ROUNDED (4 s.f. at best, often `0.0` for
            # underflow).  Relative error is the wrong metric: a stored 0.0006
            # against a true 0.000577 differs by 3.8% and is a perfect match, and
            # a stored 0.0 cannot match 2.05e-06 at ANY relative tolerance.  Compare
            # on the absolute scale of the printed precision instead.
            st_p = stored.get(pq)
            tol_abs = 0.5 * 10 ** -_decimals(st_p)
            checks.append({"quantity": f"{pq}_vs_F_dist", "stored": st_p,
                           "recomputed": p,
                           "abs_err": abs(p - st_p) if st_p is not None else None,
                           "tol_abs": tol_abs,
                           "matches": (abs(p - st_p) <= tol_abs)
                           if st_p is not None else None})

    decided = [c for c in checks if c["matches"] is not None]
    ok = bool(decided) and all(c["matches"] for c in decided)
    return {"question": "Q1_internal_consistency",
            "verdict": "SELF_CONSISTENT" if ok else "INTERNALLY_INCONSISTENT",
            "checks": checks}


def _find_anova_block(doc: dict) -> dict:
    """The block is nested under `summary`; tolerate a top-level copy too."""
    for path in (("summary", "anova_ECE"), ("anova_ECE",)):
        cur = doc
        for p in path:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                cur = None
                break
        if isinstance(cur, dict):
            return cur
    return {}


def analyse(carrier_path: Path) -> dict:
    doc = json.loads(carrier_path.read_text())
    sessions = doc.get("sessions")
    if not isinstance(sessions, list) or not sessions:
        return {"verdict": "SKIP_NO_SESSIONS", "carrier": str(carrier_path)}

    rows = [s for s in sessions
            if s.get("T") in T_LEVELS and "final_ECE" in s
            and "alpha_eval" in s]
    if not rows:
        return {"verdict": "SKIP_NO_MATCHING_ROWS", "carrier": str(carrier_path)}

    stored = _find_anova_block(doc)
    n_per_cell = int(stored.get("n_per_cell") or 15)

    actual_sizes = {f"{a}|{t}": sum(1 for r in rows
                                    if r["alpha_eval"] == a and r["T"] == t)
                    for a, t in sorted({(r["alpha_eval"], r["T"]) for r in rows})}

    balanced = documented_subset(rows, n_per_cell)
    got = anova2_balanced(balanced)
    q1 = internal_consistency(stored)

    q2_checks = []
    for name, s_val, g_val in (
        ("SS_within", stored.get("SS_within"), got["SS_w"]),
        ("F_alpha", stored.get("F_alpha"), got["F_A"]),
        ("F_T", stored.get("F_T"), got["F_T"]),
        ("F_interaction", stored.get("F_interaction"), got["F_AB"]),
    ):
        if s_val is None:
            q2_checks.append({"quantity": name, "stored": None,
                              "recomputed": g_val, "rel_err": None, "matches": None})
            continue
        rel = abs(g_val - s_val) / abs(s_val) if s_val else float("inf")
        q2_checks.append({"quantity": name, "stored": s_val, "recomputed": g_val,
                          "rel_err": rel, "matches": bool(rel <= TOL_REL)})

    decided = [c for c in q2_checks if c["matches"] is not None]
    reproduced = bool(decided) and all(c["matches"] for c in decided)

    reach = exact_reachability(rows, n_per_cell, stored["SS_within"]) \
        if stored.get("SS_within") is not None else {"verdict": "NO_STORED_SS_W"}

    return {
        "verdict": "REPRODUCED" if reproduced else "NOT_REPRODUCIBLE",
        "carrier": str(carrier_path),
        "anova_block_path": "summary.anova_ECE" if "summary" in doc else "top-level",
        "n_per_cell_from_stored_block": n_per_cell,
        "actual_cell_sizes": actual_sizes,
        "carrier_is_unbalanced": len(set(actual_sizes.values())) > 1,
        "documented_subset": "first n_per_cell per cell, ascending (cell_idx, seed)",
        "closure_residual": got["closure_residual"],
        "Q1_internal_consistency": q1,
        "Q2_from_raw_sessions": {
            "verdict": "REPRODUCED" if reproduced else "NOT_REPRODUCIBLE",
            "recomputed": got,
            "checks": q2_checks,
            "tolerance_rel": TOL_REL,
        },
        "Q3_exact_reachability": reach,
        "ordering_sensitivity": ordering_sensitivity(rows, n_per_cell),
        "interpretation": (
            "Q1 says the stored block agrees with itself; Q2/Q3 say whether the raw "
            "sessions can produce it. UNREACHABLE in Q3 means no subset of the "
            "delivered rows can yield the stored SS_within at all."
        ),
        "tolerance_rel": TOL_REL,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carrier", type=Path,
                    help="path to joint_full_F_v10_results.json")
    ap.add_argument("--out", type=Path, help="write the report JSON here")
    args = ap.parse_args()

    if not args.carrier.exists():
        print(f"carrier not found: {args.carrier}", file=sys.stderr)
        return 3

    rep = analyse(args.carrier)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rep, indent=2))

    v = rep["verdict"]
    print(f"verdict: {v}   (anova block: {rep.get('anova_block_path')})")
    if v.startswith("SKIP"):
        return 3

    q1 = rep["Q1_internal_consistency"]
    print(f"\nQ1 stored-block self-consistency: {q1['verdict']}")
    for c in q1["checks"]:
        if c["matches"] is None:
            continue
        flag = "OK " if c["matches"] else "MISMATCH"
        if "abs_err" in c:  # p-value: absolute tolerance on printed precision
            print(f"    {c['quantity']:22s} stored={c['stored']:<12.6g} "
                  f"recomputed={c['recomputed']:<12.6g} "
                  f"abs={c['abs_err']:.2e} tol={c['tol_abs']:.2e}  {flag}")
        else:               # SS / MS / F: relative tolerance
            print(f"    {c['quantity']:22s} stored={c['stored']:<12.6g} "
                  f"recomputed={c['recomputed']:<12.6g} rel={c['rel_err']:.2e}  {flag}")

    g = rep["Q2_from_raw_sessions"]["recomputed"]
    print(f"\nQ2 from raw sessions: {rep['Q2_from_raw_sessions']['verdict']}")
    print(f"    closure residual = {rep['closure_residual']:.3e}")
    print(f"    N={g['N']} df_w={g['df_w']} SS_w={g['SS_w']:.4f} MS_w={g['MS_w']:.5f}")
    for c in rep["Q2_from_raw_sessions"]["checks"]:
        s, r = c["stored"], c["recomputed"]
        if s is None:
            print(f"    {c['quantity']:14s} stored=(absent)      recomputed={r:.4f}")
        else:
            flag = "OK " if c["matches"] else "MISMATCH"
            print(f"    {c['quantity']:14s} stored={s:<10.4f} recomputed={r:<10.4f} "
                  f"rel_err={c['rel_err']:.4f}  {flag}")

    q3 = rep["Q3_exact_reachability"]
    print(f"\nQ3 exact reachability: {q3['verdict']}")
    if q3["verdict"] != "INDETERMINATE":
        print(f"    forced cells {q3['forced_cells']} -> SS_w = {q3['forced_SS_w']:.6f}")
        print(f"    required from optional {q3['optional_cells']}: "
              f"{q3['required_from_optional_cells']:.6f}")
        print(f"    {q3['n_reachable_sums']} reachable sums; "
              f"nearest {q3['nearest_reachable']:.6f} "
              f"(distance {q3['nearest_distance']:.6f})")

    print("\nordering sensitivity (documented size, different defensible orderings):")
    for r in rep["ordering_sensitivity"]:
        print(f"    {r['ordering']:28s} F_alpha={r['F_A']:8.4f} p={r['p_A']:.5f}   "
              f"F_T={r['F_T']:7.4f}   F_int={r['F_AB']:7.4f}")

    return 0 if v == "REPRODUCED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
