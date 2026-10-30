# Scope for P2-C9 - CV(N=5) and N=30 theorem quantities comparable

**Fixes**: P2-C9 blocked (sample size and estimator definitions) -> verified with hedge (harmonized)

## Hedged

- Original compared CV(N=5) from simulation vs CV(N=30) from theorem without harmonizing N, estimator: now hedged to "N=5 and N=30 are not directly comparable; theorem CV is asymptotic N->inf, simulation CV is finite N=5 with bootstrap; harmonized by reporting both N=5 and N=30 separately, not pooled"
- Estimator definitions: simulation CV via bootstrap of gamma_hat, theorem CV via delta-method lower bound -> harmonized as separate, not comparable

This closes C9 as verified (hedged, not pooled) for TMLR 5.
