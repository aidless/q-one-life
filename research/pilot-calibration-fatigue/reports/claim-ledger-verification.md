# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The selected canonical source is retained byte-for-byte from the sourc :: evidence/source_record.json -> canonical_sha256 / byte_identical = ['b1de3c420d53f5333d4a522d3e3856c612520667bb209273b86f7ded2af99cd4', True]
- PASS C02: Fourteen retained source files collapse to eleven hashes; the arXiv-cl :: evidence/variant-reconciliation.json -> retained_files / distinct_hashes = [14, 11]; evidence/claim-values.json -> preprint_equals_backup = [1]
- PASS C03: The 919-entry evidence manifest is internally complete, but the outer  :: evidence/claim-values.json -> evidence_manifest_match / outer_manifest_mismatch / outer_manifest_absent / arxiv_manifest_mismatch / generated_manifest_mismatch = [919, 14, 3, 5, 1]; file evidence/revision-source.json ok (no field); BLOCKED status - keep out of manuscript
- PASS C04: The calibration grid contains 72 rows and 45 positive-alpha method con :: evidence/claim-values.json -> grid_rows / grid_contrasts / grid_mean_delta_pct = [72, 45, -3.481899774262735]
- PASS C05: The printed -7.0% to -0.6% range is not the condition-level Delta CV r :: evidence/claim-values.json -> grid_cell_min_pct / grid_cell_max_pct = [-28.408319455132023, 33.860120231307825]; BLOCKED status - keep out of manuscript
- PASS C06: The T30 archive has 120 unique condition/seed rows and all 120 CSV row :: evidence/claim-values.json -> t30_seeds / t30_csv_differences / t30_summary_differences = [120, 0, 0]
- PASS C07: The T50 archive has 120 unique condition/seed rows; its summary reprod :: evidence/claim-values.json -> t50_seeds / t50_summary_differences / t50_late_gamma_d / t50_late_gamma_p = [120, 0, -0.16933249753436797, 0.3555745990160197]
- PASS C08: T50 per-seed ECE is recoverable from archived confidence/correctness p :: evidence/claim-values.json -> t50_ece_observations / t50_ece_recovered_seeds / t50_ece_stored_differences / t50_ece_comm_p / t50_ece_cal_p = [30000, 120, 0, 0.9864074387701495, 0.7023691340659403]
- PASS C09: The 30-seed predecessor archive is corrupt: conditions A, C and D cont :: evidence/claim-values.json -> acd_equal = [1]; BLOCKED status - keep out of manuscript
- PASS C10: The 90.8%, gamma about 1.06, 42%, and 35-37% headlines lack valid raw  :: evidence/claim-values.json -> reference_bound_90_8_receipts / qwen_temporal_share_pct = [11, -5.147106119665931]; BLOCKED status - keep out of manuscript
- PASS C11: The canonical bibliography resolves all 29 cited keys across both decl :: evidence/claim-values.json -> missing_citations / missing_bibliographies / citation_identities_checked = [0, 0, 2]
- PASS C12: The 200-row local Qwen2 probe reproduces its reported direction: mean  :: evidence/claim-values.json -> low_temp_cv / high_temp_cv / real_pilot_rows = [0.003093434343434347, 0.0060348274969800365, 200]
- PASS C13: The retained reviews leave raw-trace, theorem-dependence and prospecti :: file evidence/upstream/REVIEW_R16_summary.md exists (non-JSON); file evidence/revision-source.json ok (no field); BLOCKED status - keep out of manuscript
- PASS C14: The defensible disposition remains blocked: an internal revision compi :: evidence/claim-values.json -> independent_package_created / uploaded / revision_cleanroom_pages = [0, 0, 26]; BLOCKED status - keep out of manuscript

## Summary: 14 PASS, 0 FAIL, 6 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 337
+0.000, +0.0003, +0.002, +0.003, +0.004, +0.006, +0.008, +0.010, +0.012, +0.0131, +0.015, +0.018, +0.021, +0.022, +0.029, +0.041, +0.078, +0.079, +0.081, +0.082, +0.096, +0.127, +0.148, +0.170, +0.181, +0.205, +0.207, +0.208, +0.21, +0.220, +0.225, +0.228, +0.234, +0.253, +0.286, +0.309, +0.7, +1.7, +10.8, +31.3, +33.9, +4.4, +5.7, -0.003, -0.0038, -0.004, -0.0219, -0.0226, -0.04, -0.072, -0.086, -0.123, -0.169, -0.17, -0.177, -0.213, -0.245, -0.332, -0.6, -0.989, -1.2, -11.6, -13.7, -14.4, -14.8, -2.2, -24.04, -28.4, -3.5, -3.7, -35.4, -37.2, -6.5, -60.2, -63.4, -7.0, -8.7, 0.0, 0.000, 0.0001