# Paper 6 evidence-qualified claim ledger

Canonical upstream: `evidence/upstream/paper/main.tex`

Canonical SHA-256: `42fe9b13f6a17af326f346aaa1afb7228fa1e8f4478126fadbce0fc7cea80cc3`

Overlay source: `source/main.tex`

Overlay SHA-256 is checked by `project.json`; the upstream bytes remain
unchanged. The upstream ledger contains several universal claims and a
theorem that are not supported by the frozen evidence. This ledger preserves
those unresolved claims as blocked or inconclusive and records the exact
benchmark facts that can be replayed.

| ID | Claim | Evidence file and field | Values | Verification | Status |
|---|---|---|---|---|---|
| C01 | The synthetic benchmark contains four scenarios, seven aggregation methods, five seeds, and 1,000 rounds per cell. | `evidence/upstream/paper/evidence/main_results/benchmark_table.json` -> config.T / config.N / config.f / config.n_seeds | 1000 / 7 / 2 / 5 | Recompute config and per-seed row counts. | verified |
| C02 | In S1--S3 majority is best or tied; in S4 trust-mean is 0.0076 higher than majority, so majority is not best in every scenario. | `evidence/upstream/paper/evidence/main_results/benchmark_table.json` -> aggregate[0]["mean"] / aggregate[3]["S4: high-honest, strong-attack"] | 0.6859 / 0.8506 | Recompute every aggregate cell from per-seed records and inspect column maxima. | verified |
| C03 | The three implemented attack families are prompt injection, rubric injection, and majority-bias mimicry. | `evidence/upstream/source/source/attacks.py`; `evidence/upstream/paper/evidence/main_results/per_attack_table.json` | 3 | Cross-check the attack registry and three table families. | verified |
| C04 | The synthetic pilot contains 4,000 trials per cell and reports a prompt-injection gain for trust weighting but not a majority-bias gain. | `evidence/upstream/paper/evidence/pilot_results/summary_v2.json` -> ["acc0.6\|prompt_injection"].n | 4000 | Resolve the named pilot cell and compare its method values. | verified |
| C05 | The local Ollama pilot contains 20 questions, four models, three seeds, and two captured slots. | `evidence/upstream/paper/evidence/real_llm_results/summary.json` -> config.n_questions / config.n_seeds | 20 / 3 | Cross-check the config against the three cells. | verified |
| C06 | The local pilot reports 0.9167 mean accuracy for all seven aggregation methods and is only a descriptive pilot. | `evidence/upstream/paper/evidence/real_llm_results/summary.json` -> per_method.majority.mean | 0.9167 | Recompute all methods from the three cell records; do not treat as a generalization test. | verified |
| C07 | The negative result is structural for all verifier ensembles or all real LLM distributions. | `evidence/upstream/source/source/evidence/protocol.md` | missing | No universal evidence or complete theorem is present. | blocked |
| C08 | An ATV epsilon-resilience guarantee is proved for the current benchmark. | `evidence/upstream/source/source/evidence/protocol.md` | missing | The upstream appendix omits the proof and the benchmark does not establish the guarantee. | blocked |
| C09 | Synthetic findings generalize to deployed real-LLM ensembles. | `evidence/upstream/source/source/evidence/gaps/C09_generalization.md` | not established | Requires a held-out real-trace benchmark. | inconclusive |
| C10 | The ensemble-size sweep reports N=5, N=7 and N=10 values; the values are descriptive rather than a monotone robustness result. | `evidence/upstream/paper/evidence/main_results/ensemble_sweep.json` -> results.N5_f1 / results.N7_f2 / results.N10_f3 | 3 | Compare the three sweep cells and report the N=10 trust-median gain without claiming a trend. | verified |
| C11 | Hyperparameter sweeps establish robustness of the aggregation rankings. | `evidence/upstream/source/source/evidence/protocol.md` | missing | The frozen evidence has no per-cell tau or alpha sweep files. | blocked |

`verified` means the named frozen field or code path resolves and the stated
scope is recomputable. `inconclusive` means the claim is held with a named
missing test. `blocked` means the claim must not be presented as established.

The native C02 assertion that majority is strongest in all four headline
scenarios is not reproduced: S4 favors trust-mean. The native C07/C08/C11
assertions are not promoted.
