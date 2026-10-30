# Independent review request: f-acceptance

Review type: method and statistics, model-assisted or human

## Frozen target

- Project: `research/pilot-f-acceptance`
- Manuscript: `source/main.tex`
- Source SHA-256:
  `986c0a3039e91dc31ad182a2fdaaba643454edd61407b8cfb280c64ef244d5ef`
- Upstream baseline: `evidence/upstream/main.tex`
- Upstream SHA-256:
  `4c59377876dfe6136c24dd016bca1111918e09a5ecbdf1a4109801795394f797`
- Candidate archive:
  `reports/package/f-acceptance-arxiv-candidate.tar.gz`
- Candidate archive SHA-256:
  `cf23a62a2c2066a934bea529b6aa97d993df0b78d048c42ceb6ce96620de213a`

## Required evidence

1. `CLAIM_LEDGER.md` and `reports/claim-ledger-verification.md`
2. `reports/native-verification-gate.json`
3. `reports/flip-disjointness.json`
4. `reports/review-response-audit.json`
5. `reports/cleanroom/receipt.json`
6. `reports/package/package-receipt.json`
7. Frozen JSON under `evidence/native/`
8. Historical review `evidence/reviews/FINAL_REVIEW_2026-10-26.md`

## Review questions

1. Does the 62,819-cell region and the two-sided exact reference implement the
   manuscript's stated estimand without circularity or post-hoc selection?
2. Are the 231 anti-conservative flips, 84-at-n<=200 count, alpha robustness,
   and maximum-error statements reproducible from the frozen formulas and data?
3. Does `reports/flip-disjointness.json` correctly establish that the 231
   uncorrected and 9 continuity-corrected cells are disjoint?
4. Does the 14-entry evolution-ledger rejudgment preserve the distinction
   between recorded decisions and recomputed exact decisions?
5. Are the public-code survey claims limited to the sampling frame and
   classification method rather than generalized to ecosystem prevalence?
6. Do the bibliography, limitations, data-availability language, and local
   review-response fixes match the current source?
7. Are there any remaining Critical or Major methodological, statistical,
   reproducibility, or writing defects?

## Output contract

- Write a read-only review report with severity, finding, evidence location,
  and exact requested revision.
- Bind the report to the source SHA-256 above.
- End with one disposition: `pass`, `minor-revision`, `major-revision`, or
  `blocked`.
- A model-assisted review does not establish human peer review, acceptance,
  publication, or upload authorization.

Do not modify the manuscript, package, project state, or external services.
