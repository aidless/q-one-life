# Claim ledger - Conditional Communication Effects

Status marker: `agent-proposed, not human publication approval`

| ID | Claim | Evidence file + fields | Value | How to verify | Status |
|---|---|---|---|---|---|
| C01 | The family has seven packet-listed source versions plus one additional source mirror, all with distinct hashes. | evidence/variant-reconciliation.json -> variant_count / distinct_hashes / packet_variant_count / additional_variant_count | 8 / 8 / 7 / 1 | Re-hash every retained source and group by content | verified |
| C02 | The canonical source has one title, one author block, one end-document token, unique labels, and resolvable references. | evidence/blocked-audit.json -> structure.labels / structure.references / structure.citation_keys | 22 / 33 / 40 | Run `tools/audit_paper13.py` and inspect structural checks | verified |
| C03 | All 40 citation keys resolve mechanically to 40 bibliography keys. | evidence/blocked-audit.json -> structure.citation_keys / structure.bib_keys | 40 / 40 | Re-parse every citation and every retained BibTeX entry | verified |
| C04 | The documented balanced subset yields F_alpha=6.61, F_T=2.95, F_interaction=2.22, with p=0.0022, 0.089, and 0.115. | evidence/blocked-audit.json -> joint_experiment.balanced_recompute.F_A / joint_experiment.balanced_recompute.F_T / joint_experiment.balanced_recompute.F_AB / joint_experiment.balanced_recompute.p_A / joint_experiment.balanced_recompute.p_T / joint_experiment.balanced_recompute.p_AB | 6.61 / 2.95 / 2.22 / 0.0022 / 0.089 / 0.115 | Recompute the balanced two-way ANOVA from the delivered sessions | verified |
| C05 | The carrier's stored ANOVA (F_alpha=8.16, F_T=7.845, F_interaction=15.37) is reproducible from the delivered sessions. | evidence/blocked-audit.json -> joint_experiment.stored_anova.F_alpha / joint_experiment.stored_anova.F_T / joint_experiment.stored_anova.F_interaction | 8.16 / 7.845 / 15.37 | Compare the stored block with the recomputed balanced subset and exact reachability | blocked |
| C06 | The old paper13 source mirror still carries legacy ANOVA values and must not be treated as canonical. | evidence/blocked-audit.json -> structure.legacy_anova_counts_source_mirror.8.16 / structure.legacy_anova_counts_source_mirror.7.84 / structure.legacy_anova_counts_source_mirror.15.37 | 8 / 5 / 4 | Search the retained source mirror for the legacy values | verified |
| C07 | The joint experiment metadata records 5 tasks, 5 seeds, 125 completed sessions, and 4,000 calls. | evidence/blocked-audit.json -> joint_experiment.metadata.n_tasks / joint_experiment.metadata.n_seeds / joint_experiment.metadata.total_cells_completed / joint_experiment.metadata.total_calls | 5 / 5 / 125 / 4000 | Read the metadata block and cross-check the session count | verified |
| C08 | The Face-1 C5 CAF contrast and its confidence interval have a raw per-seed carrier in the retained evidence. | evidence/blocked-audit.json -> face1_caf_carrier_search.hit_count | 0 | Search every retained JSON numeric leaf for the printed CAF endpoints | blocked |
| C09 | The +0.207 temporal contrast, its CI, Cohen's d=4.85, and the 90.8 percent share are independently recomputable from archived GPT-4o per-repetition rows. | evidence/upstream/source/evidence/FINDING1_DATA_SEARCH_VERDICT.md | missing | Restore the GPT-4o per-repetition ECE records; the search verdict records that they were never archived | blocked |
| C10 | The DeepSeek-V4-Pro held-out probe has 3 seeds and a mean T=20 minus T=10 ECE delta of -0.007. | evidence/blocked-audit.json -> heldout_v4pro.n_seeds / heldout_v4pro.mean_delta_ece | 3 / -0.007 | Recompute paired final-ECE differences from the held-out JSON | verified |
| C11 | The 30-seed E4 archive gives uncalibrated/calibrated gamma_TV 1.081/0.749 and reductions of 30.765 percent (TV) and 29.348 percent (VT). | evidence/blocked-audit.json -> e4.uncalibrated_gTV / e4.calibrated_gTV / e4.gTV_reduction_pct / e4.gVT_reduction_pct | 1.081 / 0.749 / 30.765 / 29.348 | Recompute from the 30 per-seed E4 records | verified |
| C12 | The five-condition landscape reproduces r(H,gamma)=-0.989 and r(CV,gamma)=-0.916. | evidence/blocked-audit.json -> landscape.n / landscape.r_H_gamma / landscape.r_CV_gamma | 5 / -0.989 / -0.916 | Recompute Pearson correlations from the five complete triples | verified |
| C13 | Independent review is closed against the canonical hash with no open Critical or Major finding. | evidence/upstream/paper/REVIEW_CARD.md | open | Require a current-hash reviewer receipt; the retained review summary has 6 Major findings | blocked |
| C14 | This family currently has a package ready for upload. | evidence/variant-reconciliation.json -> package_created / uploaded | false / false | Check the package directory and upload receipts | blocked |
| C15 | The current canonical paper uses 6.61/2.95/2.22 and excludes the legacy 8.16/7.845/7.84/15.37 values. | evidence/blocked-audit.json -> structure.legacy_anova_counts_current.8.16 / structure.legacy_anova_counts_current.7.845 / structure.legacy_anova_counts_current.7.84 / structure.legacy_anova_counts_current.15.37 | 0 / 0 / 0 / 0 | Inspect the current source and the structural audit | verified |

## Summary

The current canonical manuscript is structurally cleaner and uses the reproducible
ANOVA subset, but the family remains blocked because the Face-1 CAF result and
the GPT-4o temporal decomposition lack raw carriers, the stored ANOVA block is
not derivable from its sessions, the source mirror carries legacy values, and no
current-hash independent review exists.
