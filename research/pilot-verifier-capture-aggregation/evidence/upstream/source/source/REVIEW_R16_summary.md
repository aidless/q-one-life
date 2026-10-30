# Adversarial Review Summary — PAPER6 R16

## Critical

1. The paper previously claimed a 12-family empirical stress test without
   manuscript evidence. **Resolution:** scope the abstract and results to the
   canonical synthetic benchmark and explicitly descriptive local pilot.
2. The universal impossibility theorem and ATV guarantee are not established.
   **Resolution:** ledger them as blocked; remove universal wording and retain
   the failed proof only as a clearly labeled unresolved limitation.

## Major

- Add exact uncertainty intervals and a multiplicity policy for all scenario and
  attack-family comparisons.
- Complete model/version/environment provenance for the local pilot.
- Replace unpublished self-citation placeholders and add a real related-work
  comparison.
- Supply a held-out real-trace benchmark before making deployment claims.

## Current verdict

Machine checks can establish packaging and consistency, but the evidence gaps
above prevent a Strong Accept recommendation in this round.

Canonical R16 rerun confirms 0 stale markers, 0 inverted CIs, 0 statistical
errors, 0 TMLR failures, taint 0/0, and compile 0 errors/undefined references.
The claim ledger format was repaired to match the verifier's required six-column
schema; verification now reports 10 PASS, 0 FAIL, and 4 WARN (two inconclusive,
two blocked). However, 81 manuscript numeric literals still lack ledger-value
coverage, and compilation retains 13 orphan-label warnings. These remain
Strong-Accept blockers even though the formal packaging gates pass.

## R16 remediation rerun 2026-08-19

- Added `evidence/gaps/C09_generalization.md` and changed C09 from a missing `pilot only` path to an explicit inconclusive evidence record.
- Re-ran the canonical ledger and taint gates: **10 PASS / 0 FAIL / 4 WARN**, taint **0/0**. Scoped TMLR remains **0 failures**; statistics remain **0 error classes**; compile remains **0 errors** with 13 orphan-label warnings.
- The 81 uncovered numeric literals and 13 orphan labels remain open presentation/provenance work. C07–C08 remain blocked and C09–C10 inconclusive; no deployment or universal claim was promoted.
## Revision R17 (2026-08-19)

- Added `\setlength{\headheight}{14pt}` to remove the recurring fancyhdr head-height warning in the canonical manuscript.
- Fresh compile succeeded (exit code 0; PDF generated in `sa_20260819_c`).
- Fresh hallucination scan reports 0 citation/methodology/arithmetic errors; six strong-claim phrases and 107 uncovered numeric literals remain for evidence-ledger reconciliation.
- The abstract and discussion continue to scope the synthetic pilot, theorem, and local-model results; no universal impossibility or deployment claim was promoted.
- Theorem/guarantee blockers, generalization inconclusiveness, orphan labels, and provenance gaps remain.
