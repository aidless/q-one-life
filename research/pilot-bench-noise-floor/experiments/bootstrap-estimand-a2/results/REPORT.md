# A2 report: the printed margin interval is not the identity's interval

Status: **accepted measurement** (preregistration v2.0.0, two byte-identical runs).
Date: 2026-10-28. Evidence: `results/run-1.json`, `results/run-2.json`
(`4b0d6506…`, identical), `results/native-rerun-factuality.json`
(`e9b7a6ec…`, byte-identical to the recorded native evidence).

## Question

The independent review (finding A2) states that the manuscript's zero-margin
identity and the non-degenerate bootstrap interval are not the same statistic.
The experiment separates them on the four real m25 carriers and asks which
estimand the printed interval belongs to.

## Result

1. **The identity is replicate-invariant.** Re-selecting the leader inside each
   bootstrap round as well as the floor returns a margin of exactly zero in
   2,000 of 2,000 rounds on every one of the four tasks. Its percentile interval
   is the degenerate `[0, 0]`. This is not an empirical accident: on the shared
   domain `U`, a plurality leave-one-out reduction never re-labels an item, so
   each generator's ballot against `c^-_g` equals its ballot against `c` item by
   item; the maximum over the ranked generating pool therefore equals the
   maximum over generators under **any** resampling weights.
2. **The printed interval is the fixed-winner contrast.** Holding the winner
   fixed and re-maximising the floor each round gives
   `[-3.9018, 0.0000]` (factuality), `[0.0000, 0.0000]` (coherence),
   `[-0.7071, 0.0000]` (relevance) and `[-1.7309, 0.0000]` (preference). These
   reproduce the recorded native intervals within `0.001` points.
3. **It can never be positive.** `theta_fixed` is `<= 0` in every valid round of
   every task, because the frozen winner is one of the terms in the per-round
   maximum. The negative lower bound is produced by the asymmetric selection.
4. **The degeneracy check can fail.** Adding a system that is not a generator
   (and scores exactly 100.0 on `U`) moves the same statistic to
   `[+3.2720, +7.3469]`; dropping the leader from the ranked field while keeping
   it in the gold pool moves it to `[-2.6750, 0.0000]` with 766 of 2,000 rounds
   strictly negative.

## What the manuscript already says, and what it does not

The canonical text already names the asymmetry ("a statement about a fixed
leader against a re-maximised floor") and already says the interval "is not an
interval for the identity". What it does not do is (a) argue that the identity is
invariant to resampling, so that the identity's interval is degenerate rather
than merely unprinted, and (b) carry a receipt for either claim. Both are now
available, so a revision can replace an assertion with a deduction plus a
recomputable carrier.

## Boundaries

This is a statement about two estimands on four fixed carriers. It does not
validate the native implementation beyond the exercised path, does not touch the
threshold semantics of finding A4, and does not establish publication readiness,
novelty, acceptance, or arXiv authorization. The controls are experiment-internal
constructions, not leaderboard measurements.
