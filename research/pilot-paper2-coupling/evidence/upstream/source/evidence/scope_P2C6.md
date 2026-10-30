# Scope for P2-C6 - Theorem 3 product-bound proof direction

**Fixes**: P2-C6 blocked (H upper bound cannot yield product lower bound) -> verified with hedge (corrected direction)

## Issue

Original used H upper bound (max entropy) to lower bound product = |gamma|*H*CV -> direction wrong: upper H gives upper product, not lower.

## Hedged

- Correct: Use H lower bound h_min (at gamma_max=2.0) as in tmlr_p20 proof_cmin, not H upper bound.
- With h_min = 0.59-0.85 (K=3..5) and CV lower bound via sqrt(s_min(1-s_min))/sqrt(C(K,2)), product lower bound = h_min * ... / sqrt(N) as in tmlr_p20.
- Original proof gap hedged to "product lower bound holds with h_min, not H upper bound" for TMLR 5.

This closes C6 as verified (corrected direction, hedged) for TMLR 5.
