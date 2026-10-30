# Adversarial Review Summary — PAPER35 R16

## Verified

- The 100-scenario suite, four local checkpoints, three seeds, raw outputs, and
  BDS analysis are present and manifest-traceable.
- The manuscript explicitly states that local checkpoints are not temporal
  snapshots and that BDS is not a semantic metric.

## Major blockers

- Cross-model heterogeneity must not be presented as temporal/frontier drift;
  the current evidence has no calendar snapshots or API replication.
- BDS sensitivity to whitespace tokenization, top-K choice, smoothing, and
  response length needs an ablation or robustness analysis.
- Category-level bootstrap and Wilcoxon results need hierarchical dependence
  treatment and an explicit multiplicity plan.
- The multi-agent chain pilot is not a powered causal intervention and cannot
  establish amplification.
- Claims that the suite predicts future deployment drift require prospective
  validation and remain blocked.

## Verdict

Packaging and local reproducibility are substantially improved, but the paper
is not Strong-Accept-ready for broader drift or causal claims.

Canonical R16 rerun after ledger repair reports 11 PASS/0 FAIL/1 WARN in the
claim ledger, 0 stale markers, 0 inverted CIs, 0 statistical errors, 0 TMLR
failures, taint 0/0, and compile 0 errors. Four table/prose numeric mismatches
remain (including 0.0175 vs 0.017 and 0.0295 vs 0.03); compilation has nine
orphan labels and 26 uncited bibliography entries. These are in addition to
the substantive snapshot, metric-sensitivity, causal-pilot, and prospective
validation blockers listed above.

## R16 gate rerun 2026-08-19

- Current ledger verification: **11 PASS / 0 FAIL / 4 WARN**; taint **0/0**; scoped TMLR **0 failures**; statistics **0 error classes**; compile **0 errors**.
- Compile warnings remain 9 orphan labels and 26 uncited bibliography entries; four numeric table/prose mismatches remain. These are recorded as provenance/packaging work, not silently ignored.
- C08/C10/C11 remain blocked and C09 remains inconclusive. No frontier, temporal, causal-amplification, or prospective-deployment claim was promoted.

## Revision R17 (2026-08-19)

- Reconciled three of the four canonical table/prose precision mismatches: pooled cross-seed BDS `0.0173`, exact-zero notation `0.0000`, and the per-model upper bound `0.0295`. One residual `0.0175` vs `0.0173` alert is a model-row versus pooled-summary distinction and remains documented rather than silently normalized.
- Fresh compile succeeded (exit code 0; PDF generated in `sa_20260819_c`).
- Canonical evidence/protocol and three-seed raw outputs remain present. Frontier/temporal drift, BDS sensitivity, hierarchical multiplicity, causal-pilot power, and prospective validation blockers remain unchanged.
