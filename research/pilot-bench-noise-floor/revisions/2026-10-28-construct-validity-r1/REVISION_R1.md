# Noise Floor revision candidate R1

Generated: `2026-10-29T02:28:16Z`

## Status

This is an internal, evidence-bound revision candidate. It is not the canonical
manuscript, does not close the independent method review, and is not ready for
arXiv upload.

The candidate changes only construct-interpretation wording. It preserves the
original manuscript, all reported measurements, the calibrated arm, and the
previously reported disjoint-field deployment.

## Source identity

| Item | SHA-256 |
|---|---|
| Canonical overlay source (`source/main.tex`) | `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca` |
| Revision candidate (`revisions/2026-10-28-construct-validity-r1/source/main.tex`) | `842f7760f95aaa8bc3eb32fdc59933a54669157fd0b5e3a09f3375ea3ee12451` |
| Unified diff | `9352aa037213ed7998006c1fe52b641d1a29c7e6ce73f3a6e562e8a18a24a553` |

The canonical source still differs from the source named in the native
manifest. This candidate does not change that publication-identity state.

## What changed

- The abstract now says that a readable verdict is the positive branch of one
  producer-baseline rule, not that every resolvable ranking must pass it.
- The introduction no longer calls a readable verdict a necessary condition for
  citing a leaderboard. It states explicitly that the rule is neither necessary
  for every resolvable ordering nor sufficient for full ordering validity.
- The threat model no longer says a ranked table necessarily asserts that its
  top advantage exceeds producer reproducibility. It describes that as an
  invited reading that the audit tests only against one named baseline.
- The related-work and method sections now distinguish "a disjoint case was
  measured and refused" from "a disjoint case returned a positive verdict and
  remains unmeasured."
- The limitations section now says that no real leaderboard of the required
  shape returns a positive verdict in this paper, without denying that the
  disjoint-field deployment itself was measured.
- The conclusion states the conditional operation of the audit rather than
  asserting that every leaderboard has a floor that must be cleared to be
  meaningful.

The diff contains no new measured result and does not claim that the wording
change resolves bootstrap, k-fold support, threshold, or implementation-interface
objections.

## Evidence bindings

- The perfect-gold refusal is already present in the canonical source and is the
  direct logical witness against treating producer-baseline clearance as a
  necessary condition for every resolvable ordering.
- `experiments/producer-baseline-counterexample/results/reproduction.json`
  records two byte-identical accepted runs of an independent synthetic runner:
  `4e96412333a6634b5f3977fa71a447dd4e1cd743493aad113fabff98b3b6f84d`.
- That synthetic experiment is supporting evidence, not validation of the native
  implementation. Its positive control uses producer support that differs from
  the full leaderboard and therefore does not exercise the manuscript's domain
  gate.
- `evidence/source-lineage.json` recovers the manifest-named source blob but
  records `publication_identity_ready=false`.

## Verification

| Check | Result | Receipt SHA-256 |
|---|---|---|
| Mechanical package audit | PASS, 11 files, package `e8c168e73130a9f2f721e3c9b48fd2b80c3d0591732312007e46dc27e03df9f8` | `b43fcd7db57b0faf638a057345b75c2fdd2d5b2d6d3239d6f6bf1bd6a9bf8e8d` |
| Two-run clean-room compile | PASS, byte-identical 45-page PDF, SHA-256 `4c2b1bcfb4db4022c8f22423b446f2ae4ec7cf47d2a29e7e272a40f8e5e82442` | `febe768d78cd457d07b5164f76dfbb6a6f771304729216fd6c80df6d1a5332a7` |
| Ledger reverse coverage | 353 numeric readings, 350 bound, 3 allowlisted, 0 unbound | `e13e76b5d2b34b707d08e45f2355bb104344e10369cae5fc25794cf1651e024c` |
| Verdict-word gate | 136/136 checks pass | `cd698d4a423735ecb7211c26d4a98ccb528f6627fbce8cdb08c61a124b949aa6` |
| Ledger anchor census | GREEN, A1=0 | `3217e519c4ce1fa9247ed65b926cccd00b7223d14c5d17f9a5413469565aaf79` |

The native 250/250 number checker is evidence-to-carrier validation and is not
treated here as a candidate-specific prose check. The candidate-specific
reverse-coverage gate is the relevant check for changed manuscript wording.

## Superseded working drafts

The following earlier working files are preserved but are not accepted as the
revision candidate:

- `.qone-revision-proposal/proposal.md`
  `4eb88f8e821e2ea2b5b7ba6241f167db12768617587fa72b5127fa4dcedc3906`
- `.qone-revision-proposal/position.txt`
  `bd790dfb6225e8565ca38c7d608e8611c4261bc40e9db28dd56b9437eb39688d`
- `drafts/abstract-edit.md`
  `e5a7d5139d53b9f2b7006464b6009eade29aa437afa1252268d80a4f8ce3b2f5`
- `drafts/intro-edit.md`
  `566baca3ecbd212f7a74da840f5fcb8b21c4b8a4e76445395d1357115adbaa90`

Those drafts contain material errors: `READABLE` was described as a condition
for refusal; the existing real disjoint-field result was incorrectly replaced
with "pending"; passing text or compile gates were said to close an independent
scientific review; and arbitrary sample-size thresholds were proposed without a
power derivation. They must not be used as the paper's revision.

## Remaining blockers

- C02: the canonical overlay source is not byte-identical to the source recorded
  in the native manifest.
- C03: the independent method review remains open. This candidate addresses its
  A1 wording problem only.
- A2: fixed-winner versus reselected-winner bootstrap semantics remain unresolved.
- A3: the k-fold comparison still requires a common-support recomputation.
- A4: threshold equality, confidence-interval decision semantics, and the
  parameter/interface description remain unresolved.
- A real disjoint-field board that returns a positive verdict remains unmeasured.

No commit, push, arXiv upload, email, account change, author/license change, GPU
use, or paid action was performed.
