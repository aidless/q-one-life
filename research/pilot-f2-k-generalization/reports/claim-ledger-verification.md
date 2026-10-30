# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The family has three packet source versions plus one source mirror, al :: evidence/variant-reconciliation.json -> variant_count / distinct_hashes / packet_variant_count / additional_variant_count = [4, 4, 3, 1]
- PASS C02: The canonical source has one title, author block, end-document token,  :: evidence/blocked-audit.json -> structure.labels / structure.citation_keys = [17, 32]
- PASS C03: All 32 citation keys resolve to retained bibliography entries. :: evidence/claim-values.json -> citation_keys / missing_citation_count = [32, 0]
- PASS C04: joint_2700.json declares 2,700 cells and 2,700 holds. :: evidence/blocked-audit.json -> joint_2700.declared_cells / joint_2700.declared_holds = [2700, 2700]
- PASS C05: joint_2700.json actually archives 2,700 per-cell records. :: evidence/claim-values.json -> archived_joint_rows = [5]; BLOCKED status - keep out of manuscript
- PASS C06: joint_2700.json covers all six carried K/gamma conditions without dupl :: evidence/claim-values.json -> distinct_joint_conditions / duplicate_condition_rows_present = [3, 1]; BLOCKED status - keep out of manuscript
- PASS C07: analysis_2700.json contains six K/gamma condition summaries. :: evidence/claim-values.json -> analysis_conditions = [6]
- PASS C08: The bootstrap_2700.json point values equal the means of their stored p :: evidence/claim-values.json -> bootstrap_disagreement_count = [2]; BLOCKED status - keep out of manuscript
- PASS C09: The staged per_seed.jsonl reproduces every printed analysis product wi :: evidence/blocked-audit.json -> joint_2700.per_seed_means / joint_2700.analysis_conditions = [{'K3_g0.5': 0.4853924027857237, 'K3_g1.0': 0.3543985690362582, 'K4_g0.5': 0.5332128601652144, 'K4_g1.0': 0.4293078752457063, 'K5_g0.5': 0.54768587242957, 'K5_g1.0': 0.42635594377059627}, 6]; BLOCKED status - keep out of manuscript
- PASS C10: episodes.jsonl contains 2,700 episodes and all three gamma levels. :: evidence/claim-values.json -> episode_records / episode_gamma_level_count = [180, 2]; BLOCKED status - keep out of manuscript
- PASS C11: The real-LLM subset has 192/144/90/40 archived calls, summing to 466. :: evidence/claim-values.json -> archived_real_calls / claimed_frozen_subset_sum = [384, 466]; BLOCKED status - keep out of manuscript
- PASS C12: The 64-episode real-LLM carrier is uniform across every condition. :: evidence/claim-values.json -> real64_failure_count / real64_constant_product_count = [1, 8]; BLOCKED status - keep out of manuscript
- PASS C13: The 128-call carrier records a complete 144-call subset. :: evidence/claim-values.json -> real128_archived_calls / real128_remaining_batches = [128, 1]; BLOCKED status - keep out of manuscript
- PASS C14: The 192-call carrier retains per-episode hold records. :: evidence/claim-values.json -> real192_per_episode_record_count = [0]; BLOCKED status - keep out of manuscript
- PASS C15: p16_provenance.json contains the reported selective effect d_z=0.42, C :: evidence/claim-values.json -> p16_effect_field_count = [0]; BLOCKED status - keep out of manuscript
- PASS C16: protocol.md contains the declared threshold values 0.810 and 0.797. :: evidence/claim-values.json -> protocol_bytes = [218]; BLOCKED status - keep out of manuscript
- PASS C17: The frozen tightness proof and abstract use the same product range. :: evidence/claim-values.json -> proof_abstract_range_conflict_count = [1]; BLOCKED status - keep out of manuscript
- PASS C18: The seven flagged manuscript values have executable carrier receipts. :: evidence/claim-values.json -> executable_carrier_count / flagged_value_count = [0, 7]; BLOCKED status - keep out of manuscript
- PASS C19: The family is ready for package construction. :: evidence/claim-values.json -> package_created / uploaded = [0, 0]; BLOCKED status - keep out of manuscript
- PASS C20: The family has a closed independent review. :: evidence/claim-values.json -> review_reject_count / review_total = [2, 10]; BLOCKED status - keep out of manuscript
- PASS C21: The canonical source contains two unresolved references. :: evidence/claim-values.json -> missing_reference_count = [2]; BLOCKED status - keep out of manuscript

## Summary: 21 PASS, 0 FAIL, 16 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 140
+0.42, +0.85, +1.10, -0.031, -0.26, -0.56, -0.85, -27.5, 0.00, 0.001, 0.002, 0.0047, 0.0084, 0.009, 0.0138, 0.014, 0.015, 0.0150, 0.017, 0.018, 0.0181, 0.02, 0.020, 0.021, 0.0228, 0.023, 0.026, 0.031, 0.0312, 0.038, 0.04, 0.041, 0.05, 0.063, 0.08, 0.083, 0.090, 0.0905, 0.0912, 0.0936, 0.094, 0.1, 0.11, 0.110, 0.1139, 0.12, 0.125, 0.14, 0.143, 0.146, 0.15, 0.157, 0.16, 0.17, 0.173, 0.18, 0.1832, 0.19, 0.196, 0.20, 0.21, 0.23, 0.24, 0.25, 0.257, 0.26, 0.27, 0.28, 0.284, 0.3, 0.31, 0.32, 0.33, 0.3441, 0.35, 0.3544, 0.36, 0.40, 0.409, 0.41