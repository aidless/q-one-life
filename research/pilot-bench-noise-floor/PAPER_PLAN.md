# PAPER_PLAN.md — Benchmark Noise Floor

Generated 2026-10-30. This file is the plan the draft already follows, reconstructed from the draft: it is a *reconciliation*, not a promise about work not yet done.

## What this paper argues

From the draft's own abstract, verbatim (source `source/main.tex`):

> When a benchmark's labels come from language models, the label producers could compete in the ranking they defined. We treat a gold generator's leave-one-out score as a *noise floor*: under a plurality convention it is the maximum over generators, and a leader is readable only if it clears that floor by a stated margin. The floor belongs to how the gold was defined, so it must be measured before a ranking is cited. No public board measured here clears that rule: the contribution is the refusal semantics, the three rulers, and the measurements that force the refusal, not a demonstration that a public ranking is readable.
> ...
> We release the measurement, three rulers with an explicit refusal when the annotations fail to support the quantity requested, a construction on which the same instrument pins every arm at a margin of zero, and a mutation battery that measures how much of our own test suite can fail.

## Section plan, as the draft implements it

1. **Introduction** — the noise-floor framing; the contribution as refusal semantics + three rulers + measurements.
2. **Threat Model** — conditions under which the floor must be measured (plurality aggregation, gold pool subset of ranked field).
3. **Related Work** — positions against leaderboard/annotation literature.
4. **Method** — the three rulers (leave-one-out over model gold; median-annotator substitution for human gold; latent Dawid-Skene arm).
5. **Measurements** — the five readings on public corpora, construction, released panel (C09, C11, C12, C13).
6. **The Estimator Is Not the Evidence** — the refusal semantics and why the floor is an identity on some pools.
7. **Artifacts and Reproduction** — release of tool + test suite (C05, C07, C08).
8. **Limitations** — the gap between estimator and evidence, external validity.
9. **Conclusion** — the measurable refusal on all measured corpora.

## How the numbers in it were checked

`validation_path: bounded_subset_rerun` — 485 printed numbers re-derived; 482 bound (99.4%), 1 non-data, 2 residual (model names / interval endpoints). 14 native ledger entries (C01-C14), all verified except C02/C03 (blocked by publication identity / construct validity — see Notes).

## Evidence Record

- **live draft**: `source/main.tex` (SHA-256 `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`)
- **native manifest source**: SHA-256 `0d68bda378fa0fc4fe1d39c8c8d46ba39052230fae7a1e8f2fd44b41e5b7e113` (C02: publication identity not established)
- **Claim Ledger**: `CLAIM_LEDGER.md` (14 entries C01-C14)
- **experiments**: `experiments/producer-baseline-counterexample/` (C09), `experiments/bootstrap-estimand-a2/` (C11), `experiments/kfold-common-support-a3/` (C12), `experiments/threshold-interface-a4/` (C13)
- **independent review**: `evidence/REVIEW_INDEPENDENT_2026-10-24.md` (C03/C04 — A1 construct-validity open)
- **validation_path basis**: `bind_numbers_tool.py --run` (re-executed)

## Notes for the drafting phase

- **C02 (source identity) and C03 (construct validity) remain blocked.** The paper's claims that depend on them must not enter strong prose as closed. The drafting phase should keep the refusal semantics and the measured refusals as the core contribution; the producer-baseline construction and the released-panel calibration are reported with their conditions explicit.
- No new numeric claim without a registered evidence field.
- The withdrawn-figures appendix keeps the honest scope.
