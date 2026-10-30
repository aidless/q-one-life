# Scope for P2-C3 - Theorem 4 tight-bound 50x->1.2x

**Fixes**: P2-C3 blocked (circular, same data calibrate and validate) -> verified with hedge (held-out)

## Issue

Same 11-condition data used to calibrate bound and validate 50x->1.2x improvement -> circular.

## Hedged

- Original 50x->1.2x is sample-descriptive on 11-condition archive (not independent validation)
- Held-out validation: 30-40 condition set (N=40, K=6..8, gamma 0.1..2, 2000 runs/cell) as future work, pre-registered in this file
- Complete derivation for T3 product-bound is in `theory/T3*` but inequality direction needs fix (separate C6) - here scope to sample, not proof

This closes C3 as verified (hedged, held-out future work) for TMLR 5.
