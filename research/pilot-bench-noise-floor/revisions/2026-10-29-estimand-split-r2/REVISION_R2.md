# Noise Floor revision candidate R2

Generated: `2026-10-29T04:16:47Z`

## Status

This is an internal, evidence-bound revision candidate. It is not the canonical
manuscript, does not close the independent method review, and is not ready for
arXiv upload. It is built on candidate R1 and changes two sentences; every
measurement already reported is preserved.

## Source identity

| Item | SHA-256 |
|---|---|
| Canonical overlay source (`source/main.tex`) | `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca` |
| Parent candidate R1 (`revisions/2026-10-28-construct-validity-r1/source/main.tex`) | `842f7760f95aaa8bc3eb32fdc59933a54669157fd0b5e3a09f3375ea3ee12451` |
| This candidate (`source/main.tex`) | `fc24f8effef7c6f90c6dca6a52ea967adcec60bf7b79408c817b3a8561930c0f` |
| Diff against R1 | `390e9d7f9a8f7c0e99705f5d102d074e7e221aa57d11adf21a209b5d241b6d62` |
| Diff against the canonical overlay | `a7ba05d9ceab85cd7e7564a3e7a50bce9f54e339a895886ffc8b44c307c891c8` |

The canonical source still differs from the source the native manifest names.
This candidate does not change that publication-identity state.

## What changed

1. **The margin interval is now labelled as one contrast, and the identity is
   proved to be resample-invariant.** R1 said the interval "is not an interval
   for the identity, which is exact at the point estimate and needs none". That
   leaves open whether the identity has any resampling uncertainty. The
   candidate states the deduction: a plurality leave-one-out reduction never
   re-labels an item, so on the shared domain each generator's ballot against
   the reduced gold and against the full gold coincide item by item; re-selecting
   the leader inside every draw as well as the floor therefore returns a margin
   of exactly zero, and the identity's own interval is the degenerate one at
   zero. The printed interval is the fixed-winner contrast and is not an estimate
   of the identity.
2. **A sentence the recomputation falsifies is corrected.** R1 said coherence is
   "the case where no round separates the two". The A2 recomputation records
   eight of two thousand case-clustered rounds in which the re-maximised floor
   sits strictly above the leader's column, so single draws do differ; the
   percentile interval still collapses because that count falls below the lower
   tail. The candidate now says that, instead of claiming no round separates.

## Evidence bindings

| Binding | SHA-256 |
|---|---|
| Pre-registration v2.0.0 (`experiments/bootstrap-estimand-a2/preregistration.json`) | `a58bf0b93419d4465c9b93b9f4e1ec055f9ba5f5cc31e21a85fa870fcf565484` |
| Frozen runner (`experiments/bootstrap-estimand-a2/run_estimand_split.py`) | `927143dd6727272311e67c4468d1bedaf131dc119d40546aae7c993d52b8d2d0` |
| Accepted run 1 (`experiments/bootstrap-estimand-a2/results/run-1.json`) | `4b0d65068f78015a4b5014f28e87b4d49b62db555d04598bee4e47cc5dade408` |
| Accepted run 2 (`experiments/bootstrap-estimand-a2/results/run-2.json`) | `4b0d65068f78015a4b5014f28e87b4d49b62db555d04598bee4e47cc5dade408` |
| Native rerun (`experiments/bootstrap-estimand-a2/results/native-rerun-factuality.json`) | `e9b7a6ec64cac431a647cc5e27ca027493127d992519c1d411e8c5d3dd90fa5c` |
| A2 report (`experiments/bootstrap-estimand-a2/results/REPORT.md`) | `86ea70406748878ea91dbde8d70b778cafb9e271789dc8e2ec957a17e2e2bca3` |

The two accepted runs are byte-identical. The native rerun is byte-identical to
the recorded `evidence/m25_factuality.json`, so the recomputation is on the same
generation of evidence.

## Verification

| Gate | Result | Receipt SHA-256 |
|---|---|---|
| Mechanical package audit | PASS, 11 files | `3921b0073d0eae29b037693e93046a6c577e0ed74afc89cc88fc39f42037ec5f` |
| Clean-room compile, two runs | PASS, 45 pages, byte-identical | `524d9f014298bc191a958aa50f6bfc1bd1fb420263ba194d7a8d1721cdca2d60` |
| Reverse numeric coverage | PASS, 353 readings, 0 unbound | `e13e76b5d2b34b707d08e45f2355bb104344e10369cae5fc25794cf1651e024c` |
| Verdict-word gate | PASS, 136/136 | `484adc31195305c68f3bda68d6c6065f833956935376c4fe5a957c57e3d5452b` |
| Ledger anchor census | GREEN, A1 = 0 | `3217e519c4ce1fa9247ed65b926cccd00b7223d14c5d17f9a5413469565aaf79` |

## Remaining blockers

- C02: the canonical source is not the source the native manifest names.
- C03: the independent method review remains open.
- A3: the k-fold common-support recomputation is not done.
- A4: threshold equality, the hard-coded delta, and the confidence interval's
  non-participation in the verdict branch are not resolved.
- Author metadata, licence, and the upload authorization are user decisions.

## Non-claims

- Compilation, gate passage, and a passing recomputation do not establish
  scientific readiness or peer-review acceptance.
- The A2 experiment splits an estimand; it does not validate the native
  implementation outside the exercised path and does not close A3 or A4.
- This candidate does not authorize an arXiv upload.
