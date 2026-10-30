# -*- coding: utf-8 -*-
"""B1 evidence re-derivation for tmlr-paper2-consolidated (dispatch b1w1-tmlr-paper2-consolidated-20260926T174617Z).

Deterministic re-derivation of the carrier-gate-flagged headline numbers, using ONLY:
  (a) the staged artifacts in this evidence/ directory (copied verbatim from
      /data3/Research/PAPER2_CONSOLIDATED), and
  (b) closed-form formulas stated in the manuscript (source/main.tex).

Comparison rules (declared per entry):
  R1  exact string match between the paper's decimal rendering and the artifact
      value formatted to the paper's precision (zero-padding allowed).
  R3  recompute from stated formula / artifact inputs; match iff
      round(recomputed, paper_dp) equals the paper value.
  R2  same as R3 but accepted within one display-unit-of-last-place (|delta| <= 1e-3
      for 3-decimal displays); the slack is recorded explicitly.

Writes b1_carrier_rederivation_20260927.json next to this script. No file outside
runs/tmlr-paper2-consolidated/source/evidence/ is modified.
"""
import hashlib
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def sig(x):
    return 1.0 / (1.0 + math.exp(-x))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def load(name):
    p = os.path.join(HERE, name)
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return p, sha256(p), data


results = []
artifacts = {}


def add(value, line, carrier, pointer, found, rule, agree, note=""):
    results.append({
        "paper_value": value, "paper_line": line, "carrier": carrier,
        "json_path_or_cell": pointer, "recomputed_or_found": found,
        "rule": rule, "agrees": agree, "note": note,
    })


# ---- staged artifacts -------------------------------------------------------
p_bh, h_bh, bh = load("p2_bound_vs_heuristic_20260808.json")
p_dc, h_dc, dc = load("p2_bound_decision_case_20260808.json")
p_ss, h_ss, ss = load("p2_sampling_theorem_sim_20260808.json")
artifacts = {
    "p2_bound_vs_heuristic_20260808.json": h_bh,
    "p2_bound_decision_case_20260808.json": h_dc,
    "p2_sampling_theorem_sim_20260808.json": h_ss,
}

# ---- 1) L373: 2.72 = observation-budget ratio ------------------------------
ratio_exact = bh["bound_total"] / bh["heur_total"]
add("2.72", "L373", "p2_bound_vs_heuristic_20260808.json", "/total_ratio",
    bh["total_ratio"], "R3: round(bound_total/heur_total, 2) == 2.72",
    round(ratio_exact, 2) == 2.72,
    "bound_total=5434, heur_total=2000, 5434/2000=%.4f -> 2.72" % ratio_exact)

# ---- 2-3) L262/L266: gamma 0.9790 / 0.9360 ---------------------------------
dcg = {r["condition"]: r["gamma"] for r in dc["rows"]}
add("0.9790", "L262", "p2_bound_decision_case_20260808.json",
    "/rows/%d/gamma (condition='Ablation no-s0')" % [r["condition"] for r in dc["rows"]].index("Ablation no-s0"),
    dcg["Ablation no-s0"], "R1: render 0.979 at 4 dp == '0.9790'",
    ("%.4f" % dcg["Ablation no-s0"]) == "0.9790",
    "provenance caveat: raw archive mm_epc_ablation_no_s0.json not archived; this derived artifact carries the value")
add("0.9360", "L266", "p2_bound_decision_case_20260808.json",
    "/rows/%d/gamma (condition='DS self-eval r30')" % [r["condition"] for r in dc["rows"]].index("DS self-eval r30"),
    dcg["DS self-eval r30"], "R1: render 0.936 at 4 dp == '0.9360'",
    ("%.4f" % dcg["DS self-eval r30"]) == "0.9360",
    "provenance caveat: raw archive mm_epc_ds_selfeval_r30.json not archived; this derived artifact carries the value")
# internal consistency of the decision-case artifact (formula from paper L373)
for cond in ("Ablation no-s0", "DS self-eval r30"):
    row = [r for r in dc["rows"] if r["condition"] == cond][0]
    g = row["gamma"]
    n30 = 1.0 / (g ** 2 * 0.30 ** 2 * sig(g) * (1 - sig(g)))
    assert abs(n30 - row["N_for_CV0.30"]) <= 0.05, cond

# ---- 4) L242/L212: r=-0.9977, LOO [-0.9997,-0.9963] -----------------------
# carrier = the five rows of Table tab:triangle-11 (source/main.tex L231-235),
# staged here verbatim; recomputation is deterministic (scipy-free implementation).
tab = {"DS Self-Eval": (0.033, 0.999), "DS x Qwen": (0.187, 0.988),
       "Qwen x DS": (0.766, 0.931), "Ablation mid": (0.560, 0.954),
       "Ablation max": (1.038, 0.913)}


def pearson(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return sxy / math.sqrt(sxx * syy)


def pearson_p(r, n):
    # survival of |t| with df=n-2 via incomplete beta: p = I_{df/(df+t^2)}(df/2, 1/2)
    tt2 = (r * r * (n - 2)) / (1 - r * r)
    df = n - 2
    x = df / (df + tt2)

    def betacf(a, b, xx):
        MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
        qab, qap, qam = a + b, a + 1.0, a - 1.0
        c, d = 1.0, 1.0 - qab * xx / qap
        if abs(d) < FPMIN:
            d = FPMIN
        d = 1.0 / d
        h = d
        for m in range(1, MAXIT + 1):
            m2 = 2 * m
            aa = m * (b - m) * xx / ((qam + m2) * (a + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            h *= d * c
            aa = -(a + m) * (qab + m) * xx / ((a + m2) * (qap + m2))
            d = 1.0 + aa * d
            if abs(d) < FPMIN:
                d = FPMIN
            c = 1.0 + aa / c
            if abs(c) < FPMIN:
                c = FPMIN
            d = 1.0 / d
            de = d * c
            h *= de
            if abs(de - 1.0) < EPS:
                break
        return h

    # regularized incomplete beta I_x(a,b)
    a, b = df / 2.0, 0.5
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(lbeta + a * math.log(x) + b * math.log(1 - x))
    if x < (a + 1) / (a + b + 2):
        return front * betacf(a, b, x) / a
    return 1.0 - front * betacf(b, a, 1 - x) / b


gx = [v[0] for v in tab.values()]
hy = [v[1] for v in tab.values()]
r_full = pearson(gx, hy)
p_full = pearson_p(r_full, 5)
loo = []
keys = list(tab)
for i in range(5):
    xs = [gx[j] for j in range(5) if j != i]
    ys = [hy[j] for j in range(5) if j != i]
    loo.append(pearson(xs, ys))
add("0.9977", "L212, L242", "Table tab:triangle-11 rows (source/main.tex L231-235)",
    "five (gamma,H) pairs", round(r_full, 4),
    "R3: Pearson r from the five table rows, rounded to 4 dp",
    ("%.4f" % abs(r_full)) == "0.9977",
    "recomputed r=%.6f, p=%.6f (paper 0.0001 at 4dp); cross-checked against REVIEW_CARD_source_project.md manual check" % (r_full, p_full))
add("0.9997", "L242", "Table tab:triangle-11 rows", "LOO leave-one-condition-out min",
    round(min(loo), 4), "R3: min LOO r rounded to 4 dp", ("%.4f" % abs(min(loo))) == "0.9997")
add("0.9963", "L242", "Table tab:triangle-11 rows", "LOO leave-one-condition-out max",
    round(max(loo), 4), "R3: max LOO r rounded to 4 dp", ("%.4f" % abs(max(loo))) == "0.9963")

# ---- 5) L152 analytic CR-bound column -------------------------------------
bound_cells = [("7.305", "(0.05,30)", 0.05, 30), ("6.333", "(0.1,10)", 0.1, 10),
               ("2.550", "(0.25,10)", 0.25, 10), ("1.009", "(1.0,5)", 1.0, 5),
               ("0.690", "(2.0,5)", 2.0, 5)]
for rep, lab, g, N in bound_cells:
    b = 1.0 / (g * math.sqrt(N * sig(g) * (1 - sig(g))))
    dp = len(rep.split(".")[1])
    exact = ("%.3f" % b) == ("%.3f" % float(rep))
    add(rep, "L152", "closed form 1/(gamma*sqrt(N*s*(1-s))) of Proposition 1 (no data dependency)",
        "cell %s" % lab, round(b, 6),
        "R3 if round==paper else R2 (1-ULP slack)",
        exact or abs(b - float(rep)) <= 1e-3,
        "recomputed=%.6f; delta=%.6f" % (b, abs(b - float(rep))))

add("0.953", "L152", "p2_sampling_theorem_sim_20260808.json (and closed form s(3.0))",
    "/gamma_grid[6].s", ss["gamma_grid"][6]["s"],
    "R3: round(artifact s=0.9526 to 3 dp) == 0.953; closed form s(3.0)=%.6f" % sig(3.0),
    round(ss["gamma_grid"][6]["s"], 3) == 0.953)

# ---- 6) L476/L484 version strings -----------------------------------------
with open(os.path.join(HERE, "requirements_source_project.txt"), encoding="utf-8") as f:
    req = f.read()
add("3.10", "L476, L484", "requirements_source_project.txt",
    "line 3 comment '# Python 3.10+'", "Python 3.10+",
    "R1 exact string", "Python 3.10+" in req,
    "constraint string, not a measurement")
add("4.40", "L476, L484", "requirements_source_project.txt (searched; absent)",
    "no transformers pin found", None, "R1", False,
    "UNBACKED: paper requires transformers>=4.40; project requirements.txt has no transformers entry; not a measurement")

# ---- 7) empirical CV / MLE / JSD / H(0): unbacked --------------------------
for v, ln, why in [
    ("6.794", "L152", "coverage-probe simulation (5000 runs/cell, logit estimator) script and output not archived; grep across /data3/Research/PAPER2_CONSOLIDATED (all text types) hits only main.tex/main_nb.tex and reports/ (which restate the paper)"),
    ("6.015", "L152", "same missing coverage-probe output"),
    ("2.422", "L152", "same missing coverage-probe output"),
    ("1.007", "L152", "same missing coverage-probe output"),
    ("0.426", "L152", "same missing coverage-probe output"),
    ("-3.37", "L152", "closed form logit(1/30)=%.4f reproduces the rendering, but the positive-coupling rate 1/30 itself has no archived carrier (mm_epc_multi_seed_ds_final.json absent)" % math.log((1 / 30) / (29 / 30))),
    ("-1.61", "L152", "closed form logit(5/30)=%.4f reproduces the rendering, but the rate 5/30 has no archived carrier" % math.log((5 / 30) / (25 / 30))),
    ("0.969", "L276", "per-seed gamma-JSD pair file gamma_jsd_correlation.json is referenced by experiments/T1_pinsker_fit.py line 79 but is not archived; no artifact contains 0.969/0.998/n=152"),
    ("0.9999", "L348", "convergence-dynamics simulation output (H(0)) not archived; protocol.md L263 only restates paper values (circular)"),
]:
    results.append({"paper_value": v, "paper_line": ln, "carrier": None,
                    "json_path_or_cell": None, "recomputed_or_found": None,
                    "rule": "n/a", "agrees": False, "note": "UNBACKED: " + why})

summary = {
    "dispatch": "b1w1-tmlr-paper2-consolidated-20260926T174617Z",
    "date": "2026-09-27",
    "flagged_total": 23,
    "backed": [r["paper_value"] for r in results if r["agrees"]],
    "unbacked": [r["paper_value"] for r in results if not r["agrees"]],
    "artifact_sha256": artifacts,
    "entries": results,
}
out = os.path.join(HERE, "b1_carrier_rederivation_20260927.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=1, ensure_ascii=False)
print("backed:", len(summary["backed"]), "unbacked:", len(summary["unbacked"]))
print("backed values:", summary["backed"])
print("unbacked values:", summary["unbacked"])
print("wrote", out)
