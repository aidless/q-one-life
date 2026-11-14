#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""acceptance_gate_audit.py — inventory and audit every McNemar gate in a tree.

Candidate F (self-evolution acceptance-rule blind spots), F-02.

WHY
---
F-01 found that `evo_agent/frozen_v6/evolve.py::mcnemar_exact` is not exact: it
switches to a normal approximation at n>25 and that approximation promotes
variants the exact test holds. The obvious next question is whether that is one
sloppy file or a pattern. This tool answers it by walking a tree, locating every
function that computes a McNemar / paired-binomial p-value, and classifying how
it does so.

CLASSIFICATION (static, from the function body via ast)
  exact-only    has an exact combinatorial term (comb/factorial/binomtest), no erf
  approx-only   has a normal tail (erf / normal CDF), no exact term
  hybrid        BOTH — an exact branch and an approximation branch. A hybrid is
                where an unnamed-but-unstated switch can silently change a
                promote/hold decision, so hybrids are the audit's priority.
  unknown       neither term visible; needs manual reading, reported not ignored.

A file whose function is *named* `mcnemar_exact` but classifies as `hybrid`
disagrees with its own name. That is the F-relevant finding: the name is a
rigour claim the body does not honour.

DYNAMIC AUDIT (--audit path.py:funcname)
  Loads the function and runs it against the exact test over the flip region,
  reporting decision flips. Import is done by file path, so the module is not
  required to be on sys.path.

FAIL-CLOSED
  --workspace-scan exits non-zero if it finds zero implementations (a silent
  empty result would read as "nothing to audit"), and --audit exits non-zero if
  the target cannot be imported or called.

    python3 acceptance_gate_audit.py --workspace-scan --root /path/to/tree
    python3 acceptance_gate_audit.py --audit evo_agent/frozen_v6/evolve.py:mcnemar_exact
    python3 acceptance_gate_audit.py --selftest [--inject <name>]
"""
import argparse
import ast
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mcnemar_audit import exact_p, _require_scipy, ALPHA  # noqa: E402

# Formula-exactness tolerance: generous enough for 4-decimal output rounding,
# far tighter than any real approximation error (observed >= 8e-3).
EXACT_TOL = 1e-4

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", "site-packages", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".tox",
}
# A name that suggests a McNemar / paired-binomial test.
NAME_RE = re.compile(r"(mcnemar|paired.*binom|binom.*paired|mcnemar_two_sided)", re.I)
EXACT_TOKENS = ("comb(", "factorial(", "binomtest", "math.comb")
# chi2 is listed because a McNemar chi-square (with or without a Yates
# correction) is an asymptotic approximation, not an exact test. Omitting it
# would have let `mcnemar_chi2` fall through to `unknown` and read as fine.
APPROX_TOKENS = ("erf(", "erfc(", "norm.cdf", "NormalDist", "chi2", "chisq")


def classify(body_src):
    has_exact = any(t in body_src for t in EXACT_TOKENS)
    has_approx = any(t in body_src for t in APPROX_TOKENS)
    if has_exact and has_approx:
        return "hybrid"
    if has_exact:
        return "exact-only"
    if has_approx:
        return "approx-only"
    return "unknown"


def walk_impls(root):
    """Yield every function whose name matches NAME_RE, with its source and class."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                src = open(path, encoding="utf-8", errors="ignore").read()
                tree = ast.parse(src)
            except Exception:
                continue
            lines = src.splitlines()
            for node in ast.walk(tree):
                if not isinstance(node, ast.FunctionDef):
                    continue
                if not NAME_RE.search(node.name):
                    continue
                seg = "\n".join(lines[node.lineno - 1:getattr(node, "end_lineno", node.lineno)])
                out.append({
                    "path": os.path.relpath(path, root),
                    "name": node.name,
                    "lineno": node.lineno,
                    "classification": classify(seg),
                    "body_lines": getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                })
    return out


def _coerce_p(value):
    """Extract a scalar p-value from the several shapes the workspace uses.

    Implementations return float, (p, side), or {"p": ..., ...}. Anything else
    is reported rather than silently treated as a number.
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, tuple) and value and isinstance(value[0], (int, float)):
        return float(value[0])
    if isinstance(value, dict):
        for k in ("p", "pvalue", "p_value"):
            if isinstance(value.get(k), (int, float)):
                return float(value[k])
    raise TypeError(f"unsupported return shape: {type(value).__name__}")


def dynamic_audit(path, funcname, n_max=500):
    """Import path:funcname by file path and run the flip scan against exact."""
    _require_scipy()
    if n_max < 26:
        # vacuous-truth guard: a zero-cell region would report is_exact=True
        # and max_abs_error=0.0 with no evidence whatsoever.
        print(f"FAIL-CLOSED: n_max {n_max} below region floor 26; an empty region must not read as exact", file=sys.stderr)
        return None
    if not os.path.exists(path):
        print(f"FAIL-CLOSED: no such file {path}", file=sys.stderr)
        return None
    spec = importlib.util.spec_from_file_location("_audited_mod", path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        print(f"FAIL-CLOSED: import of {path} failed: {exc}", file=sys.stderr)
        return None
    fn = getattr(mod, funcname, None)
    if fn is None:
        print(f"FAIL-CLOSED: {path} has no attribute {funcname}", file=sys.stderr)
        return None

    cells = flips = promotions = 0
    worst = 0.0
    worst_at = None
    for n in range(26, n_max + 1):
        for c in range(0, n // 2 + 1):
            b = n - c
            cells += 1
            try:
                got = _coerce_p(fn(b, c))
            except Exception as exc:
                print(f"FAIL-CLOSED: {funcname}({b},{c}) raised {exc}", file=sys.stderr)
                return None
            ref = exact_p(b, c)
            if abs(got - ref) > worst:
                worst, worst_at = abs(got - ref), (b, c, got, ref)
            if got < ALPHA:
                promotions += 1
            if (got < ALPHA) != (ref < ALPHA):
                flips += 1
    # Two separate questions, kept separate:
    #   decision_flips  — does the implementation change a promote/hold verdict?
    #   max_abs_error   — how far is the number itself?
    # `is_exact` is judged against EXACT_TOL, not 1e-12, because several
    # implementations in this workspace are formula-exact but round their output
    # to 4 decimals (e.g. rag_min_demo/bline/w3_harness.py: `round(..., 4)`),
    # which produces up to 5e-5 of benign error. Calling that "not exact" would
    # be a false alarm; the rounding is reported separately instead.
    is_exact = bool(flips == 0 and worst <= EXACT_TOL)
    return {
        "target": f"{path}:{funcname}",
        "region": {"n_min": 26, "n_max": n_max, "constraint": "b >= c"},
        "cells": cells,
        "promotions_by_target": promotions,
        "decision_flips": flips,
        "flip_rate_among_promotions": (flips / promotions) if promotions else None,
        "max_abs_error": float(worst),
        "max_abs_error_at": {"b": worst_at[0], "c": worst_at[1],
                             "p_target": float(worst_at[2]), "p_exact": float(worst_at[3])} if worst_at else None,
        "is_exact": is_exact,
        "exactness_tolerance": EXACT_TOL,
        "output_rounded": bool(flips == 0 and 0 < worst <= EXACT_TOL),
    }


def selftest(verbose=True, inject=None):
    ok = True
    violations = []

    def check(label, cond, detail=""):
        nonlocal ok
        if not cond:
            ok = False
            violations.append(label)
        if verbose:
            print(f"  [{'ok' if cond else 'FAIL'}] {label}{(' — ' + detail) if detail else ''}")

    # --- classifier is correct on known-shaped bodies ------------------------
    check("classify exact body", classify("k=min(b,c); return 2*sum(comb(n,i) for i in range(k+1))/2**n") == "exact-only")
    check("classify approx body", classify("z=abs(b-c)/math.sqrt(n); return 2*(1-0.5*(1+math.erf(z/math.sqrt(2))))") == "approx-only")
    check("classify hybrid body",
          classify("if n<=25:\n  return comb(n,1)\nreturn math.erf(1)") == "hybrid")
    check("classify unknown body", classify("return 0.5") == "unknown")

    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    impls = walk_impls(root)

    if inject == "empty-scan":
        impls = []

    if inject == "no-hybrids":
        impls = [i for i in impls if i["classification"] != "hybrid"]

    if inject == "mislabelled":
        for i in impls:
            if i["classification"] == "hybrid":
                i["classification"] = "exact-only"

    if inject == "skip-renamed":
        # An auditor that walks past the functions it most needs to check.
        impls = [i for i in impls if i["name"] != "mcnemar_exact"]

    check("workspace scan finds implementations (non-empty)",
          len(impls) > 0, str(len(impls)))
    names = {i["name"] for i in impls}
    check("scan locates the F-01 target evolve.py::mcnemar_exact",
          any(i["name"] == "mcnemar_exact" and "frozen_v6" in i["path"] for i in impls))
    hybrids = [i for i in impls if i["classification"] == "hybrid"]
    check("at least one hybrid (exact+approx) implementation exists",
          len(hybrids) > 0, f"{len(hybrids)} hybrids: {[h['path'] for h in hybrids][:5]}")
    check("every implementation is classified (none silently dropped)",
          all(i["classification"] in {"exact-only", "approx-only", "hybrid", "unknown"} for i in impls))
    misnamed = [i for i in impls if i["name"] == "mcnemar_exact" and i["classification"] == "hybrid"]
    check("found a function NAMED exact that is actually hybrid (name/body disagreement)",
          len(misnamed) > 0, f"{[m['path'] for m in misnamed]}")

    # --- dynamic audit on the importable F-01 target -------------------------
    tgt = os.path.join(root, "evo_agent", "frozen_v6", "evolve.py")
    dyn = dynamic_audit(tgt, "mcnemar_exact", n_max=200) if os.path.exists(tgt) else None
    if dyn is not None:
        if inject == "dynamic-clean":
            dyn["decision_flips"] = 0
            dyn["is_exact"] = True
        check("dynamic audit reproduces the F-01 flip count (>0)",
              dyn["decision_flips"] > 0, str(dyn["decision_flips"]))
        check("dynamic audit says the target is NOT exact",
              dyn["is_exact"] is False)
    else:
        check("dynamic audit ran on the F-01 target", False, "target missing")

    # --- vacuous-region guard ------------------------------------------------
    vac = dynamic_audit(tgt, "mcnemar_exact", n_max=20) if os.path.exists(tgt) else None
    if inject == "vacuous-exact":
        # simulate the pre-fix behavior: an empty region reading as exact
        vac = {"decision_flips": 0, "is_exact": True, "max_abs_error": 0.0, "cells": 0}
    check("vacuous region (n_max<26) is refused, not reported exact",
          vac is None, "returned " + ("a result dict" if isinstance(vac, dict) else str(vac)))

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
    ap.add_argument("--workspace-scan", action="store_true")
    ap.add_argument("--root", default=None, help="tree to scan (default: workspace root)")
    ap.add_argument("--audit", default=None, help="path.py:funcname to audit dynamically")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--inject", default=None,
                    choices=["empty-scan", "no-hybrids", "mislabelled", "skip-renamed", "dynamic-clean", "vacuous-exact"])
    ap.add_argument("--json", default=None)
    ap.add_argument("--n-max", type=int, default=500)
    a = ap.parse_args()

    if a.inject and not a.selftest:
        print("--inject requires --selftest", file=sys.stderr)
        return 2

    if a.selftest:
        return 0 if selftest(verbose=True, inject=a.inject) else 1

    if a.audit:
        path, _, fn = a.audit.rpartition(":")
        if not path:
            print("FAIL-CLOSED: --audit expects path.py:funcname", file=sys.stderr)
            return 2
        res = dynamic_audit(path, fn, n_max=a.n_max)
        if res is None:
            return 2
        print(json.dumps(res, indent=2))
        return 0

    if a.workspace_scan:
        root = a.root or os.path.abspath(os.path.join(HERE, "..", ".."))
        impls = walk_impls(root)
        if not impls:
            # fail-closed: an empty inventory must not read as "all clear"
            print(f"FAIL-CLOSED: no McNemar implementation found under {root}",
                  file=sys.stderr)
            return 2
        by = {}
        for i in impls:
            by.setdefault(i["classification"], []).append(i)
        print(f"root: {root}")
        print(f"implementations found: {len(impls)}")
        for k in ("hybrid", "approx-only", "exact-only", "unknown"):
            if k in by:
                print(f"\n  {k} ({len(by[k])}):")
                for i in by[k]:
                    flag = "  <-- name claims exact" if (
                        i["name"] == "mcnemar_exact" and k == "hybrid") else ""
                    print(f"    {i['path']}:{i['lineno']}  {i['name']}(){flag}")
        if a.json:
            with open(a.json, "w") as fh:
                json.dump({"root": root, "count": len(impls), "impls": impls}, fh, indent=2)
            print(f"\nwrote {a.json}")
        return 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
