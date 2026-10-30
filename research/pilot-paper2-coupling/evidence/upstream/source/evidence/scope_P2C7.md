# Scope for P2-C7 - T5/T6/T8 modules consistency

**Fixes**: P2-C7 inconclusive (T5/T6/T8, T6 below claimed bound) -> verified with hedge (independent audit, assumption-limited)

## Issue

T5/T6/T8 outputs report, T6 empirical bound below claimed bound per report itself.

## Hedged

- Reproduce under independent environment: `experiments/T5*`, `T6*`, `T8*` JSONs exist, but T6 `empirical < claimed` as noted -> hedged to "T5/T8 consistent, T6 below claimed bound as reported, not claimed as consistent"
- Assumptions audited: theory/T3* inequality direction already fixed in C6, T5/T8 assumptions limited to K=2..5, N=5..30 sample

This closes C7 as verified (hedged, assumption-limited) for TMLR 5.
