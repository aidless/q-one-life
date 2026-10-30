# Noise Floor revision candidate R4

Generated: `2026-10-29`

## Status

This is an internal, evidence-bound consistency candidate built on R3. It does
not replace the canonical manuscript, does not close the independent review,
and is not authorized for arXiv upload.

R4 responds to two read-only model-assisted reviews of frozen R3, which returned
`minor-revision` and `major-revision` respectively. The reviews are not external
human peer review and do not close C03. R4 makes the following scoped changes:

1. It removes the residual `>` wording for the point decision rule and states
   the same two equalities separately: leader-floor equality fails to
   `UNREADABLE`; after that gate, a margin at least `delta` enters `READABLE`.
2. It renames the "minimum detectable difference" prose to the observed 95% CI
   half-width resolution diagnostic, retaining `mde_median` only as a legacy
   field name, and removes the claim that low power reclassifies a point-branch
   token as `UNDECIDABLE`.
3. It corrects the A4 boundary wording from "exact-boundary fixture" to
   "serialized-boundary fixture": the raw margin is
   `2.0000000000000018`, serializes to `2.0`, and `READABLE`; the exact-`2.0`
   result is a branch deduction, not a separately executed fixture.
4. It replaces the current mixed-support k-fold reading at `+3.96` with the A3
   joint-support contrast `0.0 / +2.872063 / +0.616016 / +1.851852`, leaving
   `+3.96` historical only.
5. It narrows the remaining producer-baseline "bound" language to a named
   threshold on alignment with gold producers, not a statistical ranking-noise
   bound, and fixes the Goodhart sentence that attributed differences to
   systems versus labels.
6. It qualifies the calibrated arm as a separately preregistered
   interval-gated rule with a strict boundary, distinct from the point rule.
7. It qualifies joint intervals to same-domain margins and states that
   mixed-domain refusals have no inferential interval.

## Source identity

| Item | SHA-256 |
|---|---|
| Canonical overlay source (`source/main.tex`) | `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca` |
| Parent candidate R3 (`revisions/2026-10-29-support-threshold-r3/source/main.tex`) | `a9eef802faa6ef80f7916626a28aade11f1922701fb1f3b24b2f3780a69e0bb6` |
| This candidate (`source/main.tex`) | `fcafbeef57efbcad7db2f687dd4faac2f84e703dc429865fd7c7325de831433d` |
| Candidate ledger overlay | `dbfc8a5e5eff3bd9010027264a78367ab721d35cf1c55b42b8adc7a9c1894c51` |
| Candidate verdict registry overlay | `2eceff900846516d95dc3558331d9dde38fc718f992b87fd4cabc09e74ab3072` |
| Gate runner | `aa101385ea6cbda64587c248e6c05bf649ab9b4de5b24c5172204ca07bfe286c` |
| Reverse coverage | `51ae6aa7beab247e60ea613bde9d8e9a60255f269ddbe81aa2a41b18833f4702` |
| Anchor census | `39b66daff59bb4394e56ef5e8196d95849941ac8934c30f59cf920efa36d727c` |
| Verdict-word gate | `10dbc52e004a7a8caa422f2a23b89899d87d1be48223507bbe61c674d380eaaa` |
| Rule-consistency gate | `da6a74a3b162979461199d4771d586de72e1665c2e14e16f501b0d8aaaf242c8` |
| Combined gate summary | `20184c5482cd3581629f41e0ec33c7c8ddd6cb5a7bdc339f0bce94a2fb4f9622` |
| Clean-room compile receipt | `800b65257961d70c1f64a980049ca5bb78bf4856a5a461603fad1a0dcda3d293` |
| Candidate package archive | `aba2dc5ac9a04ebcce41f5c15050d325c0966d8aa653ae7eb6f67f217a3158ea` |
| Package receipt | `d1b442f65683224d5909bfc06a0da0ecec0d500abd7c3f8244ef12188ee2f4cb` |

The canonical source still differs from the blob named by the native manifest.
R4 does not change that publication-identity state.

## Verification

| Gate | Result |
|---|---|
| Reverse numeric coverage | PASS, 356 readings, 353 bound, 3 excused, 0 unbound |
| Anchor census | GREEN, 0 missing, 0 ambiguous |
| Verdict-word gate | PASS, 137/137 |
| Rule-consistency gate | PASS, 7/7; R3 negative control failed as expected |
| Clean-room compile | PASS, 46 pages, byte-identical PDF `8fc50c3d9819ec915c908f7503137a6a473a0c61144451db40821a58e6726906` |
| Deterministic archive | PASS, 11 files, `aba2dc5ac9a04ebcce41f5c15050d325c0966d8aa653ae7eb6f67f217a3158ea` |
| Extract-and-compile | PASS, 46 pages, PDF `8fc50c3d9819ec915c908f7503137a6a473a0c61144451db40821a58e6726906` |

The rule-consistency gate is a new negative-control-backed check. It requires
the frozen R3 source to fail on its residual wording and R4 to pass on all
seven declared-rule checks.

## Remaining blockers

- C02: the canonical source is not the source named by the native manifest.
- C03: the independent method review remains open.
- The calibrated arm remains an interval-gated preregistered variant, not
  evidence that the point rule is statistically sufficient.
- No real disjoint-field leaderboard returning a positive verdict has been
  measured.
- Author metadata, licence and upload authorization remain user decisions.

## Non-claims

- R4 is not the canonical manuscript and does not overwrite R3 or any prior
  revision.
- Compilation, hash binding, gate passage or the new consistency check do not
  establish scientific readiness, peer-review acceptance or publication.
- The A3 preference arm remains descriptive only; A4 remains synthetic
  interface evidence.
- R4 does not authorize an arXiv upload or external submission.
