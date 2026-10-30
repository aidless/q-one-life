# Gemma Tool-Selection Paper Claim Ledger

Manuscript: `/home/liuzewen/kaggle-control-20261013/paper-evidence/GEMMA_REVISED.md`
Source SHA-256: `aa25d33d83b55c4bff5716f2777f420b182122faf93b26a78694b5ce9c5ea798`

This ledger distinguishes the preserved 450-record archive, the 48-row fresh
cross-model probe, the current remote Kaggle receipt and the local manuscript
identity. The archive records text decisions; they are not execution outcomes.

| ID | Claim | Evidence file + field | Numeric values | Verification | Status |
|---|---|---|---|---|---|
| C01 | The archive contains 450 rows and 120 substring-scored positive records. | `evidence/toolselect_replay_audit.json -> archive_rows; evidence/toolselect_recompute.json -> per_k.5.scored_correct / per_k.20.scored_correct / per_k.50.scored_correct` | 450 / 24 / 60 / 36 | Re-run `verify_claim_ledger.py`; compare archive row count and per-registry positive counts | verified |
| C02 | The archive shows 96 whole-identifier positives, 12 fully recorded longer-name discrepancies and 12 unresolved truncated positives. | `evidence/toolselect_replay_audit.json -> archive[0].whole_identifier_observed / archive[1].whole_identifier_observed / archive[2].whole_identifier_observed / archive[0].fully_recorded_longer_name_discrepancy / archive[1].fully_recorded_longer_name_discrepancy / archive[2].fully_recorded_longer_name_discrepancy / archive[0].unresolved_truncated_record / archive[1].unresolved_truncated_record / archive[2].unresolved_truncated_record` | 18 / 48 / 30 / 0 / 12 / 0 / 6 / 0 / 6 | Recompute the row classifications and verify the three registry buckets | verified |
| C03 | The archive contains 75 distinct registry-record pairs, and each retained signature occurs six times. | `evidence/toolselect_replay_audit.json -> distinct_registry_record_pairs / archive[1].signature_multiplicities[0]` | 75 / 6 | Recompute distinct complete-record signatures and multiplicity | verified |
| C04 | The fresh probe contains 48 rows; Qwen has 22/24 correct tool names and 21/24 correct arguments, while Llama has 10/24 and 7/24. | `evidence/toolselect_cross_model_analysis.json -> rows / models[0].flat_contract_tool_correct / models[0].flat_contract_arguments_correct / models[1].flat_contract_tool_correct / models[1].flat_contract_arguments_correct` | 48 / 22 / 21 / 10 / 7 | Re-run the cross-model probe analysis from the preserved records | verified |
| C05 | The remote Kaggle writeup is PUBLISHED with a verified submitted banner and 1611 editor words / 1631 whitespace words. | `evidence/publication_receipt_20261016.json -> articles.gemma-4-developer-agent-paper.contentState / articles.gemma-4-developer-agent-paper.submitted_banner_verified_after_update / articles.gemma-4-developer-agent-paper.editor_word_count / articles.gemma-4-developer-agent-paper.whitespace_word_count` | 1611 / 1631 | Inspect the authenticated publication receipt and preserve its file hash | verified |
| C06 | The exact remote source bytes recorded by the publication receipt (SHA-256 `2ad3ce3d...92d8`) have been recovered as `source/WRITEUP.md` and hash-verified. The local `GEMMA_REVISED.md` remains the pre-publication draft. | `evidence/manuscript_identity_recovered.json -> recovered_source_sha256 / matches_published_source` | - | Verify `source/WRITEUP.md` against the receipt hash; this proves source lineage, not that the local draft is the published source | verified |
| C07 | Among valid wrong selected-tool responses, the probe records 1 Qwen and 3 Llama substring false positives. | `evidence/toolselect_cross_model_analysis.json -> models[0].substring_false_positives_valid_wrong_selected_tool / models[1].substring_false_positives_valid_wrong_selected_tool` | 1 / 3 | Recompute substring versus whole-identifier matching on preserved responses | verified |
| C08 | The preserved replay does not establish tool execution correctness or task success. | `evidence/toolselect_cross_model_analysis.json -> no_tool_execution / no_inferential_pvalues / format_discrepancies_are_not_semantic_errors` | - | Inspect the probe analysis and confirm that no execution outcome was recorded | verified |

## Strong Assertion Review

| Assertion | Evidence scope | Permitted wording | Decision |
|---|---|---|---|
| Substring matching credits a shorter identifier inside a longer one | Preserved archive and scorer | "The scorer's substring rule produces record-level discrepancies" | Keep |
| The archive establishes model capability or a population error rate | Missing requests, registries and independent trial identities | Do not claim a capability ranking or population rate | Block |
| Forty-eight fresh outputs establish a model ranking | Two local models, six requests, one generation per condition | Report only descriptive counts and contract discrepancies | Keep bounded |
| The local Markdown is the exact published source | Local and remote hashes differ | "The local copy must be resynchronized" | Block |
