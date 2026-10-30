# Independent review request - Paper 2

Date: 2026-10-27

Source under review:

- `evidence/upstream/paper/main.tex`
- SHA-256 `379e1632302e979ded0c0462eeba32a07fa82653796ca72d4f9f55e46f8d5cec`
- Overlay candidate: `source/main.tex`
- Overlay SHA-256 `7eb12d1302cf935ab8e19ea425c43da2e72daa89636fd3a5a1e0759bffab8b5d`

This is an internal scientific review request, not an acceptance decision.

## Required review tracks

1. **Method and proof**
   - Check the regularity conditions, unbiasedness requirement and positive
     gamma assumption in the conditional Cramer-Rao proposition.
   - Audit the first-order Delta-method variance statement for the empirical
     distance proxy and whether its error terms justify the reported N range.
   - Audit the conditional product bound, including the compact parameter space
     and positive entropy-floor assumptions.
   - Decide whether the corrected lower-bound direction is sufficient for the
     surviving theorem statements.

2. **Statistics and estimand**
   - Determine whether the measured weight-distance gamma can be identified
     with the logistic observation-model parameter in any defensible regime.
   - Reconcile the T7 scope statement (8/11 descriptive) with the frozen T7
     output (`n_all_constraints_satisfied=0`, `n_cells_tested=20`).
   - Check the relationship among five-seed CV, full-archive CV and confidence
     intervals.

3. **Empirical evidence**
   - Reproduce the GPT-4o drift table. The native scope note says `p=0.12`;
     the frozen replication JSON reports `p_bootstrap=1.0` and zero coupling
     for all eight seeds.
   - Confirm which condition rows and thresholds support the empty-region
     statement.
   - Treat the proposed 30-40 held-out condition set as absent until a dataset
     and run receipt exist.

4. **Reproducibility and publication metadata**
   - Check the seven local citations and the manual bibliography.
   - Decide what code, raw data and environment evidence can be asserted
     truthfully in the reproducibility statement.
   - Final author list, category, abstract, license and upload authorization
     remain user decisions.

## Required response

Return a finding list with severity, exact source location, evidence inspected,
whether the issue is local or fundamental, and a closure test. A model score
alone is not review closure.
