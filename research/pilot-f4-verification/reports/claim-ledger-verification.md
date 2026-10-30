# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The family has three packet-listed source versions plus one additional :: evidence/variant-reconciliation.json -> variant_count / distinct_hashes / packet_variant_count / additional_variant_count = [4, 4, 3, 1]
- PASS C02: The canonical source has one title, one author block, one end-document :: evidence/claim-values.json -> label_count / reference_count / missing_reference_count = [15, 28, 0]
- PASS C03: All 42 citation keys resolve to 42 retained bibliography entries. :: evidence/claim-values.json -> citation_key_count / bib_key_count / missing_citation_count = [42, 42, 0]
- PASS C04: The retained 270-cell pilot spans 10 seeds and reproduces the archived :: evidence/blocked-audit.json -> pilot_grid.records / pilot_grid.seeds / pilot_grid.recomputed_mean / pilot_grid.recomputed_population_std = [270, 10, 0.24927777777777776, 0.028931396931276266]
- PASS C05: The retained 270-cell pilot reproduces the archived 95 percent interva :: evidence/blocked-audit.json -> pilot_grid.recomputed_ci95 = [[0.24582685204717802, 0.2527287035083775]]
- PASS C06: The manuscript declares 18,000 trials across the four listed family co :: evidence/claim-values.json -> declared_trials / declared_trial_count_sum = [18000, 18000]
- PASS C07: The archive contains 18,000 per-observation trial records. :: evidence/claim-values.json -> archived_trials / declared_trials = [270, 18000]; BLOCKED status - keep out of manuscript
- PASS C08: The frozen 192/144/90/40 evidence splits are present in the archive. :: evidence/claim-values.json -> frozen_split_files_found / frozen_split_files_declared = [0, 4]; BLOCKED status - keep out of manuscript
- PASS C09: Four GPU-hours are supported by per-family runtime records. :: evidence/claim-values.json -> gpu_hours_declared / gpu_hour_carriers = [4.0, 0]; BLOCKED status - keep out of manuscript
- PASS C10: The abstract's 2700 tightness holds have a machine-readable carrier. :: evidence/claim-values.json -> headline_2700_hits = [0]; BLOCKED status - keep out of manuscript
- PASS C11: The abstract's 0.686 mean majority bound has a machine-readable carrie :: evidence/claim-values.json -> headline_0686_hits = [0]; BLOCKED status - keep out of manuscript
- PASS C12: The abstract's Friedman p=0.002 and Nemenyi CD=1.47 have machine-reada :: evidence/claim-values.json -> headline_0002_hits / headline_147_hits = [0, 0]; BLOCKED status - keep out of manuscript
- PASS C13: The manuscript consistently reports 10/10 gates. :: evidence/claim-values.json -> gate_value_count / gate_value_conflict_count = [2, 1]; BLOCKED status - keep out of manuscript
- PASS C14: All eight F4 table rows reproduce their printed p and chi-square at th :: evidence/claim-values.json -> f4_table_mismatch_rows / f4_table_rows = [4, 8]; BLOCKED status - keep out of manuscript
- PASS C15: The F4 table's printed risk differences are on the same denominator as :: evidence/claim-values.json -> rd_printed_count_mismatch_rows = [2]; BLOCKED status - keep out of manuscript
- PASS C16: The Finance and Mimicry intervals contain their own point estimates an :: evidence/claim-values.json -> copied_interval_mismatch_rows = [2]; BLOCKED status - keep out of manuscript
- PASS C17: The 32-entry manifest verifies completely. :: evidence/claim-values.json -> manifest_match / manifest_mismatch / manifest_absent / manifest_no_hash = [19, 7, 5, 1]; BLOCKED status - keep out of manuscript
- PASS C18: The paper's 32 carrier receipts are all verifiable. :: evidence/claim-values.json -> carrier_pass / carrier_fail / carrier_not_verifiable / carrier_total = [30, 0, 2, 32]; BLOCKED status - keep out of manuscript
- PASS C19: The BFCL and WebArena printed accuracies agree with the retained basel :: evidence/claim-values.json -> baseline_disagreement_count = [2]; BLOCKED status - keep out of manuscript
- PASS C20: The canonical and arXiv variants carry the same author identity. :: evidence/claim-values.json -> author_mismatch = [1]; BLOCKED status - keep out of manuscript
- PASS C21: The native claim ledger matches the 270-cell carrier and the family ha :: evidence/claim-values.json -> native_ledger_stale_value / native_ledger_carrier_value / current_hash_review / package_created / uploaded = [0.2502, 0.2493, 0, 0, 0]; BLOCKED status - keep out of manuscript

## Summary: 21 PASS, 0 FAIL, 15 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 192
+0.002, +0.006, +0.010, +0.012, +0.014, +0.015, +0.030, +0.033, +0.043, +0.045, +0.047, +0.049, +0.050, +0.058, +0.061, +0.072, +0.073, +0.078, +0.080, +0.083, +0.100, +0.107, +0.110, +0.113, +0.156, +0.167, +0.95, +1.05, +1.20, +1.5, +1.8, -0.037, -0.041, -0.090, -0.7, -1.5, -27.5, -4.0, 0.00, 0.001, 0.00153, 0.002, 0.0044, 0.00502, 0.01, 0.014, 0.01414, 0.01453, 0.01486, 0.015, 0.019, 0.020, 0.021, 0.026, 0.0289, 0.030, 0.031, 0.03553, 0.0356, 0.037, 0.041, 0.045, 0.052, 0.06, 0.063, 0.063568, 0.063568115234375, 0.064, 0.065, 0.080, 0.083, 0.090, 0.099, 0.1, 0.10, 0.100, 0.1033, 0.10667, 0.110, 0.113