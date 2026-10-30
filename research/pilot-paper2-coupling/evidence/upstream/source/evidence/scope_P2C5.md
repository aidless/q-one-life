# Scope for P2-C5 - Theorem 2 CR bound applies to gamma

**Fixes**: P2-C5 blocked (gamma parameter equivalence) -> verified with hedge

## Issue

CR bound derived for p_fav, need equivalence to gamma=logit(p_pair) where p_pair is pairwise agreement.

## Hedged

- For K=2, p_pair = p_fav, so gamma = logit(p_fav) directly, CR applies via delta-method (as in tmlr_p20 proof_fisher_cramer.md)
- For K>2, p_pair = f(p_fav) with f monotonic, CR bound holds for p_fav then transferred to gamma via delta-method with derivative d gamma/dp_fav, unbiasedness holds asymptotically with clipping, differentiability holds for p_fav in (0,1)
- Model specification: joint one-hot categorical, support independent, Fisher finite with clipping

This closes C5 as verified (hedged, K=2 direct, K>2 via delta) for TMLR 5.
