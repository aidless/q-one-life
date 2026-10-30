# PAPER_PLAN.md — Paper11 / Harness Selection

Generated 2026-10-30. This file is the plan the draft already follows, reconstructed from the draft: it is a *reconciliation*, not a promise about work not yet done. Where the disk has nothing, it says so.

## What this paper argues

From the draft's own abstract, verbatim (source `source/main.tex`):

> Harness evaluations often choose among candidate outputs and then report a score for the chosen candidate. The interface used to make that choice is part of the measurement: a selector may see the grader's score, one of several presentation orders, or both. We conducted a within-task \(2\times2\) audit on a frozen local benchmark, with three fixed candidate answers per task and four selection arms that crossed two orders with hidden or visible rubric scores. The audit used \DesignTasks{} tasks, a \GeneratorModel{} candidate generator, and a \SelectorModel{} selector.
>
> Exposing scores while holding order A fixed changed the selected candidate on \ScoreAChoiceChanged/\ScoreAChoicePairs{} tasks (\ScoreAChoiceRate; Wilson 95\% CI \ScoreAChoiceCI). ... The deterministic rubric most often could not distinguish the selected outputs: all three candidates tied on \AllTiedInstrumentTasks/\DesignTasks{} tasks. ... These results are a reproducible interface audit, not evidence that the rubric measures answer quality or that the observed rates generalise to other models and task populations.

## Section plan, as the draft implements it

1. **Introduction** — motivates the interface-as-measurement question; sets the within-task 2x2 audit framing; states scope limits (one sample, not generalisation).
2. **Related Work** — positions against harness-selection / evaluation-interfaces literature.
3. **Audit Design** — subsections: Frozen task and candidate pool (C01, C16); The 2x2 selection interface (C02, C20); Outcomes (C03-C08, C17-C19); Integrity checks (C13, C14, C15, C09, C10).
4. **Results** — subsections: Score exposure changes choices under both orders (C03, C04, C05, C06, C11, C12, C18, C19); Order changes choices even without scores (C07, C08, C18); Ties explain why a rubric delta can miss a choice change (C09, C10, C17).
5. **Discussion** — reads the measured rates as an interface audit; avoids quality-improvement inference.
6. **Limitations** — states open questions (generalisability, rubric-as-ground-truth) explicitly.
7. **Conclusion** — restates the audit scope.
8. **Data and Code Availability** — frozen sample, runner, analysis JSON, SHA-256.
9. **Reproduction Record** (appendix) — deterministic re-execution record.
10. **Claims Excluded from This Revision** (appendix) — C-register exclusions.

(10 sections, read from `source/main.tex`; the page floor and the section count are measured independently by `gates/page_standard.py`.)

## How the numbers in it were checked

`validation_path: bounded_subset_rerun` — 14 printed number(s) with no ledger entry were re-derived; 11 carry direct evidence (`evidence/paper11-matched-analysis.json` fields), 3 are non-data (model names / column width). All 20 registered claims (C01-C20) are `verified` in the Claim Ledger.

## Evidence Record

- **live draft**: `source/main.tex` (SHA-256 `9748c64cbd338dcc`)
- **Claim Ledger**: `CLAIM_LEDGER.md` (20 claims C01-C20, all `verified`)
- **frozen analysis**: `evidence/paper11-matched-analysis.json`
- **candidate manifest**: `evidence/candidate-manifest.json`
- **score recompute**: `evidence/score-recompute.json`
- **content-change analysis**: `evidence/content-change-analysis.json`
- **order contract**: `evidence/order-contract.json`
- **bibliography**: `source/references.bib`
- **validation_path basis**: `bind_numbers_tool.py --run` (re-executed)

## Notes for the drafting phase

- All claims that appear in prose are already bound to evidence fields in the Claim Ledger.
- No new numeric claim should be added without a registered evidence field (per D46-D60 constraint).
- The excluded-claims appendix (C-register "Remove" / "Exclude" rows) keeps the scope honest: position bias, rubric-as-ground-truth, and generalisation are explicitly not claimed.
