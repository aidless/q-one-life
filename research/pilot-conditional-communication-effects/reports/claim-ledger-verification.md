# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The family has seven packet-listed source versions plus one additional :: evidence/variant-reconciliation.json -> variant_count / distinct_hashes / packet_variant_count / additional_variant_count = [8, 8, 7, 1]
- PASS C02: The canonical source has one title, one author block, one end-document :: evidence/blocked-audit.json -> structure.labels / structure.references / structure.citation_keys = [22, 33, 40]
- PASS C03: All 40 citation keys resolve mechanically to 40 bibliography keys. :: evidence/blocked-audit.json -> structure.citation_keys / structure.bib_keys = [40, 40]
- PASS C04: The documented balanced subset yields F_alpha=6.61, F_T=2.95, F_intera :: evidence/blocked-audit.json -> joint_experiment.balanced_recompute.F_A / joint_experiment.balanced_recompute.F_T / joint_experiment.balanced_recompute.F_AB / joint_experiment.balanced_recompute.p_A / joint_experiment.balanced_recompute.p_T / joint_experiment.balanced_recompute.p_AB = [6.609756097560974, 2.9512195121951224, 2.219512195121951, 0.0021581699118363587, 0.08949712601400873, 0.11499644292073037]
- PASS C05: The carrier's stored ANOVA (F_alpha=8.16, F_T=7.845, F_interaction=15. :: evidence/blocked-audit.json -> joint_experiment.stored_anova.F_alpha / joint_experiment.stored_anova.F_T / joint_experiment.stored_anova.F_interaction = [8.16, 7.845, 15.37]; BLOCKED status - keep out of manuscript
- PASS C06: The old paper13 source mirror still carries legacy ANOVA values and mu :: evidence/blocked-audit.json -> structure.legacy_anova_counts_source_mirror.8.16 / structure.legacy_anova_counts_source_mirror.7.84 / structure.legacy_anova_counts_source_mirror.15.37 = [8, 5, 4]
- PASS C07: The joint experiment metadata records 5 tasks, 5 seeds, 125 completed  :: evidence/blocked-audit.json -> joint_experiment.metadata.n_tasks / joint_experiment.metadata.n_seeds / joint_experiment.metadata.total_cells_completed / joint_experiment.metadata.total_calls = [5, 5, 125, 4000]
- PASS C08: The Face-1 C5 CAF contrast and its confidence interval have a raw per- :: evidence/blocked-audit.json -> face1_caf_carrier_search.hit_count = [0]; BLOCKED status - keep out of manuscript
- PASS C09: The +0.207 temporal contrast, its CI, Cohen's d=4.85, and the 90.8 per :: file evidence/upstream/source/evidence/FINDING1_DATA_SEARCH_VERDICT.md exists (non-JSON); BLOCKED status - keep out of manuscript
- PASS C10: The DeepSeek-V4-Pro held-out probe has 3 seeds and a mean T=20 minus T :: evidence/blocked-audit.json -> heldout_v4pro.n_seeds / heldout_v4pro.mean_delta_ece = [3, -0.006666666666666617]
- PASS C11: The 30-seed E4 archive gives uncalibrated/calibrated gamma_TV 1.081/0. :: evidence/blocked-audit.json -> e4.uncalibrated_gTV / e4.calibrated_gTV / e4.gTV_reduction_pct / e4.gVT_reduction_pct = [1.0811, 0.7485, 30.76496161317176, 29.347618136598435]
- PASS C12: The five-condition landscape reproduces r(H,gamma)=-0.989 and r(CV,gam :: evidence/blocked-audit.json -> landscape.n / landscape.r_H_gamma / landscape.r_CV_gamma = [5, -0.988677659711492, -0.9164067346607697]
- PASS C13: Independent review is closed against the canonical hash with no open C :: file evidence/upstream/paper/REVIEW_CARD.md exists (non-JSON); BLOCKED status - keep out of manuscript
- PASS C14: This family currently has a package ready for upload. :: evidence/variant-reconciliation.json -> package_created / uploaded = [False, False]; BLOCKED status - keep out of manuscript
- PASS C15: The current canonical paper uses 6.61/2.95/2.22 and excludes the legac :: evidence/blocked-audit.json -> structure.legacy_anova_counts_current.8.16 / structure.legacy_anova_counts_current.7.845 / structure.legacy_anova_counts_current.7.84 / structure.legacy_anova_counts_current.15.37 = [0, 0, 0, 0]

## Summary: 15 PASS, 0 FAIL, 5 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 415
+0.000, +0.002, +0.003, +0.004, +0.006, +0.007, +0.008, +0.011, +0.012, +0.013, +0.0131, +0.021, +0.035, +0.041, +0.045, +0.054, +0.078, +0.082, +0.100, +0.138, +0.15, +0.181, +0.198, +0.205, +0.207, +0.21, +0.211, +0.220, +0.228, +0.234, +0.242, +0.245, +0.25, +0.253, +0.53, +10.8, +12.4, +14.2, +31.3, +5.3, +5.7, +7.8, -0.000, -0.001, -0.003, -0.0038, -0.004, -0.017, -0.0219, -0.022, -0.0226, -0.023, -0.04, -0.075, -0.08, -0.10, -0.107, -0.12, -0.39, -0.6, -0.842, -0.895, -0.902, -0.912, -0.92, -0.95, -0.969, -0.979, -0.987, -0.992, -0.993, -0.995, -1.000, -1.2, -13.7, -2.2, -2.5, -24.04, -29.4, -3.5