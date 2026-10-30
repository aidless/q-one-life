# Noise Floor revision candidate R3

Generated: `2026-10-29`

## Status

This is an internal, evidence-bound candidate built on R2. It does not replace
the canonical manuscript, does not close the independent review, and is not
authorized for arXiv upload.

`REVIEW_REQUEST_R3.md` is a frozen, self-contained review packet for this
candidate. It has not been sent to an external reviewer.

R3 makes four scoped changes:

1. It replaces R2's duplicate and mutually inconsistent equality instructions
   with one executable policy: the leader-floor margin must be at least the
   declared threshold.
2. It records that `delta = 2.0` is a hard-coded implementation constant, not a
   CLI parameter.
3. It records that the current implementation prints the interval after the
   verdict and does not gate on it.
4. It replaces the mixed-support k-fold comparison with the A3 joint-support
   result and labels the 54-item preference arm descriptive only.

## Source identity

| Item | SHA-256 |
|---|---|
| Canonical overlay source (`source/main.tex`) | `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca` |
| Parent candidate R2 (`revisions/2026-10-29-estimand-split-r2/source/main.tex`) | `fc24f8effef7c6f90c6dca6a52ea967adcec60bf7b79408c817b3a8561930c0f` |
| This candidate (`source/main.tex`) | `a9eef802faa6ef80f7916626a28aade11f1922701fb1f3b24b2f3780a69e0bb6` |
| Diff against R2 | `42e40ab0b040c12bb2982ca204aae464c41e15ecee7fa9d116e911d297ec6a14` |
| Diff against the canonical overlay | `0264a11ff93671948625934844fc993e2436a0bb1e9f6c1ffa570f0ea3503e40` |

The canonical source still differs from the blob named by the native manifest.
R3 does not change that publication-identity state.

## What changed

### Executable threshold policy

Equation `eq:rule` now states `leader - floor >= delta`. This matches the
pinned branch `margin < delta -> MARGINAL`, otherwise `READABLE`. The
manuscript states that `delta = 2.0` is a hard-coded implementation convention,
that `--delta` is rejected, and that re-thresholding stored margins is not the
same operation as passing a threshold option. The exact-boundary fixture is
bound to A4.

### Interval semantics

The manuscript no longer leaves it to inference that the interval is
non-gating. It reports the pinned behaviour and the A4 synthetic fixture with
point margin `13.6364`, interval `[-100.0, +21.1240]`, and verdict
`READABLE`. It explicitly says that an interval-gated policy would require a
new implementation and tests.

### Joint-support k-fold result

The old current-text reading of the mixed-support EC63 comparison is removed.
The retained historical lower endpoint is marked as context rather than as an
estimator contrast. R3 reports the A3 joint-support result: LOO margins are
zero on all four tasks, the bootstrap identity is zero in `2000/2000` rounds,
and k-fold margins remain non-zero on three tasks. The `54`-item preference
support is explicitly descriptive only.

## Evidence bindings

| Binding | SHA-256 |
|---|---|
| A3 preregistration v1.0.0 | `bacdf9e09372d8382460a7712893989fb04a56d921fa3cddcf3cacbac2462133` |
| A3 frozen runner | `9669db5401f31b10a450eafd0762ddd9bafdec77737a3d30a420ec85f977b012` |
| A3 reproduction receipt | `c2f1ebde69c98427acf685759e168b751700e7d88dff51c6221715d337d47b88` |
| A4 preregistration v1.0.0 | `de1cb0d656c92537444bd950fa8d357282f4ec13e489c6688f5413da9a48fabd` |
| A4 frozen runner | `c996fc7b8be09ee8e0aaf58abfb1ecb86003a8e39bfa4b4ee3bcce5dcc456971` |
| A4 reproduction receipt | `f98e5004bc953751f7a2c05c446206a87780af7202ad9acba77e62181c2a69a9` |
| Source-lineage receipt | `20a2abc52d3b38e313f821b8a51e511593170813e7a63066f11fe486c7d2b01a` |
| Independent review | `8d815000775ad110354043854967c79044605deb1f6113a549a6cba13078c86e` |
| R3 review request (not sent) | `b8eaf83c2e28da1b9f330b7a8a9d985b5e2f3e7329ec446acce5b043a2ceaae2` |
| Candidate ledger overlay | `7ff57a361f0a174e81ecf18652cadca9df7c9ee039ebf4a8917c36667f572fc3` |
| Candidate verdict registry overlay | `7f1c9b157edd4246811c61695b4899fc81c46e6417491293bfd8698d130c078d` |

The ledger and verdict overlays record the native base hashes and append or
re-window only the R3-specific readings. They do not modify the native paper
tree.

## Verification

| Gate | Result | Receipt SHA-256 |
|---|---|---|
| Mechanical package audit | PASS, 11 files, package `b375e087...ade6` | `26e8583840f2326b57c04c22ebad8a45123910f92df5e92fa03cc78193e7a588` |
| Clean-room compile, two runs | PASS, 46 pages, byte-identical PDF `439708174...396e` | `0254ad16dcb835138323a9567ad172d4eaf41cf527145d5c8625abb3ad47a39b` |
| Reverse numeric coverage | PASS, 355 readings, 352 bound, 3 excused, 0 unbound | `50bc1168961c0522ad80a9a56f47ee118bbd0fdb384d5cfda20724480b1712fd` |
| Anchor census | GREEN, A1 = 0, 0 ambiguous membership | `39b66daff59bb4394e56ef5e8196d95849941ac8934c30f59cf920efa36d727c` |
| Verdict-word gate | PASS, 137/137 | `10dbc52e004a7a8caa422f2a23b89899d87d1be48223507bbe61c674d380eaaa` |

The reverse, anchor and verdict reports were regenerated twice after the final
source bytes and were byte-identical across those runs.

## Remaining blockers

- C02: the canonical source is not the source named by the native manifest.
- C03: the independent method review remains open.
- The review's MDE terminology and generator-independence objections remain
  open; A3/A4 resolve only their named support and interface sub-questions.
- No real disjoint-field leaderboard returning a positive verdict has been
  measured.
- Author metadata, licence and upload authorization remain user decisions.

## Non-claims

- R3 is not the canonical manuscript and does not overwrite any prior revision.
- Compilation, hash binding and gate passage do not establish scientific
  readiness, peer-review acceptance or publication.
- The A3 preference arm is descriptive only.
- The A4 fixtures are synthetic interface evidence, not external leaderboard
  measurements.
- This candidate does not authorize an arXiv upload.
