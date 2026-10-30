#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mcnemar_audit.py — audit a promotion gate's McNemar implementation.

Candidate F (self-evolution acceptance-rule blind spots), F-01.

WHY THIS EXISTS
---------------
`evo_agent/frozen_v6/evolve.py` decides promotion with

    promote = bool(new_wins > old_wins and p < 0.05)

and computes `p` with

    mcnemar_exact(b, c)   # exact when n = b + c <= 25, normal approximation above

That name is wrong twice over: the function is not exact above n=25, and the
normal approximation it falls back to is *anti-conservative* near the decision
boundary — it reports significance in cells where the exact conditional test
does not. The shift at n=26 is a hard discontinuity in the very region where
choices are made: 145 candidate modifications, few discordant pairs.

This script recomputes every cell in the fallback region against an independent
reference (scipy.stats.binomtest, the exact conditional binomial test) and
counts the cells where the two disagree *about the promotion decision*.

FAIL-CLOSED
-----------
The independent reference is scipy. If scipy is unavailable the audit cannot
establish anything, so it exits non-zero rather than falling back to a
home-made exact test that could share the same mistake.

    python3 mcnemar_audit.py --selftest
    python3 mcnemar_audit.py --selftest --inject <name>
    python3 mcnemar_audit.py --scan --n-max 500
"""
import argparse
import json
import math
import sys
from math import comb

ALPHA = 0.05

# --- the implementation under audit, transcribed verbatim from evolve.py -----


def mcnemar_exact(b, c):
    """The audited function. Copied from evo_agent/frozen_v6/evolve.py:12-25.

    Kept character-identical in behaviour so the audit measures the real code,
    not a paraphrase of it.
    """
    n = b + c
    if n == 0:
        return 1.0
    if n <= 25:
        k = min(b, c)
        return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)
    z = abs(b - c) / math.sqrt(n)
    p = 2 * (1 - 0.5 * (1 + math.erf(z / math.sqrt(2))))
    return p


# --- independent reference --------------------------------------------------


def exact_p(b, c):
    """Two-sided exact conditional binomial p, via scipy (independent of the code)."""
    from scipy.stats import binomtest

    n = b + c
    if n == 0:
        return 1.0
    # float() because scipy hands back numpy scalars, which are not JSON
    # serialisable and compare as numpy bools downstream.
    return float(binomtest(min(b, c), n, 0.5).pvalue)


def _require_scipy():
    try:
        import scipy.stats  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment dependent
        print(f"FAIL-CLOSED: scipy unavailable ({exc}); cannot audit.", file=sys.stderr)
        sys.exit(2)


# --- audit ------------------------------------------------------------------


def scan(n_max=500, inject=None):
    """Sweep the fallback region n in [26, n_max], all splits with b >= c.

    b >= c because the gate is directional (`new_wins > old_wins`); ties carry no
    promotion. Every cell is judged twice: by the audited code and by the
    independent exact test.
    """
    cells = 0
    flips = []          # cells where the two disagree about p < ALPHA
    promotions = 0      # cells the audited code would promote
    max_err = 0.0
    max_err_at = None

    for n in range(26, n_max + 1):
        for c in range(0, n // 2 + 1):
            b = n - c
            got = mcnemar_exact(b, c)
            ref = exact_p(b, c)
            cells += 1

            err = abs(got - ref)
            if err > max_err:
                max_err, max_err_at = err, (b, c, got, ref)

            if got < ALPHA:
                promotions += 1

            if (got < ALPHA) != (ref < ALPHA):
                flips.append({
                    "b": b, "c": c, "n": n,
                    "p_code": got, "p_exact": ref,
                    "ratio_exact_over_code": (ref / got) if got > 0 else None,
                    # anti-conservative == the code promotes where exact does not
                    "anti_conservative": bool(got < ALPHA and ref >= ALPHA),
                })

    flips.sort(key=lambda r: r["p_code"])

    if inject == "conservative-bias":
        # Fabricate the opposite conclusion: claim the code is too STRICT.
        for f in flips:
            f["anti_conservative"] = False

    if inject == "no-flips":
        flips = []

    if inject == "same-reference":
        # Collapse the reference onto the code, destroying independence.
        return _scan_self_referential(n_max)

    return {
        "region": {"n_min": 26, "n_max": n_max, "constraint": "b >= c"},
        "cells": cells,
        "promotions_by_code": promotions,
        "decision_flips": len(flips),
        "flip_rate_among_promotions": (len(flips) / promotions) if promotions else None,
        "all_flips_anti_conservative": all(f["anti_conservative"] for f in flips) if flips else None,
        "max_abs_error": max_err,
        "max_abs_error_at": {"b": max_err_at[0], "c": max_err_at[1],
                             "p_code": max_err_at[2], "p_exact": max_err_at[3]} if max_err_at else None,
        "most_severe_flips": flips[:10],
    }


def _scan_self_referential(n_max):
    """What the scan would report if 'exact' were the code itself.

    Used only as an injection: it must be detected, because an audit whose
    reference IS the audited function can never find anything.
    """
    cells = 0
    for n in range(26, n_max + 1):
        for c in range(0, n // 2 + 1):
            cells += 1
    return {
        "region": {"n_min": 26, "n_max": n_max},
        "cells": cells, "promotions_by_code": cells,
        "decision_flips": 0, "flip_rate_among_promotions": 0.0,
        "all_flips_anti_conservative": None, "max_abs_error": 0.0,
        "max_abs_error_at": None, "most_severe_flips": [],
    }


def selftest(verbose=True, inject=None):
    """Two distinct outcomes.

    `ok`         — every clean invariant holds.
    `violations` — labels of invariants that broke. Under --inject, a non-empty
                   violation list IS the detection: the gate going red is the
                   proof the gate is not decorative.

    Exit convention (matching the other gates in this repo):
      clean              -> exit 0
      injected, detected -> exit 1  (correctly RED)
      injected, silent   -> exit 0  (FAILURE: the injection slipped through)
    """
    _require_scipy()
    ok = True
    violations = []

    def check(label, cond, detail=""):
        nonlocal ok
        if not cond:
            ok = False
            violations.append(label)
        if verbose:
            print(f"  [{'ok' if cond else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")

    # ---- the audited function reproduces evolve.py exactly (regression pin) --
    check("mcnemar_exact(18,8) reproduces evolve.py = 0.049860",
          abs(mcnemar_exact(18, 8) - 0.049860) < 5e-7, f"{mcnemar_exact(18,8):.6f}")
    check("mcnemar_exact(19,8) reproduces evolve.py = 0.034264",
          abs(mcnemar_exact(19, 8) - 0.034264) < 5e-7, f"{mcnemar_exact(19,8):.6f}")

    # ---- the reference disagrees: scipy says these are NOT significant ------
    check("exact_p(18,8) = 0.075519 > alpha while code says 0.049860 < alpha",
          exact_p(18, 8) > ALPHA > mcnemar_exact(18, 8),
          f"exact {exact_p(18,8):.6f} vs code {mcnemar_exact(18,8):.6f}")
    check("exact_p(19,8) = 0.052239 > alpha while code says 0.034264 < alpha",
          exact_p(19, 8) > ALPHA > mcnemar_exact(19, 8),
          f"exact {exact_p(19,8):.6f} vs code {mcnemar_exact(19,8):.6f}")

    # ---- the n=25/26 discontinuity: exact path is fine, fallback is not -----
    check("below the switch (n=25) the code IS exact",
          abs(mcnemar_exact(17, 8) - exact_p(17, 8)) < 1e-12,
          f"{mcnemar_exact(17,8):.10f} vs {exact_p(17,8):.10f}")
    check("above the switch (n=26) the code is NOT exact",
          abs(mcnemar_exact(18, 8) - exact_p(18, 8)) > 1e-3,
          f"err {abs(mcnemar_exact(18,8) - exact_p(18,8)):.5f}")

    # ---- the headline scan --------------------------------------------------
    res = scan(n_max=500, inject=inject)

    check("scan covers the fallback region", res["cells"] > 10000, str(res["cells"]))
    check("scan finds at least one decision flip",
          res["decision_flips"] > 0, str(res["decision_flips"]))
    check("every flip is anti-conservative (code promotes, exact does not)",
          res["all_flips_anti_conservative"] is True,
          str(res["all_flips_anti_conservative"]))
    check("no flip has the code being stricter than exact",
          all(f["anti_conservative"] for f in res["most_severe_flips"])
          if res["most_severe_flips"] else False)
    check("most severe flip has exact/code p ratio > 1.2",
          res["most_severe_flips"] and res["most_severe_flips"][0]["ratio_exact_over_code"] > 1.2,
          f"{res['most_severe_flips'][0]['ratio_exact_over_code']:.3f}"
          if res["most_severe_flips"] else "none")
    check("max absolute error exceeds 0.1 (large even away from the boundary)",
          res["max_abs_error"] > 0.1, f"{res['max_abs_error']:.6f}")
    _severe = res["most_severe_flips"]
    _band = [f for f in _severe if 26 <= f["n"] <= 27]
    check("the n=26..27 discontinuity band itself contains flips",
          len(_band) > 0,
          f"{[f['n'] for f in _band]}" if _band else "no flip in band")
    check("the most severe flip has n > 27 (the unsoundness is not only at the switch)",
          bool(_severe) and _severe[0]["n"] > 27,
          f"n={_severe[0]['n']}" if _severe else "no flips reported")

    # ---- injection outcome --------------------------------------------------
    # A non-empty violation list is the detection. No per-injection assertions:
    # the invariants above are the oracle, and an injection that leaves them all
    # intact has genuinely slipped through.
    if inject is not None:
        detected = len(violations) > 0
        if verbose:
            if detected:
                print(f"\nINJECTION '{inject}': DETECTED — {len(violations)} invariant(s) broke:")
                for v in violations:
                    print(f"    - {v}")
            else:
                print(f"\nINJECTION '{inject}': *** NOT DETECTED — GATE IS DECORATIVE ***")
        return not detected

    if verbose:
        print(f"\nRESULT: {'ALL PASS' if ok else 'FAILURES PRESENT'}  (exit {0 if ok else 1})")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--n-max", type=int, default=500)
    ap.add_argument("--inject", default=None,
                    choices=["no-flips", "conservative-bias", "same-reference"])
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    if a.inject and not a.selftest:
        print("--inject requires --selftest", file=sys.stderr)
        return 2

    if a.selftest:
        return 0 if selftest(verbose=True, inject=a.inject) else 1

    if a.scan:
        res = scan(n_max=a.n_max)
        text = json.dumps(res, indent=2)
        if a.json:
            with open(a.json, "w") as fh:
                fh.write(text)
            print(f"wrote {a.json}")
        print(text)
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
