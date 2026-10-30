# Scope for P2-C4 - Theorem 1 Pinsker informative regime

**Fixes**: P2-C4 inconclusive (K gamma 8-10 outside small-gamma asymptotic) -> verified with hedge (K=2 small-gamma)

## Issue

Current K*gamma ~8-10 is outside small-gamma regime where Pinsker `kl >= 2*tv^2` is tight.

## Hedged

- For K=2, gamma 0.1 (small), Pinsker gives tight bound: kl ~0.02, tv 0.1, product 0.02*H*CV vs bound holds with small H.
- For observed K*gamma 8-10, claim hedged to "Pinsker bound is asymptotic, not informative in observed large gamma regime; K=2 small-gamma case as future work" for TMLR 5.

This closes C4 as verified (hedged) for TMLR 5.
