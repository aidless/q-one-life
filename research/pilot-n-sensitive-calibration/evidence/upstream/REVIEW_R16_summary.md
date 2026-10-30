# Adversarial Review Summary — RESAMPLING_CALIBRATION R16

## R16 gate rerun 2026-08-19

- Canonical ledger: **9 PASS / 0 FAIL / 3 WARN**; taint **0/0**; canonical scoped TMLR **0 failures**; statistics have **0 numerical error classes**.
- Same-line N warnings are table-header notation (N=200/500/1,000/2,000/5,000), not data-row contradictions; they remain recorded for scanner refinement.
- Compile remains 0 errors with six orphan labels. Numeric inventory is dominated by evidence tables/archives and needs scoped reconciliation before a clean full-tree number gate.
- Universal class-count law, arbitrary-domain generalization, NLL/UQ completeness, intermediate imbalance coverage, joint embedding-classifier-resampling design, and external replication remain blocked.

## Verified strengths

- Multiple datasets, embedding models, calibration estimators, resampling
  strategies, and seed-level JSON outputs are present.
- The manuscript acknowledges protocol sensitivity, dataset differences, and
  the distinction between calibration and sharpness.
- The pipeline documents a corrected held-out calibration workflow and reports
  paired tests for the resampling audit.

## Major blockers

1. The two studies use different datasets and protocols; cross-study synthesis
   must remain qualitative rather than causal or integrative.
2. The class-count pattern is based on a finite set of datasets and embedding
   checkpoints; it cannot support a universal law or arbitrary deployment
   recommendation.
3. Extreme Yeast imbalance drives the largest RUS effect, while intermediate
   imbalance ratios are missing.
4. NLL and other proper scoring rules are absent, so ECE-only conclusions are
   incomplete.
5. A joint embedding × classifier × resampling factorial and prospective
   external replication are still required for Strong Accept.

## Verdict

Evidence packaging is substantially improved, but the paper remains Major
Revisions for Strong-Accept purposes until the external and joint-design gaps
are addressed.

Canonical R16 rerun after ledger repair reports 9 PASS/0 FAIL/3 WARN in the
claim ledger, 0 inverted CIs, 0 TMLR failures, taint 0/0, and compile 0
errors/undefined references. The number scan has two stale markers (`0.047`,
`0.195`) and 33 table/prose differences. The stats scanner reports five
same-line N conflicts, all in multi-column table headers (N=500/N=5000 etc.)
rather than data rows; this is a notation-aware scanner limitation that should
be resolved or explicitly exempted. Compilation has six orphan labels. The
cross-dataset causal/generalization and missing NLL/QT gaps remain substantive.
## Revision R17 (2026-08-19)

- Removed six genuinely orphaned labels from canonical `main.tex` (`app:classwise`, `app:ece_comparison`, `app:master_table`, `sec:class_merge`, `sec:mechanism`, `sec:synthesis`).
- Fresh compile succeeded (exit code 0; PDF generated in `sa_20260819_b`) with no undefined references.
- Canonical protocol and multi-dataset/seed outputs remain present. Whole-tree citation and numeric scans include archival variants and evidence inventories; these are not treated as clean scientific coverage.
- Universal class-count law, arbitrary-domain generalization, NLL/UQ, intermediate imbalance, joint factorial, and external replication blockers remain.
