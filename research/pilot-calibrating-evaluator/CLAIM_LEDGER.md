# Claim ledger - Calibrating the Evaluator

Status marker: `agent-proposed, not human publication approval`

| ID | Claim | Evidence file + fields | Value | How to verify | Status |
|---|---|---|---|---|---|
| C01 | The archived driver implements a binary TTRL arm and a confidence-weighted calibrated arm; the so-called calibration step is a mean over the latest ten confidence values, not full isotonic calibration. | evidence/upstream/calibrated_ttrl.py | binary; mean-window | Inspect `train_standard`, `train_calibrated`, and `gpt4o_confidence` | verified |
| C02 | arXiv `2606.31371v1` is an existing public identity with the same title and one listed author, Zewen Liu. | evidence/source_record.json -> arxiv.total_results / arxiv.author_count / arxiv.title_matches_source | 1 / 1 / true | Re-query the arXiv API and compare title, version, authors, and response SHA-256 | verified |
| C03 | The local manuscript prints about 2,400 rounds and 3,600 evaluator calls. | evidence/p9-audit.json -> scale.printed_rounds / scale.printed_evaluator_calls | 2400 / 3600 | Inspect the current manuscript scale paragraph and table provenance | verified |
| C04 | The archived driver realizes 1,200 rounds, 2,400 executor calls, and 1,800 evaluator calls. | evidence/p9-audit.json -> scale.realized_rounds / scale.realized_executor_calls / scale.realized_evaluator_calls | 1200 / 2400 / 1800 | Recompute from the four-phase loop and evaluator call sites in the driver | verified |
| C05 | The printed 2,400-round and 3,600-evaluator-call scale is supported by the archived driver. | evidence/p9-audit.json -> scale.rounds_shortfall / scale.evaluator_calls_shortfall | 1200 / 1800 | Recompute the scale from the driver; a nonzero shortfall contradicts the claim | blocked |
| C06 | Length-normalized and symmetric-learning-rate controls exist as independent seed-level experiments. | evidence/p9-audit.json -> controls.length_normalized.seed_level_output_present / controls.symmetric_lr.seed_level_output_present | false / false | Require two independent control archives with seed-level records and preregistered summaries | blocked |
| C07 | The headline 20--49 percent gamma and 45--67 percent JSD ranges have a per-seed carrier in the delivered package. | evidence/p9-audit.json -> result_archive.headline_percentage_carriers_present / result_archive.per_seed_records | false / 0 | Recompute the ranges from immutable per-seed gamma and JSD outputs | blocked |
| C08 | The archive the driver says it writes, `experiments/calibrated_ttrl.json`, is absent from the delivered P9 package. | evidence/p9-audit.json -> result_archive.expected_path / result_archive.present | experiments/calibrated_ttrl.json / false | Search the package and verify no substitute N=5 P9 record is present | verified |
| C09 | The manuscript's DeepSeek-V4-Pro executor and GLM5.2 evaluator pair is recoverable from the archived driver. | evidence/p9-audit.json -> model_identity.identity_match / model_identity.driver_evaluator / model_identity.driver_executor | false / gpt-4o / deepseek-chat | Compare the manuscript model names with executable model IDs and endpoint | blocked |
| C10 | The 31 percent uncertain-judgment fraction and mean-confidence values have raw confidence records in the delivered package. | evidence/p9-audit.json -> mechanism_statistics.raw_confidence_records_present | false | Recompute the mechanism statistics from immutable confidence records | blocked |
| C11 | All 17 cited keys resolve to 17 unique embedded bibliography items, although semantic support is not established by this count. | evidence/p9-audit.json -> citations.bibitems / citations.unique_citation_keys | 17 / 17 | Parse every `\cite` key and every `\bibitem` key; separately audit claim-to-citation semantics | verified |
| C12 | The current calibration-landscape merge target explicitly classifies P9 as an Appendix B protocol deposit, not as an independent result. | evidence/variant-reconciliation.json -> merge_target.current_source_marker_line / merge_target.current_source_marks_p9_protocol_deposit_only | 755 / true | Inspect the pinned merge-target copy at marker line 755 | verified |
| C13 | The expected `b1de3c...` parent snapshot can itself prove that the P9 merge was completed. | evidence/variant-reconciliation.json -> merge_target.expected_snapshot_matches_expected_sha256 / merge_target.expected_snapshot_contains_explicit_p9_marker | true / false | Missing evidence: a merge revision containing both the P9 marker and executable result provenance | inconclusive |
| C14 | P9 is dispositioned as merge/archive, with no independent candidate package and no upload. | evidence/variant-reconciliation.json -> decision.disposition / decision.independent_package_created / decision.status | merge_archive / false / archived | Check the decision record, package directory, and repository upload receipts | verified |

## Summary

The existing arXiv identity is real, but it is not evidence that the printed
P9 experiment is reproducible. The present disposition is merge/archive:
P9 is retained as a protocol deposit and must not be promoted as an
independent confirmatory result.
