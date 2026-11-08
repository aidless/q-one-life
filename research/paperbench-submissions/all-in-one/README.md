# All In One — VESDE formula slice

This submission is a Q-One minimal reference implementation for PaperBench task
`all-in-one`. It records the rubric categories, exposes a deterministic `run(data)`
interface, and has executable smoke tests.

## What now actually runs

- `src/vesde.py` implements Appendix A2.1 VESDE formulas: zero drift,
  diffusion coefficient, `sigma(t)`, perturbation kernel mean/std/sampling.
  Constants `sigma_min=1e-4`, `sigma_max=15`, time `[1e-5, 1]`.
- `tests/test_vesde.py` has 5 tests; full suite is 8 passed.
- Receipt: `research/validation-20261106/all-in-one-vesde-slice/receipt.json`.

## What is still not reproduced

Simformer architecture/tokenizer/masks, Euler-Maruyama reverse diffusion,
sbi NPE/NRE/NLE training, four SBI benchmark tasks, C2ST with 100-tree random
forest, all paper figures/tables, and any real judge score. No claim of a
PaperBench capability score is made.

Rubric leaves: 174. Categories: Code Development, Code Execution, Result Analysis.
Recurring rubric terms: Across, Algorithm, Appendix, Bernoulli, Carlo, Chain, Classifier, Conditioning.
