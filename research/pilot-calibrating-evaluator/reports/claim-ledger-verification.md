# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The archived driver implements a binary TTRL arm and a confidence-weig :: file evidence/upstream/calibrated_ttrl.py exists (non-JSON)
- PASS C02: arXiv 2606.31371v1 is an existing public identity with the same title  :: evidence/source_record.json -> arxiv.total_results / arxiv.author_count / arxiv.title_matches_source = [1, 1, True]
- PASS C03: The local manuscript prints about 2,400 rounds and 3,600 evaluator cal :: evidence/p9-audit.json -> scale.printed_rounds / scale.printed_evaluator_calls = [2400, 3600]
- PASS C04: The archived driver realizes 1,200 rounds, 2,400 executor calls, and 1 :: evidence/p9-audit.json -> scale.realized_rounds / scale.realized_executor_calls / scale.realized_evaluator_calls = [1200, 2400, 1800]
- PASS C05: The printed 2,400-round and 3,600-evaluator-call scale is supported by :: evidence/p9-audit.json -> scale.rounds_shortfall / scale.evaluator_calls_shortfall = [1200, 1800]; BLOCKED status - keep out of manuscript
- PASS C06: Length-normalized and symmetric-learning-rate controls exist as indepe :: evidence/p9-audit.json -> controls.length_normalized.seed_level_output_present / controls.symmetric_lr.seed_level_output_present = [False, False]; BLOCKED status - keep out of manuscript
- PASS C07: The headline 20--49 percent gamma and 45--67 percent JSD ranges have a :: evidence/p9-audit.json -> result_archive.headline_percentage_carriers_present / result_archive.per_seed_records = [False, 0]; BLOCKED status - keep out of manuscript
- PASS C08: The archive the driver says it writes, experiments/calibrated_ttrl.jso :: evidence/p9-audit.json -> result_archive.expected_path / result_archive.present = ['experiments/calibrated_ttrl.json', False]
- PASS C09: The manuscript's DeepSeek-V4-Pro executor and GLM5.2 evaluator pair is :: evidence/p9-audit.json -> model_identity.identity_match / model_identity.driver_evaluator / model_identity.driver_executor = [False, 'gpt-4o', 'deepseek-chat']; BLOCKED status - keep out of manuscript
- PASS C10: The 31 percent uncertain-judgment fraction and mean-confidence values  :: evidence/p9-audit.json -> mechanism_statistics.raw_confidence_records_present = [False]; BLOCKED status - keep out of manuscript
- PASS C11: All 17 cited keys resolve to 17 unique embedded bibliography items, al :: evidence/p9-audit.json -> citations.bibitems / citations.unique_citation_keys = [17, 17]
- PASS C12: The current calibration-landscape merge target explicitly classifies P :: evidence/variant-reconciliation.json -> merge_target.current_source_marker_line / merge_target.current_source_marks_p9_protocol_deposit_only = [755, True]
- PASS C13: The expected b1de3c... parent snapshot can itself prove that the P9 me :: INCONCLUSIVE status - needs hedge wording in prose + named missing evidence (evidence not verified by design)
- PASS C14: P9 is dispositioned as merge/archive, with no independent candidate pa :: evidence/variant-reconciliation.json -> decision.disposition / decision.independent_package_created / decision.status = ['merge_archive', False, 'archived']

## Summary: 14 PASS, 0 FAIL, 6 WARN

## Inconclusive entries (hedge + name missing evidence): 1

## Numeric literals in text without any ledger value: 342
+0.000, +0.0003, +0.002, +0.003, +0.004, +0.008, +0.010, +0.012, +0.0131, +0.015, +0.018, +0.021, +0.022, +0.029, +0.041, +0.078, +0.079, +0.081, +0.082, +0.096, +0.127, +0.148, +0.170, +0.181, +0.205, +0.207, +0.208, +0.21, +0.225, +0.228, +0.234, +0.253, +0.286, +0.309, +0.7, +1.7, +10.8, +31.3, +4.4, +5.7, -0.003, -0.0038, -0.004, -0.0219, -0.0226, -0.04, -0.072, -0.086, -0.123, -0.169, -0.17, -0.177, -0.213, -0.245, -0.332, -0.6, -0.989, -1.2, -11.6, -13.7, -14.4, -14.8, -2.2, -3.5, -3.7, -35.4, -37.2, -6.5, -60.2, -63.4, -7.0, -8.7, 0.0, 0.000, 0.0001, 0.001, 0.002, 0.004, 0.006, 0.009