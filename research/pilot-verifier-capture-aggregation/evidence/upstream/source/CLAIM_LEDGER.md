# PAPER6 Claim Ledger (R16)

This ledger is the source of truth for every quantitative or causal claim. A
claim marked `inconclusive` may remain only with explicit hedging; `blocked`
claims must not appear in the manuscript.

| ID | Claim | Evidence | Values | Verification | Status |
|---|---|---|---|---|---|
| C01 | The benchmark contains four scenarios, seven aggregation methods, five seeds, and 1,000 rounds per cell. | `evidence/main_results/benchmark_table.json` -> `config.T / config.N / config.n_seeds` | 1000; 7; 5 | Recompute scenario/method counts and inspect per-seed arrays. | verified |
| C02 | Plain majority is the strongest or tied method in the four headline scenarios; trust variants do not provide a consistent gain. | `evidence/main_results/benchmark_table.json` -> `aggregate` | — | Recompute column-wise maxima and method gaps. | verified |
| C03 | The three attack families are prompt injection, rubric injection, and majority-bias mimicry. | `attacks.py`; `benchmark.py`; `evidence/main_results/per_attack_table.json` | — | Code-path and table cross-check. | verified |
| C04 | The synthetic pilot has 4,000 trials per cell for nine attack/accuracy cells and shows prompt-injection gains for trust weighting but not majority-bias gains. | `evidence/pilot_results/summary_v2.json` -> `["acc0.6\|prompt_injection"].n` | 4000 | Recompute each listed proportion from counts. | verified |
| C05 | A local real-model pilot contains 20 questions, four local models, three seeds, and two captured slots. | `evidence/real_llm_results/summary.json` -> `config.n_questions / config.n_seeds` | 20; 3 | Cross-check config against cell records. | verified |
| C06 | The local pilot gives identical rounded mean accuracy (0.9167) for all seven aggregation methods. | `evidence/real_llm_results/summary.json` -> `per_method.majority.mean` | 0.9167 | Recompute from `cells.json`; report as pilot-only and descriptive. | verified |
| C07 | The negative result is structural for all verifier ensembles or all real LLM distributions. | `protocol.md` | — | No supporting evidence is available; requires a formal theorem with complete assumptions or broad external validation. | blocked |
| C08 | Theorem 2 gives a valid \(\varepsilon\)-resilience guarantee for ATV. | `protocol.md` | — | The appendix retracts the proof; complete proof and independent verification are required. | blocked |
| C09 | Synthetic findings generalize to deployed real-LLM ensembles. | evidence/gaps/C09_generalization.md | not established | Requires preregistered held-out real-trace benchmark. | inconclusive |
| C10 | Hyperparameter and ensemble-size sweeps establish robustness. | `evidence/main_results/ensemble_sweep.json` | — | Recompute all sweep cells and report exact ranges; current manuscript summary is incomplete. | inconclusive |

## Strong-claim register

The manuscript may retain C01--C06 only within the stated synthetic or pilot
scope. C07--C08 are removed or explicitly marked as unresolved. C09--C10
require hedging and cannot support universal or deployment claims.
