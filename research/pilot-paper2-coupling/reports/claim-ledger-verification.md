# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: Six standalone theory TeX files and six experiment JSON outputs encode :: evidence/native-audit.json -> counts.theory_tex_files / counts.experiment_json_files / counts.native_claims = [6, 6, 14]
- PASS C02: The favorable-region emptiness is descriptive of the 11-condition reco :: evidence/native-audit.json -> counts.scope_heldout_mentions / counts.heldout_data_files = [9, 0]
- PASS C03: The reported tight-bound improvement is sample-descriptive rather than :: file evidence/upstream/source/evidence/scope_P2C3.md exists (non-JSON); evidence/native-audit.json -> checks.heldout_data_file_present = [False]
- PASS C04: The Pinsker analysis is outside its small-gamma regime for the observe :: evidence/upstream/source/experiments/T1_pinsker_fit.json -> n_in_small_gamma_regime / n_conditions = [0, 11]
- PASS C05: The logistic Cramer-Rao bound is not automatically equivalent to the m :: file evidence/upstream/source/evidence/scope_P2C5.md exists (non-JSON); evidence/upstream/source/experiments/T2_multiparameter.json -> n_gamma_obs = [65]
- PASS C06: The product-bound inequality is only available after replacing the ori :: file evidence/upstream/source/evidence/scope_P2C6.md exists (non-JSON); file evidence/upstream/source/theory/T5_minimax.tex exists (non-JSON)
- PASS C07: T5 and T8 report consistent outputs, while T6 reports an empirical bou :: evidence/upstream/source/experiments/T6_ensemble_K4.json -> empirical_gamma_H_CV_K4 / bound_at_K4_delta_0.05 = [0.063247, 0.384555]
- PASS C08: The four-axis polytope remains descriptive; the native scope text and  :: file evidence/upstream/source/evidence/scope_P2C8.md exists (non-JSON); evidence/upstream/source/experiments/T7_polytope.json -> n_all_constraints_satisfied / n_cells_tested = [0, 20]
- PASS C09: CV values at different N and estimator definitions are not pooled into :: file evidence/upstream/source/evidence/scope_P2C9.md exists (non-JSON); evidence/upstream/source/experiments/T2_multiparameter.json -> N_samples = [30]
- PASS C10: Standard psychometric baselines such as kappa, ICC and Rasch are outsi :: file evidence/upstream/source/evidence/scope_P2C10.md exists (non-JSON)
- PASS C11: GPT-4o drift is not robust at N=8, and the native p=0.12 statement con :: file evidence/upstream/source/evidence/scope_P2C11.md exists (non-JSON); evidence/upstream/source/evidence/analyses/gpt4o_drift_june_snapshot.json -> n_seeds = [8]; evidence/upstream/source/evidence/analyses/mm_epc_gpt4o_replication.json -> p_bootstrap = [1.0]; BLOCKED status - keep out of manuscript
- PASS C12: All eleven condition rows are represented in the decision-case table a :: evidence/native-audit.json -> counts.bound_decision_rows / counts.table_numbers = [11, 66]
- PASS C13: The current reproducibility bundle is incomplete because it lacks held :: evidence/native-audit.json -> counts.carrier_receipts_passed / counts.heldout_data_files / counts.proof_audit_receipts = [176, 0, 0]
- PASS C14: Adversarial review is not closed: the frozen review summary still reco :: evidence/upstream/source/review_real/summary.json -> r6.major / r6.critical = [5, 0]; evidence/native-audit.json -> checks.meta_review_reports_major_revisions = [True]; BLOCKED status - keep out of manuscript

## Summary: 14 PASS, 0 FAIL, 2 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 247
+0.36, +11.2, -0.03, -0.075, -0.49, -0.699, -0.78, -0.787, -0.8, -0.85, -0.852, -0.868, -0.895, -0.95, -0.969, -0.989, -0.9963, -0.9977, -0.9997, -1.0, -1.176, -1.61, -3.37, -3.5, -3.7, -5.2, 0.0, 0.000, 0.0001, 0.00034, 0.001, 0.0014, 0.002, 0.0022, 0.003, 0.0039, 0.004, 0.0043, 0.005, 0.0075, 0.01, 0.012, 0.0128, 0.013, 0.02, 0.025, 0.03, 0.033, 0.0332, 0.04, 0.05, 0.06, 0.066, 0.075, 0.08, 0.080, 0.0880, 0.0909, 0.0979, 0.098, 0.1, 0.113, 0.12, 0.13, 0.14, 0.143, 0.145, 0.148, 0.15, 0.157, 0.158, 0.16, 0.167, 0.176, 0.18, 0.180, 0.184, 0.186, 0.1865, 0.187