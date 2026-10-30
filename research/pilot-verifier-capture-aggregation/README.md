# Q-One research overlay: Paper 6 verifier capture

- Canonical upstream: `evidence/upstream/paper/main.tex`
- Canonical SHA-256:
  `42fe9b13f6a17af326f346aaa1afb7228fa1e8f4478126fadbce0fc7cea80cc3`
- Current overlay source: `source/main.tex`
- Current source SHA-256:
  `fdfdb030c807bcb2d9c2bedec5281f4de6d8cc5710632bc75b58898742366331`
- Status: `revision`
- Target: `arxiv`

The canonical source is retained byte-for-byte. The overlay removes unrelated
calibration and GPT-4o/GSM8K template text, duplicate reproducibility and
ethics blocks, the ATV proof placeholder, and unconditional claims that are
not supported by the frozen evidence.

## Current evidence

- The synthetic benchmark has 4 scenarios, 7 methods, 5 seeds, and 1,000
  rounds per cell.
- The aggregate table recomputes from the per-seed records.
- The one frozen numeric carrier receipt passes, including its printed source
  line.
- The local Ollama pilot has 20 questions, 4 model slots, 3 seeds, and 2
  captured slots; all seven methods recompute to 0.9167 mean accuracy.
- The candidate package contains 5 files and compiles reproducibly to 15
  pages; archive SHA-256 is
  `c0e51c1b59d278a6eaa5c54637ec33e37b907640c7232f41038f580b453c6103`.

## Hard blockers

- No held-out real-trace benchmark exists.
- The upstream evidence manifest has 11 missing entries.
- No per-cell tau or alpha hyperparameter sweep is present.
- Native C02 is contradicted in S4: trust-mean is 0.0076 higher than
  majority.
- The universal negative-result and ATV epsilon-resilience claims remain
  blocked.
- The upstream review has 7 Major and 12 Minor findings.
- Final author, category, abstract, license and upload authorization remain
  user decisions.

The archive is internal and is not upload-authorized.
