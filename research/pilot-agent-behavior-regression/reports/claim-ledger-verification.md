# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The canonical suite contains 100 scenarios across six behavior categor :: evidence/native-audit.json -> counts.scenarios / counts.category_counts = [100, {'A': 20, 'L': 20, 'M': 20, 'R': 15, 'T': 10, 'X': 15}]
- PASS C02: The frozen full-run manifest declares four models, 100 scenarios and t :: evidence/upstream/paper/experiments/full_run/_manifest.json -> scenarios_count / total_cells = [100, 1200]
- PASS C03: The frozen aggregate output reports near-zero cross-seed BDS for qwen2 :: evidence/upstream/paper/experiments/full_run/analysis/full_run_analysis.json -> q1_seed_reproducibility.qwen2_7b.mean_bds = [0.029507500928217904]
- PASS C04: The frozen output reports cross-model BDS 7.1547 and a cross-model min :: evidence/upstream/paper/experiments/full_run/analysis/full_run_stats_20260813.json -> q2_overall.mean / seed_vs_cross.mean_diff = [7.1547, 7.1374]
- PASS C05: The frozen output reports tool-use as the lowest category mean and mul :: evidence/upstream/paper/experiments/full_run/analysis/full_run_analysis.json -> q2_cross_model.by_category.T.mean_bds / q2_cross_model.by_category.X.mean_bds = [4.476091700350247, 9.419422386271638]
- PASS C06: The reported Wilcoxon comparison uses 100 paired per-scenario differen :: evidence/upstream/paper/experiments/full_run/analysis/full_run_stats_20260813.json -> seed_vs_cross.n_paired = [100]
- PASS C07: BDS is defined as a whitespace-token distribution proxy and is not cla :: file evidence/upstream/paper/scripts/bds_evaluator.py exists (non-JSON); evidence/native-audit.json -> checks.formal_consistency_claim_removed = [True]
- PASS C08: The results generalize to frontier APIs, future snapshots or temporal  :: file evidence/upstream/paper/protocol.md exists (non-JSON); evidence/native-audit.json -> checks.full_run_raw_present = [False]; BLOCKED status - keep out of manuscript
- PASS C09: The three-agent chain pilot demonstrates causal amplification of drift :: INCONCLUSIVE status - needs hedge wording in prose + named missing evidence (evidence not verified by design)
- PASS C10: Model families are interchangeable after controlling for scenario cate :: file evidence/upstream/paper/protocol.md exists (non-JSON); BLOCKED status - keep out of manuscript
- PASS C11: The regression suite predicts future deployment drift. :: file evidence/upstream/paper/protocol.md exists (non-JSON); BLOCKED status - keep out of manuscript

## Summary: 11 PASS, 0 FAIL, 4 WARN

## Inconclusive entries (hedge + name missing evidence): 1

## Numeric literals in text without any ledger value: 105
0.0, 0.0000, 0.0008939817893, 0.00272, 0.002822166505, 0.003, 0.0033, 0.017, 0.0173, 0.0175, 0.01752992645, 0.02215079784, 0.0222, 0.02950750093, 0.03, 0.030, 0.05, 0.08648528152, 0.0865, 0.1, 0.12, 0.1215977828, 0.15, 0.153219446, 0.3, 0.40, 0.4047186569, 0.5676765873, 0.57, 0.7, 0.7149670957, 0.85, 0.92, 1.096457513, 1.1, 1.10, 1.2, 1.20, 1.3, 1.4, 1.468091444, 1.6599, 1.7, 1.75, 1.752144883, 10.39, 11.39, 11.4, 127.0, 13.5, 13.6, 2.0, 2.5, 2.57, 20.7, 3.1, 3.10, 3.3, 3.5, 3.54, 3.9, 4.4, 4.40, 4.4760917, 4.48, 5.38, 5.3848, 5.4, 5.63, 6.2757, 6.28, 6.39, 6.4, 6.6, 6.73, 6.7331, 6.733149662, 6.74, 6.7422, 6.7963