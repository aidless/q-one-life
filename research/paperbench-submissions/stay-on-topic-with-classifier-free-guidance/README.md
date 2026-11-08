# Stay On Topic With Classifier Free Guidance — CFG inference slice

This submission is a Q-One minimal reference implementation for PaperBench task
`stay-on-topic-with-classifier-free-guidance`. It records the rubric categories, exposes a deterministic `run(data)`
interface, and has executable smoke tests.

## What now actually runs

- `src/cfg.py` implements Eq. 7 `gamma * logits_cond + (1 - gamma) * logits_uncond`
  with a mutable `gamma`, unconditional branch start at the last prompt token,
  shape/gamma validation, and the nine section-3.1 benchmark source contracts.
- `tests/test_cfg.py` adds 9 tests; full suite is 12 passed.
- `run.py` with `{"cfg_slice": {}}` runs the toy-logit slice.

## What is still not reproduced

GPT-2 / Pythia weights, ARC-c / ARC-e / BoolQ / HellaSwag / PiQA / SciQ /
TriviaQA / WinoGrande / LAMBADA zero-shot evaluation, Section 3.2 GSM8K/AQuA,
Section 4 FLOPs/VRAM, Section 5 entropy/perplexity, human preference study,
and any real PaperBench judge score. The nine benchmark manifests are marked
`available=false`. No claim of a PaperBench capability score is made.

Rubric leaves: 121. Categories: Code Development, Code Execution, Result Analysis.
Recurring rubric terms: ANCOVA, ARC-c, ARC-e, Across, Addendum, Appendix, B-mono, BoolQ.
