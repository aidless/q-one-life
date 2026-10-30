# Review request: Paper 6 verifier capture

Review the overlay source at SHA-256
`fdfdb030c807bcb2d9c2bedec5281f4de6d8cc5710632bc75b58898742366331`.

The upstream review is still open with 7 Major and 12 Minor findings. The
current package is a cleaned synthetic benchmark, not a held-out deployment
study.

## Questions for the independent reviewer

1. Are the seven aggregation implementations faithful to their stated
   definitions, and are the synthetic attack generators the right
   operationalization of the threat model?
2. Does the recomputed per-seed table support the revised claim that majority
   is best or tied in S1--S3 and only 0.0076 below trust-mean in S4?
3. Is the local four-model, 20-question pilot informative enough to retain, or
   should it be moved fully to an appendix/descriptive note?
4. What held-out real-trace benchmark is required before the negative result
   can be stated beyond the synthetic generator?
5. Which tau and alpha values, if any, should be tested to establish
   hyperparameter robustness?
6. Is the N=5/N=7/N=10 sweep descriptive only, and does the N=10 trust-median
   gain invalidate the manuscript's monotone-trend language?
7. Are the theorem and proof appendix claims appropriately bounded or should
   they be removed entirely?
8. Do author, category, abstract, license and final release metadata remain
   user decisions?

## Requested decision

Return `scientifically-ready` only if every question has an artifact-bound
positive answer against the current source hash; otherwise return
`major-revision` with named evidence requirements or `blocked` if the missing
held-out evidence prevents review.

A successful compile or archive is not evidence of scientific readiness.
