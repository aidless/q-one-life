# Claim ledger - F2 K-Generalization

Status marker: `agent-proposed, not human publication approval`

| ID | Claim | Evidence file + fields | Value | How to verify | Status |
|---|---|---|---|---|---|
| C01 | The family has three packet source versions plus one source mirror, all with distinct hashes. | evidence/variant-reconciliation.json -> variant_count / distinct_hashes / packet_variant_count / additional_variant_count | 4 / 4 / 3 / 1 | Re-hash every retained source | verified |
| C02 | The canonical source has one title, author block, end-document token, 17 unique labels, and 32 citation keys. | evidence/blocked-audit.json -> structure.labels / structure.citation_keys | 17 / 32 | Run `tools/audit_f2.py` | verified |
| C03 | All 32 citation keys resolve to retained bibliography entries. | evidence/claim-values.json -> citation_keys / missing_citation_count | 32 / 0 | Re-parse every citation and `refs.bib` | verified |
| C04 | `joint_2700.json` declares 2,700 cells and 2,700 holds. | evidence/blocked-audit.json -> joint_2700.declared_cells / joint_2700.declared_holds | 2700 / 2700 | Read the declared scalars | verified |
| C05 | `joint_2700.json` actually archives 2,700 per-cell records. | evidence/claim-values.json -> archived_joint_rows | 5 | Count the stored `cells` rows | blocked |
| C06 | `joint_2700.json` covers all six carried K/gamma conditions without duplicated condition rows. | evidence/claim-values.json -> distinct_joint_conditions / duplicate_condition_rows_present | 3 / 1 | List `(K,gamma)` pairs and compare to the six-condition table | blocked |
| C07 | `analysis_2700.json` contains six K/gamma condition summaries. | evidence/claim-values.json -> analysis_conditions | 6 | Inspect the six `K*_g*` keys | verified |
| C08 | The `bootstrap_2700.json` point values equal the means of their stored `per_seed` arrays within 0.005. | evidence/claim-values.json -> bootstrap_disagreement_count | 2 | Recompute the mean of each 10-value array | blocked |
| C09 | The staged `per_seed.jsonl` reproduces every printed analysis product within 0.005. | evidence/blocked-audit.json -> joint_2700.per_seed_means / joint_2700.analysis_conditions | six means; disagreements present | Recompute every per-condition mean and compare to `analysis_2700.json` | blocked |
| C10 | `episodes.jsonl` contains 2,700 episodes and all three gamma levels. | evidence/claim-values.json -> episode_records / episode_gamma_level_count | 180 / 2 | Count records and distinct gamma values | blocked |
| C11 | The real-LLM subset has 192/144/90/40 archived calls, summing to 466. | evidence/claim-values.json -> archived_real_calls / claimed_frozen_subset_sum | 384 / 466 | Sum the three retained call counts and compare to the frozen subset declaration | blocked |
| C12 | The 64-episode real-LLM carrier is uniform across every condition. | evidence/claim-values.json -> real64_failure_count / real64_constant_product_count | 1 / 8 | Inspect per-episode holds and product fields | blocked |
| C13 | The 128-call carrier records a complete 144-call subset. | evidence/claim-values.json -> real128_archived_calls / real128_remaining_batches | 128 / 1 | Read the retained call-count note | blocked |
| C14 | The 192-call carrier retains per-episode hold records. | evidence/claim-values.json -> real192_per_episode_record_count | 0 | Inspect the carrier schema | blocked |
| C15 | `p16_provenance.json` contains the reported selective effect d_z=0.42, CI [0.18,0.66], and p=0.009. | evidence/claim-values.json -> p16_effect_field_count | 0 | Search for `dz`, `d`, `ci`, and `p` fields | blocked |
| C16 | `protocol.md` contains the declared threshold values 0.810 and 0.797. | evidence/claim-values.json -> protocol_bytes | 218 | Search the retained protocol | blocked |
| C17 | The frozen tightness proof and abstract use the same product range. | evidence/claim-values.json -> proof_abstract_range_conflict_count | 1 | Compare both retained files | blocked |
| C18 | The seven flagged manuscript values have executable carrier receipts. | evidence/claim-values.json -> executable_carrier_count / flagged_value_count | 0 / 7 | Inspect the carrier disposition table | blocked |
| C19 | The family is ready for package construction. | evidence/claim-values.json -> package_created / uploaded | 0 / 0 | Check package and upload receipts | blocked |
| C20 | The family has a closed independent review. | evidence/claim-values.json -> review_reject_count / review_total | 2 / 10 | Require a new current-hash review | blocked |
| C21 | The canonical source contains two unresolved references. | evidence/claim-values.json -> missing_reference_count | 2 | Re-parse every `\ref` and compare against labels | blocked |

## Summary

The source structure and bibliography parse, but the core empirical artifact is a
declaration rather than a sample. The archived per-seed and episode files disagree
with the printed values, the real-LLM carriers mix target and actual counts, and the
selective/drift/causal statistics lack field-level carriers. The disposition is
`blocked`; no candidate package is created.
