# PAPER35 Claim Ledger (R16)

| ID | Claim | Evidence | Values | Verification | Status |
|---|---|---|---|---|---|
| C01 | The canonical suite has 100 scenarios across six behavior categories. | `data/scenarios/canonical.jsonl`; `protocol.md` | 100 | Count scenario IDs and category labels. | verified |
| C02 | The main local run has four models, 100 scenarios, and three seeds (1,200 cells). | `experiments/full_run/_manifest.json` -> `scenarios_count / total_cells` | 100; 1200 | Reconcile job manifest and raw JSONL counts. | verified |
| C03 | Temperature-0 cross-seed BDS is low in the tested local models. | `experiments/full_run/analysis/full_run_analysis.json` | — | Recompute BDS from raw per-seed outputs. | verified |
| C04 | Cross-model BDS is larger than cross-seed BDS in the tested suite. | `experiments/full_run/analysis/full_run_stats_20260813.json` -> `q2_overall.mean / seed_vs_cross.mean_diff` | 7.1547; 7.1374 | Recompute paired per-scenario difference and CI. | verified |
| C05 | Heterogeneity varies by scenario category, with tool-use lower and multilingual higher in this run. | `experiments/full_run/analysis/full_run_analysis.json` | — | Recompute category means and bootstrap intervals. | verified |
| C06 | The reported Wilcoxon comparison is based on paired per-scenario differences. | `experiments/full_run/analysis/full_run_stats_20260813.json` -> `seed_vs_cross.n_paired` | 100 | Inspect test method and input pairing. | verified |
| C07 | BDS is a whitespace-token distribution metric, not a semantic distance. | `protocol.md`; `scripts/bds_evaluator.py` | — | Inspect tokenizer, smoothing, and estimator. | verified |
| C08 | Results generalize to frontier APIs, future snapshots, or temporal model drift. | `protocol.md` | — | Requires multi-snapshot/API replication; local run alone cannot establish this. | blocked |
| C09 | The 3-agent chain pilot demonstrates causal amplification of drift. | `experiments/multi_agent/analysis_repro_20260816.json` | — | Pilot is descriptive; requires controlled intervention and power. | inconclusive |
| C10 | Model families are interchangeable after controlling for scenario category. | `protocol.md` | — | Requires hierarchical model with prespecified family effects. | blocked |
| C11 | The regression suite predicts future deployment drift. | `protocol.md` | — | Requires prospective temporal validation; not present. | blocked |

## Strong-claim register

Only C01--C07 may support current manuscript conclusions, and only within the
four local checkpoints, fixed temperature, 100 scenarios, and recorded seeds.
C08--C11 must not be stated as established findings.
