# PAPER6 Working Notes (R16)

## Scope

This round makes the submission evidence-first using the files already present
in `experiments/`. The canonical package distinguishes the synthetic main
benchmark, the synthetic pilot, and the local real-model pilot. The file
`main.tex.LLM_FABRICATED_DO_NOT_SUBMIT` is excluded from all evidence and text
scans.

## Decisions

1. The paper is an empirical synthetic benchmark plus a small local pilot, not
   a completed 12-family real-LLM stress test.
2. The universal impossibility language and the unproved ATV theorem are
   blocked. Claims are scoped to the tested parameterization.
3. The local pilot is descriptive only (20 questions, four local Ollama
   models, three seeds, two captured slots); it is not external validation.
4. Existing numeric claims remain only when traceable to canonical JSON files.

## Open blockers

- Complete proof or remove Theorem 2's claimed guarantee.
- Add a formal estimand and preregistered held-out real-trace evaluation.
- Add exact confidence intervals/effect sizes and a documented multiplicity
  policy for the scenario and attack-family comparisons.
- Add environment/model snapshot hashes and a complete release repository.
- Replace self-citation placeholders (`PAPER1`--`PAPER5`) with public records or
  remove the associated novelty claims.
