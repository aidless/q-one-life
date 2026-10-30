# Producer-baseline necessity counterexample

## Status

Reproduced. The two accepted runs are byte-identical.

- Manuscript: `182822cffdc2d754daef26894231e46c4ba4346f6b3f913215fe5263b2273aca`
- Preregistration: `ee9b2355387841012450be05d934e3402c85dfc9d346274ea8d5a1b5aa369e62`
- Runner: `b615e6dd785b853f0cb0eded1cbe7f6246de9809602353f9fa4dbb428e4a440e`
- Accepted run receipt: `fa0846484b4dba64236caf2aeefb2b70d3db8f6bab78b5ad1fe6067f289cd424`
- Reproduction receipt: `4e96412333a6634b5f3977fa71a447dd4e1cd743493aad113fabff98b3b6f84d`

## Decision

Reject the broad necessity claim in the declared synthetic condition:

> The producer-baseline gate can refuse a top ordering that is deterministic
> and stable under every single-item deletion. Therefore clearance of that gate
> is not a necessary condition for every resolvable top ordering.

## Results

| Condition | Producer floor | A | B | Gate | A-vs-B order | Stable single-item deletions |
|---|---:|---:|---:|---|---|---:|
| Critical | 1.000 | 0.900 | 0.500 | refused | A > B | 700 / 700 |
| Positive control | 0.800 | 0.900 | 0.500 | readable | A > B | 700 / 700 |
| Negative control | 1.000 | 0.500 | 0.900 | refused | A < B | 700 / 700 |

In the critical condition, A is correct on every item where B is correct.
There are 280 A-only correct observations and 0 B-only correct observations.
The exact one-sided sign-test tail under the declared item-exchangeability null
is `5.147557589468029e-85`.

## Interpretation boundary

This is a logical witness about the gate's construct interpretation. It is not
an estimate of how often real leaderboards have this pattern, not a new
measurement of model accuracy, and not evidence that the producer floor is
uninformative in every benchmark.

It does not close the manuscript's independent method review. It supports
narrowing the manuscript's claim and retaining the explicit perfect-gold
counterexample; it does not establish publication readiness, acceptance, or
arXiv authorization.

## Preserved failed attempts

- Attempt 1: implementation error before any measurement
  (`attempts/attempt-1-failure.log`).
- Attempt 2: positive-control floor was `2/3`, not the preregistered `0.8`;
  the runner did not yet compare exact numeric signatures
  (`attempts/attempt-2-protocol-failure.log`).
- Attempt 3: implementation was corrected, but the positive-control paired
  discordance was miscomputed as `70/0` instead of `280/0`
  (`attempts/attempt-3-protocol-failure.log`).
- Attempt 4: all frozen signatures matched and both runs were identical.

The failed attempts are not accepted as evidence.

## Reproduce

From this experiment directory:

```bash
python3 run_counterexample.py \
  --preregistration preregistration.json \
  --output results/run-1.json
python3 run_counterexample.py \
  --preregistration preregistration.json \
  --output results/run-2.json
cmp -s results/run-1.json results/run-2.json
sha256sum results/run-1.json results/run-2.json
```
