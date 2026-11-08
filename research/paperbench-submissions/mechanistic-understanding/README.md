# Mechanistic Understanding — partial reproduction slice

This submission is a Q-One minimal reference implementation for PaperBench task
`mechanistic-understanding`. It records the rubric categories, exposes a deterministic `run(data)`
interface, and has executable smoke tests.

## What now actually runs

- `src/pipeline.py` reads the verified public Jigsaw `train.csv` (159,571 rows,
  68,802,655 bytes, SHA-256 `bd4084611bd27c939ba98e5e63bc3e5a2c1a4e99477dcba46c829e4c986c429d`).
- Deterministic hash-based 90:10 split: 143,614 train / 15,957 validation.
- `softmax(Wx)` binary probe via `LogisticRegression` on TF-IDF features.
  Measured validation accuracy **0.9595**. This is a word n-gram toxicity
  classifier, **not** the paper's GPT-2 residual-stream probe; the number must
  not be reported as the paper's ~94% result.
- `run.py` with `{"limit": 200}` runs a fast smoke slice; without `limit` it
  runs the full split. `tests/test_pipeline.py` adds 4 tests (7 total).

## What is still not reproduced

GPT-2 residual-stream features, DPO fine-tuning, PPLM pair generation,
24,576 continuation pairs, SVD toxic vectors, layer-wise " shit" probability,
the paper's tables/figures, and any real PaperBench judge score. The submission
is still `architecture_stub` for those leaves. No claim of a PaperBench
capability score is made.

Rubric leaves: 96. Categories: Code Development, Code Execution, Result Analysis.
Recurring rubric terms: Appendix, GPT-2, Gaussian, However, Jigsaw, Precision, RMSProp, RealToxicityPrompt.
