# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The simulation artifact records 15 seeds, 30 rounds, K=3, alpha=1.0, a :: evidence/upstream/evidence/cg_tee_results.json -> config.n_seeds / config.n_rounds / config.k_tee / config.alpha / config.tau = [15, 30, 3, 1.0, 1.0]
- PASS C02: The three printed simulation gamma_TV means reproduce from the 15 per- :: evidence/native-audit.json -> simulation.standard.recomputed_mean / simulation.cg_alone.recomputed_mean / simulation.cg_tee.recomputed_mean = [0.1429878956260213, 0.7187781641976239, 0.5740180982911599]
- PASS C03: The aggregate file records CV values 0.192, 0.134, and 0.174. :: evidence/native-audit.json -> simulation.standard.recorded_cv / simulation.cg_alone.recorded_cv / simulation.cg_tee.recorded_cv = [0.19180676050901868, 0.1341812396040852, 0.1742851260509935]
- PASS C04: No tested per-seed CV definition reproduces the recorded CVs; the near :: evidence/native-audit.json -> simulation.standard.nearest_cv_gap / simulation.cg_alone.nearest_cv_gap / simulation.cg_tee.nearest_cv_gap = [0.02965283004045835, 0.016350905562969822, 0.028957000353120016]
- PASS C05: TEE reduces measurement noise or CV relative to standard TTRL in the a :: evidence/native-audit.json -> checks.simulation_cv_recompute = [False]; BLOCKED status - keep out of manuscript
- PASS C06: The real-API CG and CG+TEE arms are degenerate on all 15 seeds: gamma_ :: evidence/native-audit.json -> real_api.arms.cg_alone.gamma_tv_zero / real_api.arms.cg_tee.gamma_tv_zero / real_api.arms.cg_tee.entropy_t_one = [15, 15, 15]
- PASS C07: The archived real-API runner silently maps confidence-parse failures t :: evidence/run-script-identity.json -> facts.real_api_confidence_parse_fallback = [0.5]
- PASS C08: The N=15 result artifacts identify the executor/evaluator models or re :: evidence/native-audit.json -> real_api.model_identity_present = [False]; BLOCKED status - keep out of manuscript
- PASS C09: The separate final-results artifact records uncalibrated, calibrated,  :: evidence/native-audit.json -> final_results.means.uncalibrated / final_results.means.calibrated / final_results.means.cg_tee / final_results.uncalibrated_to_calibrated_reduction_pct = [0.9909266666666666, 0.602, 0.6438733333333333, 39.248783966522915]
- PASS C10: The 39.2 percent scalar is a CG or CG+TEE effect. :: evidence/native-audit.json -> final_results.uncalibrated_to_calibrated_reduction_pct / final_results.cg_tee_minus_calibrated = [39.248783966522915, 0.04187333333333332]; BLOCKED status - keep out of manuscript
- PASS C11: The fixed local smoke run covers 3 seeds and 10 rounds, records zero c :: evidence/upstream/paper/experiments/results/cg_tee_local_smoke.json -> config.n_seeds / config.rounds / parse_failures.confidence_parse_fail_rate = [3, 10, 0.0]
- PASS C12: All 26 cited keys resolve mechanically to 26 unique embedded bibliogra :: evidence/native-audit.json -> citations.bibitems / citations.unique_bibitems / citations.citation_keys = [26, 26, 26]
- PASS C13: All 11 archived numeric carrier receipts resolve to the named JSON loc :: evidence/native-audit.json -> carrier_audit.receipts / carrier_audit.passed / carrier_audit.failed = [11, 11, 0]
- PASS C14: The overlay compiles reproducibly in two isolated directories to a 10- :: reports/cleanroom/receipt.json -> pdf.pages / exit_codes[0] / exit_codes[1] = [10, 0, 0]
- PASS C15: The candidate package is ready for arXiv upload. :: reports/package/package-receipt.json -> ready_for_upload = [False]; BLOCKED status - keep out of manuscript
- PASS C16: Independent method and statistics review is closed against the current :: file evidence/upstream/paper/REVIEW_CARD.md exists (non-JSON); BLOCKED status - keep out of manuscript

## Summary: 16 PASS, 0 FAIL, 5 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 111
+0.0, +301.4, +402.7, +8.5, -0.11, -10.0, -13.4, -39.2, -433.4, 0.000, 0.016, 0.029, 0.030, 0.033, 0.0882, 0.0952, 0.1153, 0.1169, 0.1177, 0.127, 0.1303, 0.1317, 0.1361, 0.14, 0.1547, 0.157, 0.159, 0.1614, 0.165, 0.1722, 0.1729, 0.177, 0.1791, 0.1861, 0.1870, 0.2, 0.3, 0.3358, 0.3375, 0.42, 0.4717, 0.4742, 0.511, 0.5269, 0.5306, 0.5313, 0.5482, 0.553, 0.5858, 0.5867, 0.595, 0.6127, 0.6178, 0.621, 0.627, 0.6281, 0.6335, 0.634, 0.6516, 0.653, 0.6625, 0.663, 0.678, 0.691, 0.6928, 0.699, 0.7015, 0.7131, 0.7199, 0.72, 0.7209, 0.7232, 0.7236, 0.744, 0.7554, 0.758, 0.7588, 0.772, 0.7738, 0.7817