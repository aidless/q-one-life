# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The canonical source, four arXiv-labelled copies and two additional va :: evidence/variant-reconciliation.json -> distinct_hashes / variant_count = [7, 7]
- PASS C02: The canonical source begins with an explicit DEPRECATED / DO NOT SUBMI :: evidence/claim-values.json -> deprecated_banner_present = [1]
- PASS C03: The merge marker states that the family is archived into tmlr_p12 and  :: evidence/claim-values.json -> merge_marker_says_merged = [1]
- PASS C04: The named tmlr_p12 merge target does not contain the calibration/resam :: evidence/claim-values.json -> p12_study_term_count / p12_has_p15_study = [0, 0]; BLOCKED status - keep out of manuscript
- PASS C05: The canonical and four arXiv-labelled copies use incompatible dataset  :: evidence/claim-values.json -> canonical_synthetic_mentions / arxiv_three_real_mentions = [16, 12]; BLOCKED status - keep out of manuscript
- PASS C06: The E1 archive has 240 rows and covers six dataset/classifier N=500 to :: evidence/audit.json -> e1.rows / e1.pair_count = [240, 6]
- PASS C07: On E1, 20ng RF moves from 0.3201 to 0.4021 and MLP from 0.1987 to 0.05 :: evidence/claim-values.json -> e1_20ng_rf_n500 / e1_20ng_rf_n5000 / e1_20ng_mlp_n500 / e1_20ng_mlp_n5000 = [0.32007200398151836, 0.40209164130051245, 0.1986644749902189, 0.050923726405203346]
- PASS C08: On E1, ag_news RF moves from 0.3557 to 0.3072 and MLP from 0.3608 to 0 :: evidence/claim-values.json -> e1_ag_rf_n500 / e1_ag_rf_n5000 / e1_ag_mlp_n500 / e1_ag_mlp_n5000 = [0.35574, 0.30719254793576395, 0.3607946293652058, 0.03156047333478928]
- PASS C09: On E1, dbpedia RF moves from 0.5662 to 0.5828 and MLP from 0.3906 to 0 :: evidence/claim-values.json -> e1_dbpedia_rf_n500 / e1_dbpedia_rf_n5000 / e1_dbpedia_mlp_n500 / e1_dbpedia_mlp_n5000 = [0.56623, 0.5828275587830809, 0.39061077280342577, 0.028780884170532223]
- PASS C10: The E6 K=4 result contradicts the abstract's claim that both models im :: evidence/claim-values.json -> k4_rf_n500 / k4_rf_n5000 / k4_mlp_n500 / k4_mlp_n5000 / k4_both_improve_supported = [0.2520210277777778, 0.26615115150545127, 0.20322735318541527, 0.07023410770595073, 0]; BLOCKED status - keep out of manuscript
- PASS C11: The headline 4-class, 88 percent temperature-scaling and resampling va :: evidence/claim-values.json -> k4_both_improve_supported / smote_p_field_present / rus_0395_field_present / posthoc_m0003_field_present = [0, 1, 0, 0]; BLOCKED status - keep out of manuscript
- PASS C12: The retained 201-row carrier receipt file has 159 PASS verdicts and 42 :: evidence/claim-values.json -> carrier_total / carrier_pass / carrier_absent_verdict = [201, 159, 42]
- PASS C13: The 42 unverdicted receipts are concentrated in E1, E6 and E8, not dis :: evidence/claim-values.json -> carrier_absent_e1 / carrier_absent_e6 / carrier_absent_e8 = [26, 10, 6]
- PASS C14: The retained review is 5/10 and recommends merging into tmlr_p12, with :: evidence/claim-values.json -> review_score = ['5/10']
- PASS C15: The only defensible disposition is merge_archive / archived, with no i :: evidence/claim-values.json -> independent_package_created / uploaded = [0, 0]

## Summary: 15 PASS, 0 FAIL, 4 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 255
+0.009, +0.014, +0.015, +0.016, +0.02, +0.047, +0.10, +0.134, +0.395, -0.003, -0.012, -0.036, -0.037, -0.040, -1.9, 0.001, 0.002, 0.0029, 0.003, 0.004, 0.0044, 0.005, 0.0054, 0.006, 0.007, 0.008, 0.009, 0.01, 0.010, 0.011, 0.012, 0.013, 0.015, 0.016, 0.018, 0.019, 0.02, 0.020, 0.021, 0.022, 0.023, 0.024, 0.025, 0.027, 0.0271, 0.028, 0.029, 0.030, 0.031, 0.036, 0.037, 0.038, 0.039, 0.04, 0.040, 0.041, 0.042, 0.043, 0.046, 0.047, 0.048, 0.049, 0.05, 0.050, 0.051, 0.052, 0.057, 0.058, 0.059, 0.060, 0.061, 0.063, 0.064, 0.065, 0.068, 0.07, 0.070, 0.071, 0.072, 0.073