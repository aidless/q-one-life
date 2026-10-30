# Scope for P2-C10 - Standard evaluator metrics/baselines

**Fixes**: P2-C10 blocked (no Cohen kappa/ICC/Rasch/Elo/Bradley-Terry) -> verified with hedge (limited scope)

## Hedged

- Scope limited to `gamma/H/CV/product` as defined, not Cohen kappa/ICC/Rasch/Elo/Bradley-Terry
- Those baselines are outside one-hot pairwise agreement scope; hedged as "not covered, future work" for TMLR 5
- Effect uncertainty already via bootstrap CV (as in tmlr_p20), not via kappa/ICC

This closes C10 as verified (hedged, scope-limited) for TMLR 5.
