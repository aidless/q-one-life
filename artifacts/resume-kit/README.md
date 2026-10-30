# Q-One Resume Evidence Kit

This directory contains the local evidence used by the resume narrative. It is
not a public release receipt and not a scientific result.

## What was actually run

- Fresh dependency installation in a copied source tree at a colon-free path.
- Python: 178 pytest tests plus 32 subtests; 88 unittest tests.
- Desktop: 42 TypeScript unit tests.
- Electron E2E: 5 tests with a native PyInstaller sidecar and the pinned
  Qwen3-0.6B-Q8_0 model (2 core journeys, 2 benchmark modes, and screenshot
  capture).
- Resume benchmark: six fixed tasks, once with rule fallback and once with the
  local model.

## Research Factory evidence

This is a separate current check, not the historical desktop clean-room counts
above.

- Research tests: 92 pytest tests plus 22 subtests, and 90 unittest tests.
- Research Factory: 17/17 pilot overlays valid, 0 ready, 85 blocked claims and
  4 inconclusive claims; no paper is upload-authorized.
- Benchmark Noise Floor revision candidate R1: deterministic 45-page compile,
  353 ledgered numeric readings with 0 unbound, and 136/136 verdict-word checks.

Revision R1 is a construct-validity wording candidate only. C02 source identity
and C03 independent method review remain blocked/open, and the candidate does
not establish publication readiness.

## Benchmark boundary

Both modes matched all six target goals and produced trace-bound, actionable
recommendations. The rule path averaged 55 ms; the local-model path averaged
4,540 ms in this Linux CPU run. The Electron working-set readings were about
0.50 GiB and 0.94 GiB respectively.

These numbers are a small local engineering acceptance check. They do not show
real-world benefit, recommendation quality in general, retention, or scientific
validity.

## Reproduce

```bash
QONE_CLEANROOM_E2E=1 \
QONE_RUN_RESUME_BENCHMARK=1 \
QONE_CAPTURE_DEMO=1 \
QONE_SIDECAR_BIN=/absolute/path/to/qone-life-sidecar \
QONE_E2E_LOCAL_MODEL_PATH=/absolute/path/to/Qwen3-0.6B-Q8_0.gguf \
bash scripts/cleanroom-check.sh
```

The three flags above produce the five-test evidence run, including both
benchmark modes and screenshot capture. To rerun only the benchmark from the
resulting clean-room checkout:

```bash
QONE_RUN_RESUME_BENCHMARK=1 \
QONE_SIDECAR_BIN=/absolute/path/to/qone-life-sidecar \
QONE_E2E_LOCAL_MODEL_PATH=/absolute/path/to/Qwen3-0.6B-Q8_0.gguf \
node node_modules/@playwright/test/cli.js test e2e/resume-benchmark.spec.ts
```

Then rebuild the hash receipt:

```bash
python3 scripts/build_resume_evidence.py
sha256sum -c artifacts/resume-kit/SHA256SUMS.txt
```

Model SHA-256:
`9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031`.

## Explicit non-claims

- No public or signed desktop release.
- No three-platform clean-machine acceptance record.
- No arXiv submission or publication-ready paper.
- No end-to-end encryption claim for the working SQLite database.
- No claim that the six-task benchmark predicts real user outcomes.
