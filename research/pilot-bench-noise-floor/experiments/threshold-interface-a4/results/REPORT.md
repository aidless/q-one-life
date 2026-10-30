# A4 result: threshold and interface semantics

Status: **accepted after two byte-identical runs**

## Frozen inputs

| Item | SHA-256 |
|---|---|
| Preregistration v1.0.0 | `de1cb0d656c92537444bd950fa8d357282f4ec13e489c6688f5413da9a48fabd` |
| Runner | `c996fc7b8be09ee8e0aaf58abfb1ecb86003a8e39bfa4b4ee3bcce5dcc456971` |
| Run 1 | `d2fedc88b0ae81f782c8169cfe8c66103871a389db644476a4b47735e049727c` |
| Run 2 | `d2fedc88b0ae81f782c8169cfe8c66103871a389db644476a4b47735e049727c` |
| Native `audit.py` | `2fbb95fc6601c855e8df09df4bbd712883411d901209d5ee497cd73d7e23876b` |
| Native HEAD | `ab40e28abcb2a97e13242d0dab5584d42a15f94e` |
| R2 candidate source | `fc24f8effef7c6f90c6dca6a52ea967adcec60bf7b79408c817b3a8561930c0f` |

The accepted outputs are byte-identical. The runner refuses to execute when
either its own hash or the pinned native audit hash differs from the
preregistration.

## Fixture results

| Fixture | Derived margin | Native margin | Native interval | Verdict | Purpose |
|---|---:|---:|---|---|---|
| `below_delta` | `+1.25` | `+1.25` | `[-0.25, +1.50]` | `MARGINAL` | exercise the sub-threshold branch |
| `equality_delta` | `+2.0000000000000018` | `+2.0` | `[0.0, +2.0]` | `READABLE` | reproduce the equality-branch mismatch |
| `above_delta` | `+20.0` | `+20.0` | `[0.0, +20.0]` | `READABLE` | exercise a clearly positive branch |
| `ci_crossing_zero` | `+13.6364` | `+13.6364` | `[-100.0, +21.1240]` | `READABLE` | test whether the interval gates the verdict |

Three fail-closed controls also pass:

| Control | Native verdict |
|---|---|
| system scored on 5 items while another system and the floor use 10 | `UNDECIDABLE_DOMAIN_MISMATCH` |
| two-generator leave-one-out floor | `UNDECIDABLE_FLOOR_DEGENERATE` |
| irreducible 2/2/1 vote on one item | `UNDECIDABLE_NO_READING` |

## Interface findings

The native CLI has no `--delta` option. Its help text exits zero, exposes
`--tie-rule`, and omits `--delta`; invoking `--delta 2.0` exits 2 with
`unrecognized arguments`. The pinned source contains the hard-coded branch and
metadata literal recorded in the preregistration, so 2.0 points is an
implementation convention rather than a configurable CLI contract.

The equality fixture derives a raw margin of `2.0000000000000018` points from
integer counts. The native JSON rounds that value to `2.0`, and the verdict is
`READABLE`. The decision branch is `margin < 2.0`, so a value of exactly 2.0
would also be `READABLE`. This conflicts with the R2 instruction that a reader
should treat equality as `MARGINAL`.

The CI-crossing fixture has a point margin of `+13.6364` and a 95% case
bootstrap interval of `[-100.0000, +21.1240]`, but the verdict remains
`READABLE`. The native output prints a warning after selecting the verdict; the
interval does not participate in the decision.

## Gates

| Gate | Result |
|---|---|
| F1 threshold is not a CLI parameter | PASS |
| F2 equality branch mismatch reproduced | PASS |
| F3 graded branch controls | PASS |
| F4 confidence interval is not gating | PASS |
| F5 fail-closed controls | PASS |

## Interpretation

The pinned tool and the candidate manuscript disagree on three observable
interface facts. The manuscript should be rewritten to state what the shipped
tool actually does, or the implementation must be changed before any R3
version can claim that the declared decision rule and executable rule are the
same. The duplicate R2 sentences that offer two competing repairs should be
collapsed into one policy in R3.

This experiment is synthetic and interface-focused. It does not show that an
interval-gated rule is statistically sufficient, does not resolve the
`m >= 3` independence caveat or the MDE terminology issue, does not measure an
external leaderboard, and does not make the paper scientifically ready.

## Reproduction

```bash
cd '/home/liuzewen/F:\deepseek/q-one-life/research/pilot-bench-noise-floor/experiments/threshold-interface-a4'

/home/liuzewen/.cache/qone-life-venv/bin/python run_threshold_interface.py \
  --external-root '/home/liuzewen/F:\deepseek' \
  --preregistration preregistration.json \
  --output results/run-1.json

/home/liuzewen/.cache/qone-life-venv/bin/python run_threshold_interface.py \
  --external-root '/home/liuzewen/F:\deepseek' \
  --preregistration preregistration.json \
  --output results/run-2.json

cmp -s results/run-1.json results/run-2.json
sha256sum -c SHA256SUMS.txt
```
