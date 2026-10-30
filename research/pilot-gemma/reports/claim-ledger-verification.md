# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The archive contains 450 rows and 120 substring-scored positive record :: evidence/toolselect_replay_audit.json -> archive_rows = [450]; evidence/toolselect_recompute.json -> per_k.5.scored_correct / per_k.20.scored_correct / per_k.50.scored_correct = [24, 60, 36]
- PASS C02: The archive shows 96 whole-identifier positives, 12 fully recorded lon :: evidence/toolselect_replay_audit.json -> archive[0].whole_identifier_observed / archive[1].whole_identifier_observed / archive[2].whole_identifier_observed / archive[0].fully_recorded_longer_name_discrepancy / archive[1].fully_recorded_longer_name_discrepancy / archive[2].fully_recorded_longer_name_discrepancy / archive[0].unresolved_truncated_record / archive[1].unresolved_truncated_record / archive[2].unresolved_truncated_record = [18, 48, 30, 0, 12, 0, 6, 0, 6]
- PASS C03: The archive contains 75 distinct registry-record pairs, and each retai :: evidence/toolselect_replay_audit.json -> distinct_registry_record_pairs / archive[1].signature_multiplicities[0] = [75, 6]
- PASS C04: The fresh probe contains 48 rows; Qwen has 22/24 correct tool names an :: evidence/toolselect_cross_model_analysis.json -> rows / models[0].flat_contract_tool_correct / models[0].flat_contract_arguments_correct / models[1].flat_contract_tool_correct / models[1].flat_contract_arguments_correct = [48, 22, 21, 10, 7]
- PASS C05: The remote Kaggle writeup is PUBLISHED with a verified submitted banne :: evidence/publication_receipt_20261016.json -> articles.gemma-4-developer-agent-paper.contentState / articles.gemma-4-developer-agent-paper.submitted_banner_verified_after_update / articles.gemma-4-developer-agent-paper.editor_word_count / articles.gemma-4-developer-agent-paper.whitespace_word_count = ['PUBLISHED', True, 1611, 1631]
- PASS C06: The exact remote source bytes recorded by the publication receipt (SHA :: evidence/manuscript_identity_recovered.json -> recovered_source_sha256 / matches_published_source = ['2ad3ce3d05303adc2adce3444c1e7d4ccf640d242b90499cd9f9d1d5022092d8', True]
- PASS C07: Among valid wrong selected-tool responses, the probe records 1 Qwen an :: evidence/toolselect_cross_model_analysis.json -> models[0].substring_false_positives_valid_wrong_selected_tool / models[1].substring_false_positives_valid_wrong_selected_tool = [1, 3]
- PASS C08: The preserved replay does not establish tool execution correctness or  :: evidence/toolselect_cross_model_analysis.json -> no_tool_execution / no_inferential_pvalues / format_discrepancies_are_not_semantic_errors = [True, True, True]

## Summary: 8 PASS, 0 FAIL, 0 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 5
-1.5, -2.0, 1.5, 2.5, 3.2