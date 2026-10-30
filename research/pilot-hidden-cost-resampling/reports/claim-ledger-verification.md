# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The canonical source is retained byte-for-byte and has the recorded SH :: evidence/source_record.json -> canonical_sha256 / byte_identical = ['b1ea39681d0b89002fd520f816dea590d5daccf1cea1c5c106a703c544fcefba', True]
- PASS C02: The canonical source starts with an explicit DEPRECATED / DO NOT SUBMI :: evidence/claim-values.json -> deprecated_banner_present = [1]
- PASS C03: Seven retained source files have seven distinct hashes; byte-identical :: evidence/variant-reconciliation.json -> retained_files / distinct_hashes = [7, 7]
- PASS C04: The archive marker says the side shell must not be submitted or upload :: evidence/claim-values.json -> merge_marker_says_merged = [1]
- PASS C05: The named tmlr_p12 target shares N-sensitivity vocabulary but contains :: evidence/claim-values.json -> p12_study_term_matches / p12_has_p16_numeric_carrier = [0, 0]; BLOCKED status - keep out of manuscript
- PASS C06: The canonical text names a synthetic benchmark, while the main snapsho :: evidence/claim-values.json -> main_snapshot_dataset_newsgroups / main_snapshot_classes / main_snapshot_embedding_key = [1, 8, 'minilm-en']; BLOCKED status - keep out of manuscript
- PASS C07: The title says resampling, but the manuscript contains only one occurr :: evidence/claim-values.json -> title_resampling_occurrences / smote_occurrences / undersampling_occurrences = [1, 0, 0]; BLOCKED status - keep out of manuscript
- PASS C08: The 195431 snapshot recomputes MLP ECE 0.1410, RF-Embed ECE 0.0957 and :: evidence/claim-values.json -> mlp_embed_ece / rf_embed_ece / rf_hybrid_ece = [0.140982293418553, 0.09570733937161496, 0.08985444402642398]
- PASS C09: Snapshot AUROCs are MLP 0.8667, RF-Embed 0.8778, RF-Hybrid 0.8754, RF- :: evidence/claim-values.json -> mlp_embed_auroc / rf_embed_auroc / rf_hybrid_auroc / rf_tabular_auroc = [0.8667479548110635, 0.8777659827728, 0.8753834134095139, 0.6601408258667705]; BLOCKED status - keep out of manuscript
- PASS C10: Snapshot Brier scores are MLP 0.5752, RF-Embed 0.4579, RF-Hybrid 0.461 :: evidence/claim-values.json -> mlp_embed_brier / rf_embed_brier / rf_hybrid_brier / rf_tabular_brier = [0.5751793531958962, 0.4579114351274139, 0.4617148059638974, 0.6968101165984253]; BLOCKED status - keep out of manuscript
- PASS C11: Isotonic calibration changes RF-Hybrid ECE from 0.0899 to 0.0675 (24.8 :: evidence/claim-values.json -> isotonic_ece_before / isotonic_ece_after / isotonic_ece_reduction_pct / isotonic_auroc_change = [0.08985444402642398, 0.06752096175451545, 24.855178298516655, -0.037834328875037904]; BLOCKED status - keep out of manuscript
- PASS C12: Of 15 pairwise Wilcoxon tests, 12 are nominally significant but only 1 :: evidence/claim-values.json -> pairwise_count / pairwise_raw_significant / pairwise_corrected_significant = [15, 12, 10]; BLOCKED status - keep out of manuscript
- PASS C13: The N-sensitivity table has one incorrect cell: RF-Embed N=200 should  :: evidence/claim-values.json -> rf_embed_n200 / rf_hybrid_n5000 / mlp_n500 = [0.1504933576108253, 0.08322735145295354, 0.14760075455420826]; BLOCKED status - keep out of manuscript
- PASS C14: Pearson correlation is neither -0.973 for RF-Hybrid nor +0.078 for MLP :: evidence/claim-values.json -> rf_hybrid_r_linear / mlp_r_linear / rf_hybrid_r_log10 = [-0.6661508837234755, -0.120090684746609, -0.8844131423159208]; BLOCKED status - keep out of manuscript
- PASS C15: All 57 carrier receipts are marked PASS, but 42 bind the printed numbe :: evidence/claim-values.json -> carrier_total / carrier_pass / carrier_semantic_mismatch = [57, 57, 42]; BLOCKED status - keep out of manuscript
- PASS C16: The stored anonymity record says anonymous, but canonical main.tex con :: evidence/claim-values.json -> anonymous_record_conflict = [1]; BLOCKED status - keep out of manuscript
- PASS C17: The manuscript has two Limitations sections and says no sample-size sw :: evidence/claim-values.json -> limitations_headings / says_no_sample_size_sweep / has_sample_size_table = [2, 1, 1]; BLOCKED status - keep out of manuscript
- PASS C18: The retained review is 2/8, D veto / reject, and the R16 summary requi :: evidence/claim-values.json -> review_card_score = ['2/8']
- PASS C19: The only defensible disposition is merge_archive / archived, with no i :: evidence/claim-values.json -> independent_package_created / uploaded = [0, 0]

## Summary: 19 PASS, 0 FAIL, 12 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 154
+0.000, +0.003, +0.004, +0.012, +0.021, +0.041, +0.078, +0.082, +0.181, +0.205, +0.207, +0.228, +0.234, +0.253, -0.004, -0.09, -0.102, -0.12, -0.63, -0.973, -1.00, -1.57, -1.88, -2.3, -2.4, -3.1, -3.65, -3.7, -3.75, -4.83, 0.0001, 0.001, 0.002, 0.003, 0.006, 0.007, 0.01, 0.012, 0.014, 0.017, 0.018, 0.02, 0.022, 0.024, 0.028, 0.031, 0.037, 0.04, 0.040, 0.041, 0.043, 0.05, 0.050, 0.06, 0.065, 0.071, 0.072, 0.074, 0.078, 0.08, 0.086, 0.089, 0.094, 0.099, 0.102, 0.103, 0.106, 0.116, 0.118, 0.129, 0.130, 0.131, 0.135, 0.15, 0.151, 0.165, 0.198, 0.20, 0.219, 0.22