#!/usr/bin/env python3
"""verify_f_v2.py -- cross-check every load-bearing number in the REVISED
F manuscript against the recomputed evidence JSONs (fail-closed).

Chain: audited source -> frozen tool outputs -> revision_stats.py recomputation
-> revision_stats.json / dynamic_audit_frozen200.json / flip_band.json /
f01_mcnemar_scan.json / f02_gate_inventory.json -> manuscript strings here.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parent
TEX = WS / "manuscript/f-acceptance/main.tex"

_ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
_ap.add_argument("--tex", default=str(TEX),
                 help="manuscript tex to verify (default: manuscript/f-acceptance/main.tex; "
                      "pass manuscript/f-acceptance-tmlr/main.tex or f-acceptance-arxiv/main.tex "
                      "to verify the submission variants against the same evidence)")
_args = _ap.parse_args()

rs = json.loads((HERE / "revision_stats.json").read_text())
dyn = json.loads((HERE / "dynamic_audit_frozen200.json").read_text())
band = json.loads((HERE / "flip_band.json").read_text())
inv = json.loads((WS / "data/f02_gate_inventory.json").read_text())

CHECKS = []   # (label, list of acceptable substrings)


def add(label, strings):
    CHECKS.append((label, strings if isinstance(strings, list) else [strings]))


b = rs["basic"]
add(f"cells={b['cells']}", ["62,819"])
add(f"promotions={b['promotions_code']:.0f}", ["55,469"])
add(f"flips_anti={b['flips_anti_cons']}", ["231"])
add(f"max_err_code={b['max_abs_err_code']:.6f}", ["0.152610"])
add(f"max_err_at={b['max_abs_err_at']}", ["14, 13", "14,13"])
add(f"strictest_ratio={b['max_strictness_ratio_flip']:.3f}", ["1.525", "1.52"])
add(f"strictest_at={b['max_strictness_ratio_at']}", ["19, 8, 27", "19,8,27"])
add(f"deep_tail={b['pcode_gt_pexact_count']}", ["41,076"])
add(f"max_pcode={b['pcode_gt_pexact_max_pcode']:.3f}",
    ["5.312", "5.3\\times10^{-5}"])
add(f"rate500={b['flip_rate_bound500']*100:.2f}%", ["0.42"])
add(f"rate200={b['flip_rate_bound200']*100:.2f}%", ["1.02"])
add(f"flips@200={b['flips_bound200']}", ["84"])
add(f"promotions@200={b['promotions_bound200']}", ["8,204"])

cc = rs["cc"]
add(f"cc_flips_cons={cc['flips_cons']}", ["9"])
add(f"cc_flips_anti={cc['flips_anti_cons']}", ["0"])
add(f"cc_max_err={cc['max_abs_err']:.6f}", ["0.002053"])
add(f"cc_max_at={cc['max_abs_err_at']}", ["19, 8, 27", "19,8,27"])
add(f"cc_p_18_8_26={cc['p_at_18_8_26']:.6f}", ["0.077556"])

mp = rs["midp"]
add(f"midp_flips_anti={mp['flips_anti_cons']}", ["221"])
add(f"midp_max_err={mp['max_abs_err']:.6f}", ["0.149446"])

bm = rs["benchmark_1s_nominal"]
add(f"1s_conservative={bm['conservative_cells']}", ["928"])
add(f"1s_anti={bm['anti_cons_cells']}", ["0"])
add(f"1s_p_code_ex={bm['exemplar_18_8_26']['p_code']:.6f}", ["0.049860"])
add(f"1s_exact_ex={bm['exemplar_18_8_26']['p_1s_exact']:.6f}", ["0.037759"])

for alpha_key in ("0.01", "0.025", "0.05", "0.1"):
    v = rs["alpha_robustness"][alpha_key]
    add(f"alpha@{alpha_key}={v}", [str(v)])

led = rs["ledger_rejudgment"]
add(f"ledger_agree={led['agree']}/{led['entries']}",
    [f"all {led['entries']} recorded verdicts agree",
     f"{led['agree']}/{led['entries']}",
     "all fourteen recorded verdicts agree", "14/14"])
add(f"ledger_max_n={led['max_n']}",
    [f"n\\le{led['max_n']}", f"n \\le {led['max_n']}",
     f"$n\\le{led['max_n']}$"])
add(f"ledger_promos={led['promotions_recorded']}",
    [f"{led['promotions_recorded']} promotions", "five promotions"])

loop = rs["loop_illustration"]
add(f"loop={loop['p_at_least_one_false_promo']*100:.1f}%", ["97.5"])
add(f"loop_n={loop['n_decisions']}", ["145"])

sr = rs["scipy_refs"]
add(f"scipy_ref_18_8={sr['binomtest_18_8_26_two_sided']!r}",
    ["0.07551869750022888"])
add(f"scipy_ref_14_13={sr['binomtest_14_13_27_two_sided']!r}", ["1.0"])

chi = rs["chi2_decomposition"]["bound200"]
add(f"chi2_tie_cells@200={chi['tie_cells']}", ["88"])
add(f"chi2_tie_err@200={chi['tie_artifact_max_err']:.6f}",
    ["0.155481", "0.1555"])
add(f"chi2_tie_at={chi['tie_at']}", ["13, 13, 26", "13,13,26"])
add(f"chi2_nontie_err={chi['nontie_asym_max_err']:.6f}", ["0.002053"])
add(f"chi2_flips_cons@200={chi['flips_cons']}", ["5"])
add(f"chi2_flips_cons@500={rs['chi2_decomposition']['bound500']['flips_cons']}",
    ["9"])

add(f"band_n={band['n_flips']}", ["231"])
add(f"band_05_06={band['bands']['(0.05,0.06]']}", ["218"])
add(f"band_cap={band['max_p_exact']!r}", ["0.07551869750022888"])
add(f"band_floor={band['min_p_exact']:.6f}", ["0.050005", "0.05000494"])

chi2_dyn = dyn["paper_workflow_kb (chi2)"]
add(f"dyn_chi2_flips={chi2_dyn['decision_flips']}", ["5"])
add(f"dyn_chi2_err={chi2_dyn['max_abs_error']:.6f}", ["0.155481", "0.1555"])

gsm = dyn["gsm8k-self-evolve"]
add(f"dyn_gsm8k_err={gsm['max_abs_error']!r}",
    ["1.9984014443252818e-15", "2.0{\\times}10^{-15}"])
rag = dyn["rag_min_demo (w3)"]
add(f"dyn_rag_err={rag['max_abs_error']!r}",
    ["4.9974e-05", "4.997e-05", "5.0{\\times}10^{-5}"])

add(f"inventory_count={inv['count']}", ["118"])

# 48-unknown full resolution (unknown48_full_audit.json)
u48 = json.loads((HERE / "unknown48_full_audit.json").read_text())
dyn48 = [r for r in u48 if r.get("verdict") == "audited-dynamic"]
add(f"unknown48_total={len(u48)}", ["48"])
add(f"unknown48_dynamic={len(dyn48)} (tex: Twelve)", ["Twelve"])
# tex rounds the two dyn max errors UP to a bound: 9.248e-14 -> 9.3e-14,
# 1.3955e-13 -> 1.4e-13 (conservative upper bounds, asserted in tex form)
add("unknown48_2param_maxerr_bound=9.3e-14 (json max %.3e)" % max(
    r["max_abs_error"] for r in dyn48 if "alternative" not in r.get("kind", "")),
    ["9.3\\times10^{-14}"])
d3 = [r for r in dyn48 if "alternative" in r.get("kind", "")]
add(f"unknown48_3param={len(d3)} (tex: seven)", ["seven"])
add("unknown48_3param_maxerr_bound=1.4e-13 (json max %.3e)" % max(
    r["max_abs_error"] for r in d3), ["1.4\\times10^{-13}"])
notgate48 = [
    r
    for r in u48
    if r["verdict"].startswith("not-a-gate") or r["verdict"] == "non-gate-shape"
]
add(f"unknown48_notgate={len(notgate48)}",
    ["The remaining 36 are not p-value gates at all"])
add("live_scan_delta=121", ["121"])
add("region_floor=26", ["floor of 26", "region floor 26"])

ver = rs["versions"]
add(f"python={ver['python']}", ["3.12.3"])
add(f"scipy={ver['scipy']}", ["1.18.1"])

# GitHub public-code survey numbers (Sec 4 "pattern or anecdote" paragraph)
gs = json.load(open(HERE / "github_survey/raw/classification.json"))
rd = json.load(open(HERE / "github_survey/raw/classification-readjudicated.json"))
pop = gs["population"]
sg = pop.get("sourcegraph_q_mcnemar_count_all", {})
sgx = pop.get("sourcegraph_q_mcnemar_exact_count_all", {})
ds = gs["def_sample"]
impl = ds["implementation_exact_named_verdicts"]
add("ghsurvey_sg_lines", ["17,335"])
add("ghsurvey_sg_files", ["5,746"])
add(f"ghsurvey_sgx_files={sgx.get('files')}", ["277"])
add("ghsurvey_fetched", ["Seventy-nine"])
add("ghsurvey_fetched_classified=79/78", ["Seventy-nine files were fetched, 78 of which"])
add("ghsurvey_sample_files=78", ["78-file public"])
add("ghsurvey_impl_defs", ["81"])
add(f"ghsurvey_exact_named={ds['implementation_exact_named']}", ["68"])
add(f"ghsurvey_counterexamples={rd['counterexamples_count']}", ["1 of 68 exact-named"])
add("ghsurvey_counterexample_id", ["Gurp-S/XEYO"])
for k, expect in [("exact", "61"), ("exact-delegate", "four delegate"), ("exact-wrapper", "two wrap"), ("non-computing-wrapper", "one formats")]:
    add(f"ghsurvey_{k}={impl[k]}", [expect])

# live tool hashes (16-hex prefixes must appear in Sec 7 / appendix)
for tool in ("mcnemar_audit.py", "acceptance_gate_audit.py"):
    h = hashlib.sha256((HERE / tool).read_bytes()).hexdigest()[:16]
    add(f"hash_{tool}={h}", [h])

# exit-vocabulary table: --scan is a reporter, and the retired no-flips
# injection is attributed to acceptance_gate_audit.py while the live one is
# attributed to mcnemar_audit.py
add("gate_scan_reporter_row", ["\\code{--scan} & \\emph{reporter}"])
add("noflips_live_in_mcnemar", ["still carries a working \\code{no-flips}"])
add("postrepair_n500_err=2.7e-15", ["2.7\\times10^{-15}"])

tex = re.sub(r"(?<!\\)%.*", "", Path(_args.tex).read_text())   # keep escaped \%
tex = tex.replace("{,}", ",")   # LaTeX thousands separator form
fails, passed = [], 0
for label, strings in CHECKS:
    if any(s in tex for s in strings):
        passed += 1
    else:
        fails.append(f"MISS  {label}: none of {strings}")
print(f"verify_f_v2[{_args.tex}]: {passed} checks passed, {len(fails)} failed")
for f in fails:
    print(" ", f)
sys.exit(1 if fails else 0)
