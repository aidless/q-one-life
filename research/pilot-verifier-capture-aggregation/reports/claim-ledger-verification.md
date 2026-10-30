# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The synthetic benchmark contains four scenarios, seven aggregation met :: evidence/upstream/paper/evidence/main_results/benchmark_table.json -> config.T / config.N / config.f / config.n_seeds = [1000, 7, 2, 5]
- PASS C02: In S1--S3 majority is best or tied; in S4 trust-mean is 0.0076 higher  :: evidence/upstream/paper/evidence/main_results/benchmark_table.json -> aggregate[0]["mean"] / aggregate[3]["S4: high-honest, strong-attack"] = [0.6859, 0.8506]
- PASS C03: The three implemented attack families are prompt injection, rubric inj :: file evidence/upstream/source/source/attacks.py exists (non-JSON); file evidence/upstream/paper/evidence/main_results/per_attack_table.json ok (no field)
- PASS C04: The synthetic pilot contains 4,000 trials per cell and reports a promp :: evidence/upstream/paper/evidence/pilot_results/summary_v2.json -> ["acc0.6|prompt_injection"].n = [4000]
- PASS C05: The local Ollama pilot contains 20 questions, four models, three seeds :: evidence/upstream/paper/evidence/real_llm_results/summary.json -> config.n_questions / config.n_seeds = [20, 3]
- PASS C06: The local pilot reports 0.9167 mean accuracy for all seven aggregation :: evidence/upstream/paper/evidence/real_llm_results/summary.json -> per_method.majority.mean = [0.9167]
- PASS C07: The negative result is structural for all verifier ensembles or all re :: file evidence/upstream/source/source/evidence/protocol.md exists (non-JSON); BLOCKED status - keep out of manuscript
- PASS C08: An ATV epsilon-resilience guarantee is proved for the current benchmar :: file evidence/upstream/source/source/evidence/protocol.md exists (non-JSON); BLOCKED status - keep out of manuscript
- PASS C09: Synthetic findings generalize to deployed real-LLM ensembles. :: INCONCLUSIVE status - needs hedge wording in prose + named missing evidence (evidence not verified by design)
- PASS C10: The ensemble-size sweep reports N=5, N=7 and N=10 values; the values a :: evidence/upstream/paper/evidence/main_results/ensemble_sweep.json -> results.N5_f1 / results.N7_f2 / results.N10_f3 = [{'majority': 0.7479, 'bft_pbft': 0.7479, 'weighted_uniform': 0.7258, 'trust_mean': 0.7464, 'trust_median': 0.7479, 'kalman_trust': 0.7472, 'ATV': 0.747}, {'majority': 0.6859, 'bft_pbft': 0.6192, 'weighted_uniform': 0.5954, 'trust_mean': 0.6716, 'trust_median': 0.6863, 'kalman_trust': 0.6765, 'ATV': 0.6733}, {'majority': 0.6785, 'bft_pbft': 0.6026, 'weighted_uniform': 0.5771, 'trust_mean': 0.6602, 'trust_median': 0.7668, 'kalman_trust': 0.6552, 'ATV': 0.6593}]
- PASS C11: Hyperparameter sweeps establish robustness of the aggregation rankings :: file evidence/upstream/source/source/evidence/protocol.md exists (non-JSON); BLOCKED status - keep out of manuscript

## Summary: 11 PASS, 0 FAIL, 4 WARN

## Inconclusive entries (hedge + name missing evidence): 1

## Numeric literals in text without any ledger value: 101
+0.11, +0.35, +0.90, +16.93, +2.37, +2.74, +3.23, +5.03, +7.12, +8.97, -0.15, -2.14, -2.5, -3.79, -5.00, -5.14, -5.36, -8.24, 0.0, 0.0014, 0.007, 0.0076, 0.01, 0.05, 0.1, 0.2, 0.32, 0.34, 0.365, 0.4, 0.41, 0.432, 0.438, 0.446, 0.458, 0.459, 0.484, 0.5, 0.51, 0.521, 0.522, 0.527, 0.535, 0.553, 0.595, 0.6, 0.619, 0.65, 0.672, 0.673, 0.677, 0.6785, 0.686, 0.69, 0.7, 0.720, 0.729, 0.74, 0.7479, 0.765, 0.7668, 0.777, 0.8, 0.804, 0.842, 0.843, 0.8430, 0.844, 0.846, 0.85, 0.851, 0.876, 0.877, 0.882, 0.883, 0.886, 0.889, 0.894, 0.9, 0.916