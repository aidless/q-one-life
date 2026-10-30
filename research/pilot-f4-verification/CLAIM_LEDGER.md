# Claim ledger - F4 Verification

Status marker: `agent-proposed, not human publication approval`

| ID | Claim | Evidence file + fields | Value | How to verify | Status |
|---|---|---|---|---|---|
| C01 | The family has three packet-listed source versions plus one additional source mirror, all with distinct hashes. | evidence/variant-reconciliation.json -> variant_count / distinct_hashes / packet_variant_count / additional_variant_count | 4 / 4 / 3 / 1 | Re-hash every retained source and compare content | verified |
| C02 | The canonical source has one title, one author block, one end-document token, unique labels, and no unresolved reference. | evidence/claim-values.json -> label_count / reference_count / missing_reference_count | 15 / 28 / 0 | Run `tools/audit_f4.py` and inspect the structural result | verified |
| C03 | All 42 citation keys resolve to 42 retained bibliography entries. | evidence/claim-values.json -> citation_key_count / bib_key_count / missing_citation_count | 42 / 42 / 0 | Re-parse every citation and every BibTeX entry | verified |
| C04 | The retained 270-cell pilot spans 10 seeds and reproduces the archived mean and population SD. | evidence/blocked-audit.json -> pilot_grid.records / pilot_grid.seeds / pilot_grid.recomputed_mean / pilot_grid.recomputed_population_std | 270 / 10 / 0.249278 / 0.028931 | Recompute from every row in `cells.jsonl` | verified |
| C05 | The retained 270-cell pilot reproduces the archived 95 percent interval. | evidence/blocked-audit.json -> pilot_grid.recomputed_ci95 | 0.245827 / 0.252729 | Recompute the normal-approximation interval from all 270 cells | verified |
| C06 | The manuscript declares 18,000 trials across the four listed family counts. | evidence/claim-values.json -> declared_trials / declared_trial_count_sum | 18000 / 18000 | Read the declared table and sum the four counts | verified |
| C07 | The archive contains 18,000 per-observation trial records. | evidence/claim-values.json -> archived_trials / declared_trials | 270 / 18000 | Count every archived observation and compare to the declaration | blocked |
| C08 | The frozen 192/144/90/40 evidence splits are present in the archive. | evidence/claim-values.json -> frozen_split_files_found / frozen_split_files_declared | 0 / 4 | Search for explicitly named evidence, frozen, split, or trials bundles | blocked |
| C09 | Four GPU-hours are supported by per-family runtime records. | evidence/claim-values.json -> gpu_hours_declared / gpu_hour_carriers | 4.0 / 0 | Locate and sum per-family GPU-hour receipts | blocked |
| C10 | The abstract's `2700` tightness holds have a machine-readable carrier. | evidence/claim-values.json -> headline_2700_hits | 0 | Search every retained JSON numeric leaf for 2700 | blocked |
| C11 | The abstract's `0.686` mean majority bound has a machine-readable carrier. | evidence/claim-values.json -> headline_0686_hits | 0 | Search every retained JSON numeric leaf for 0.686 | blocked |
| C12 | The abstract's Friedman `p=0.002` and Nemenyi `CD=1.47` have machine-readable carriers. | evidence/claim-values.json -> headline_0002_hits / headline_147_hits | 0 / 0 | Search every retained JSON numeric leaf for both values | blocked |
| C13 | The manuscript consistently reports `10/10` gates. | evidence/claim-values.json -> gate_value_count / gate_value_conflict_count | 2 / 1 | Compare the results table with the later reproducibility paragraph | blocked |
| C14 | All eight F4 table rows reproduce their printed p and chi-square at the stated precision. | evidence/claim-values.json -> f4_table_mismatch_rows / f4_table_rows | 4 / 8 | Recompute each row from its printed b and c counts | blocked |
| C15 | The F4 table's printed risk differences are on the same denominator as its b/c counts. | evidence/claim-values.json -> rd_printed_count_mismatch_rows | 2 | Compare (b-c)/300 with each printed RD | blocked |
| C16 | The Finance and Mimicry intervals contain their own point estimates and are not duplicated. | evidence/claim-values.json -> copied_interval_mismatch_rows | 2 | Compare both intervals with both point estimates | blocked |
| C17 | The 32-entry manifest verifies completely. | evidence/claim-values.json -> manifest_match / manifest_mismatch / manifest_absent / manifest_no_hash | 19 / 7 / 5 / 1 | Re-hash every manifest entry and resolve every path | blocked |
| C18 | The paper's 32 carrier receipts are all verifiable. | evidence/claim-values.json -> carrier_pass / carrier_fail / carrier_not_verifiable / carrier_total | 30 / 0 / 2 / 32 | Re-run the carrier gate and preserve NOT_VERIFIABLE as a third state | blocked |
| C19 | The BFCL and WebArena printed accuracies agree with the retained baseline carriers. | evidence/claim-values.json -> baseline_disagreement_count | 2 | Compare the printed 0.95/1.05 with 0.82/0.76 and real40 0.00/0.00 | blocked |
| C20 | The canonical and arXiv variants carry the same author identity. | evidence/claim-values.json -> author_mismatch | 1 | Compare the two author blocks byte for byte | blocked |
| C21 | The native claim ledger matches the 270-cell carrier and the family has a current-hash independent review and package. | evidence/claim-values.json -> native_ledger_stale_value / native_ledger_carrier_value / current_hash_review / package_created / uploaded | 0.2502 / 0.2493 / 0 / 0 / 0 | Compare the native ledger, retained review, and package/upload receipts | blocked |

## Summary

The structure, bibliography, and 270-cell pilot summary are reproducible. The
paper's 18,000-trial, 2,700-hold, 192/144/90/40 split and four-GPU-hour
headlines do not have per-observation carriers; four of eight F4 table rows do
not reproduce their own counts at the stated precision; both copied intervals
exclude their own estimates; 7 manifest entries mismatch and 5 are absent; two
of 32 carrier receipts are NOT_VERIFIABLE; baselines and author metadata
conflict; and the retained review is a rejection. The disposition is `blocked`;
no candidate package is created.
