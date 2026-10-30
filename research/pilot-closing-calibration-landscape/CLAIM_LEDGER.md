# Claim ledger - Closing the Calibration Landscape

Status marker: `agent-proposed, not human publication approval`

| ID | Claim | Evidence file + fields | Value | How to verify | Status |
|---|---|---|---|---|---|
| C01 | The simulation artifact records 15 seeds, 30 rounds, K=3, alpha=1.0, and tau=1.0. | evidence/upstream/evidence/cg_tee_results.json -> config.n_seeds / config.n_rounds / config.k_tee / config.alpha / config.tau | 15 / 30 / 3 / 1.0 / 1.0 | Read the aggregate configuration and recompute from the checkpoint | verified |
| C02 | The three printed simulation gamma_TV means reproduce from the 15 per-seed checkpoint values. | evidence/native-audit.json -> simulation.standard.recomputed_mean / simulation.cg_alone.recomputed_mean / simulation.cg_tee.recomputed_mean | 0.143 / 0.719 / 0.574 | Run `tools/audit_cg_tee.py` and compare each recomputed mean with its recorded value | verified |
| C03 | The aggregate file records CV values 0.192, 0.134, and 0.174. | evidence/native-audit.json -> simulation.standard.recorded_cv / simulation.cg_alone.recorded_cv / simulation.cg_tee.recorded_cv | 0.192 / 0.134 / 0.174 | Inspect the aggregate artifact and the audit extraction | verified |
| C04 | No tested per-seed CV definition reproduces the recorded CVs; the nearest gaps are 0.0297, 0.0164, and 0.0290. | evidence/native-audit.json -> simulation.standard.nearest_cv_gap / simulation.cg_alone.nearest_cv_gap / simulation.cg_tee.nearest_cv_gap | 0.0297 / 0.0164 / 0.0290 | Recompute sample/population CV and standard-deviation candidates from the checkpoint | verified |
| C05 | TEE reduces measurement noise or CV relative to standard TTRL in the archived experiment. | evidence/native-audit.json -> checks.simulation_cv_recompute | false | A lower recorded CV is insufficient; the CV must be recomputable from seed-level records | blocked |
| C06 | The real-API CG and CG+TEE arms are degenerate on all 15 seeds: gamma_TV=0, gamma_VT=0, H_T=1, and H_V=1. | evidence/native-audit.json -> real_api.arms.cg_alone.gamma_tv_zero / real_api.arms.cg_tee.gamma_tv_zero / real_api.arms.cg_tee.entropy_t_one | 15 / 15 / 15 | Count the exact degenerate tuple across all completed seeds | verified |
| C07 | The archived real-API runner silently maps confidence-parse failures to 0.5, which yields a zero additive update. | evidence/run-script-identity.json -> facts.real_api_confidence_parse_fallback | 0.5 | Inspect the sanitized parser provenance record and the pinned runner hash | verified |
| C08 | The N=15 result artifacts identify the executor/evaluator models or record parser success. | evidence/native-audit.json -> real_api.model_identity_present | false | Search every N=15 JSON for endpoint, model, and parser fields | blocked |
| C09 | The separate final-results artifact records uncalibrated, calibrated, and CG+TEE gamma_TV means of 0.991, 0.602, and 0.644; its uncalibrated-to-calibrated reduction is 39.249 percent. | evidence/native-audit.json -> final_results.means.uncalibrated / final_results.means.calibrated / final_results.means.cg_tee / final_results.uncalibrated_to_calibrated_reduction_pct | 0.991 / 0.602 / 0.644 / 39.249 | Recompute means from the three arrays in `cg_tee_final_results.json` | verified |
| C10 | The 39.2 percent scalar is a CG or CG+TEE effect. | evidence/native-audit.json -> final_results.uncalibrated_to_calibrated_reduction_pct / final_results.cg_tee_minus_calibrated | 39.249 / 0.0419 | Compare the source of 39.249 with the CG+TEE-versus-calibrated difference | blocked |
| C11 | The fixed local smoke run covers 3 seeds and 10 rounds, records zero confidence parse failures, and is non-degenerate. | evidence/upstream/paper/experiments/results/cg_tee_local_smoke.json -> config.n_seeds / config.rounds / parse_failures.confidence_parse_fail_rate | 3 / 10 / 0.0 | Read the smoke receipt and keep it descriptive, not confirmatory | verified |
| C12 | All 26 cited keys resolve mechanically to 26 unique embedded bibliography items. | evidence/native-audit.json -> citations.bibitems / citations.unique_bibitems / citations.citation_keys | 26 / 26 / 26 | Re-parse every `\cite` and `\bibitem` key in the overlay manuscript | verified |
| C13 | All 11 archived numeric carrier receipts resolve to the named JSON locator and matching printed manuscript token. | evidence/native-audit.json -> carrier_audit.receipts / carrier_audit.passed / carrier_audit.failed | 11 / 11 / 0 | Re-execute each receipt against the retained artifacts and canonical line | verified |
| C14 | The overlay compiles reproducibly in two isolated directories to a 10-page PDF. | reports/cleanroom/receipt.json -> pdf.pages / exit_codes[0] / exit_codes[1] | 10 / 0 / 0 | Re-run `scripts/cleanroom_compile.py` on the pinned source tree | verified |
| C15 | The candidate package is ready for arXiv upload. | reports/package/package-receipt.json -> ready_for_upload | false | Check the package blockers and the user metadata/authorization gate | blocked |
| C16 | Independent method and statistics review is closed against the current overlay hash. | evidence/upstream/paper/REVIEW_CARD.md | open | Require a reviewer receipt bound to `ada8019e...` and zero unresolved Critical or Major findings | blocked |

## Summary

The archive supports arithmetic recomputation of the simulation gamma means,
the degeneracy diagnosis, the separate final-results scalar, the citation parse,
the carrier transcription, and the deterministic compile. It does not support a
TEE noise or bias conclusion, the attribution of 39.2 percent to CG/TEE, a TEE
null result, arXiv readiness, or independent review closure.
