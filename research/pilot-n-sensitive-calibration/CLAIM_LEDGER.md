# Claim ledger - N-Sensitive Calibration archive

Status marker: `agent-proposed, not human publication approval`

| ID | Claim | Evidence file + fields | Value | How to verify | Status |
|---|---|---|---|---|---|
| C01 | The canonical source, four arXiv-labelled copies and two additional variants have 7 distinct hashes out of 7 retained files. | evidence/variant-reconciliation.json -> distinct_hashes / variant_count | 7 / 7 | Re-hash every retained source | verified |
| C02 | The canonical source begins with an explicit DEPRECATED / DO NOT SUBMIT INDEPENDENTLY banner. | evidence/claim-values.json -> deprecated_banner_present | 1 | Inspect the first eight lines of `evidence/upstream/main.tex` | verified |
| C03 | The merge marker states that the family is archived into `tmlr_p12` and must not be submitted independently. | evidence/claim-values.json -> merge_marker_says_merged | 1 | Read the retained merge marker | verified |
| C04 | The named `tmlr_p12` merge target does not contain the calibration/resampling study's identifying terms. | evidence/claim-values.json -> p12_study_term_count / p12_has_p15_study | 0 / 0 | Search the pinned p12 source for the study-specific terms | blocked |
| C05 | The canonical and four arXiv-labelled copies use incompatible dataset scopes. | evidence/claim-values.json -> canonical_synthetic_mentions / arxiv_three_real_mentions | 16 / 12 | Compare the retained source copies line by line | blocked |
| C06 | The E1 archive has 240 rows and covers six dataset/classifier N=500 to N=5000 adaptive-ECE pairs. | evidence/audit.json -> e1.rows / e1.pair_count | 240 / 6 | Recompute group means from all E1 rows | verified |
| C07 | On E1, 20ng RF moves from 0.3201 to 0.4021 and MLP from 0.1987 to 0.0509. | evidence/claim-values.json -> e1_20ng_rf_n500 / e1_20ng_rf_n5000 / e1_20ng_mlp_n500 / e1_20ng_mlp_n5000 | 0.3201 / 0.4021 / 0.1987 / 0.0509 | Recompute the E1 group means | verified |
| C08 | On E1, ag_news RF moves from 0.3557 to 0.3072 and MLP from 0.3608 to 0.0316. | evidence/claim-values.json -> e1_ag_rf_n500 / e1_ag_rf_n5000 / e1_ag_mlp_n500 / e1_ag_mlp_n5000 | 0.3557 / 0.3072 / 0.3608 / 0.0316 | Recompute the E1 group means | verified |
| C09 | On E1, dbpedia RF moves from 0.5662 to 0.5828 and MLP from 0.3906 to 0.0288. | evidence/claim-values.json -> e1_dbpedia_rf_n500 / e1_dbpedia_rf_n5000 / e1_dbpedia_mlp_n500 / e1_dbpedia_mlp_n5000 | 0.5662 / 0.5828 / 0.3906 / 0.0288 | Recompute the E1 group means | verified |
| C10 | The E6 K=4 result contradicts the abstract's claim that both models improve modestly: RF worsens from 0.2520 to 0.2662 while MLP improves from 0.2032 to 0.0702. | evidence/claim-values.json -> k4_rf_n500 / k4_rf_n5000 / k4_mlp_n500 / k4_mlp_n5000 / k4_both_improve_supported | 0.2520 / 0.2662 / 0.2032 / 0.0702 / 0 | Recompute each K=4 group from all ten seeds | blocked |
| C11 | The headline 4-class, 88 percent temperature-scaling and resampling values have a complete machine-readable carrier set. | evidence/claim-values.json -> k4_both_improve_supported / smote_p_field_present / rus_0395_field_present / posthoc_m0003_field_present | 0 / 1 / 0 / 0 | Search the named result archives for the declared fields | blocked |
| C12 | The retained 201-row carrier receipt file has 159 PASS verdicts and 42 rows without any verdict. | evidence/claim-values.json -> carrier_total / carrier_pass / carrier_absent_verdict | 201 / 159 / 42 | Count `_verdict` values and absent keys | verified |
| C13 | The 42 unverdicted receipts are concentrated in E1, E6 and E8, not distributed across the archive. | evidence/claim-values.json -> carrier_absent_e1 / carrier_absent_e6 / carrier_absent_e8 | 26 / 10 / 6 | Group missing verdicts by artifact path | verified |
| C14 | The retained review is 5/10 and recommends merging into `tmlr_p12`, with two Major findings still open. | evidence/claim-values.json -> review_score | 5/10 | Read the retained review card | verified |
| C15 | The only defensible disposition is `merge_archive` / `archived`, with no independent package and no upload. | evidence/claim-values.json -> independent_package_created / uploaded | 0 / 0 | Check the disposition record, package directory and upload receipts | verified |

## Summary

The family is explicitly deprecated by its own canonical source. Four arXiv-labelled source copies use a different dataset scope from the canonical synthetic-only manuscript. The target manuscript named by the archive marker does not textually contain this study, so the merge provenance is unresolved. E1 and E6 reproduce mechanically, but E6 directly falsifies the abstract sentence that both models improve at four classes. The resampling headline values do not have named fields in the retained result archive, and 42 of 201 carrier receipts have no verdict. The correct disposition is archive/merge with no independent package.
