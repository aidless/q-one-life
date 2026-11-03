# A3 result: k-fold common support

Status: **accepted after two byte-identical runs**

## Frozen inputs

| Item | SHA-256 |
|---|---|
| Preregistration v1.0.0 | `bacdf9e09372d8382460a7712893989fb04a56d921fa3cddcf3cacbac2462133` |
| Runner | `9669db5401f31b10a450eafd0762ddd9bafdec77737a3d30a420ec85f977b012` |
| Run 1 | `93455b86334d9345f220b0e93b4a4067783f1ff0846d2af0bd93dac1695e6391` |
| Run 2 | `93455b86334d9345f220b0e93b4a4067783f1ff0846d2af0bd93dac1695e6391` |
| Native `audit.py` | `2fbb95fc6601c855e8df09df4bbd712883411d901209d5ee497cd73d7e23876b` |
| Native EC63 receipt | `f80712e34f86e71fd75d71d3c6224dfd0af466bccef244ae9c23cd31e6a62b50` |

The accepted outputs are byte-identical. The runner also validates the
unchanged native m25 carriers through `followup_common.validate_m25_arm` before
using any result.

## Support and result

`S_joint` is the intersection of the main gold, every generator's own LOO gold,
every generator's fold gold, and every generator/system answer row. Every floor
and leaderboard arm is scored on exactly that one set.

| Task | k-fold reported | all-LOO | joint | k-fold minus all-LOO | LOO margin on k-fold domain | LOO margin on joint | k-fold margin on joint |
|---|---:|---:|---:|---:|---:|---:|---:|
| factuality | 484 | 486 | 477 | 7 | +0.062544 | 0.0 | 0.0 |
| coherence | 404 | 445 | 383 | 21 | +0.471116 | 0.0 | +2.872063 |
| relevance | 978 | 987 | 974 | 4 | +0.005238 | 0.0 | +0.616016 |
| preference | 505 | 511 | 54 | 5 | +0.015384 | 0.0 | +1.851852 |

The number of generator/Loo-label pairs checked on `S_joint` is:

- factuality: 11,925 pairs, 0 mismatches;
- coherence: 9,575 pairs, 0 mismatches;
- relevance: 24,350 pairs, 0 mismatches;
- preference: 1,350 pairs, 0 mismatches.

The reselected-leader-minus-reselected-floor bootstrap identity is exactly zero
in 2,000 of 2,000 valid rounds for the LOO arm on every task. Its percentile
interval is `[0, 0]` throughout.

The k-fold arm on `S_joint` remains non-zero. Its coherence point margin is
`+2.872063`, with a 95% bootstrap interval of `[+1.308815, +4.545455]` and
2,000 positive rounds. This control shows that the support correction does not
mechanically force every margin to zero.

## Gates

| Gate | Result |
|---|---|
| F1 recorded leak reproduced | PASS |
| F2 LOO label identity on joint support | PASS |
| F3 joint-support margin zero | PASS |
| F4 bootstrap identity degenerate | PASS |
| F5 k-fold control has teeth | PASS |

## Interpretation

The coherence symptom named in the independent review is reproduced exactly:
leader `83.168317`, floor `82.697201`, margin `0.471116` on 404 k-fold items.
Once every generator is scored on the joint support, the same leader/floor
identity gives an exact zero LOO margin. Therefore the reported non-zero
`LOO_on_kfold_domain` margin cannot be used as evidence of a clean
k-fold-versus-LOO effect; its cause on these carriers is generator-specific
missing LOO gold and actor support.

This is a recomputation on four fixed m25 constructions. It does not establish
external validity, ranking validity, or publication readiness. The preference
joint support drops to 54 items because the ranked systems do not share a
larger common answer domain, so any preference comparison on this support is
descriptive only. The k-fold arm remains a different estimator and needs its
own explicit estimand and support statement in the manuscript.

## Reproduction

```bash
cd '<WORKSPACE_ROOT>/F:\deepseek/q-one-life/research/pilot-bench-noise-floor/experiments/kfold-common-support-a3'

<WORKSPACE_ROOT>/.cache/qone-life-venv/bin/python run_common_support.py \
  --external-root '<WORKSPACE_ROOT>/F:\deepseek' \
  --preregistration preregistration.json \
  --output results/run-1.json

<WORKSPACE_ROOT>/.cache/qone-life-venv/bin/python run_common_support.py \
  --external-root '<WORKSPACE_ROOT>/F:\deepseek' \
  --preregistration preregistration.json \
  --output results/run-2.json

cmp -s results/run-1.json results/run-2.json
```
