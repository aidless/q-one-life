# Bootstrap estimand split (independent review finding A2)

This directory holds a frozen, falsifiable recomputation for finding A2 of the
independent review: the margin bootstrap interval printed by the native tool and
the Proposition 4 zero-margin identity are **two different estimands**.

Two statistics share the same inputs and the same resampling draws:

| symbol | definition | what it answers |
|---|---|---|
| `theta_fixed(b)` | macro of the point-estimate winner (**fixed** across rounds) minus macro of the per-round best generator | "does this particular leader clear the pool?" |
| `theta_both(b)`  | macro of the **per-round best** leaderboard system minus macro of the per-round best generator | the Proposition 4 identity statistic |

Under Proposition 4's hypotheses the identity is *replicate-invariant*: a
plurality leave-one-out reduction never re-labels an item, so on the shared
domain `U` each generator's ballot against `c^-_g` and against `c` coincide, and
the two maxima are equal in **every** resampling round. The identity's own
percentile interval is therefore the degenerate `[0, 0]`; the printed interval
belongs to `theta_fixed` only.

## Result (four m25 carriers, 2,000 case-cluster rounds, seed 20261001)

| task | `theta_fixed` 95% CI | negative / zero rounds | `theta_both` |
|---|---|---|---|
| factuality | `[-3.9018, 0.0000]` | 1145 / 855 | 0 in 2000/2000 |
| coherence  | `[ 0.0000, 0.0000]` | 8 / 1992    | 0 in 2000/2000 |
| relevance  | `[-0.7071, 0.0000]` | 280 / 1720  | 0 in 2000/2000 |
| preference | `[-1.7309, 0.0000]` | 531 / 1469  | 0 in 2000/2000 |

`theta_fixed` is never positive in any round on any task: the frozen winner is
one of the terms in the per-round maximum, so its lower bound is produced by the
asymmetric selection, not by uncertainty about the identity.

Two preregistered controls break the hypotheses and must move the statistic, so
the `[0, 0]` degeneracy is not automatic:

| control | construction | `theta_both` 95% CI |
|---|---|---|
| non-producer leader | append a system that answers the plurality gold and is not a generator (scores 100.0 on `U`) | `[+3.2720, +7.3469]`, 2000/2000 positive |
| unranked generator | drop the recorded leader's system rows, keeping it in the gold pool | `[-2.6750, 0.0000]`, 766/2000 strictly negative |

## Fidelity

The runner re-derives the native statistic from the same inputs and reproduces
the recorded interval within `0.001` points on all four tasks. An unmodified
rerun of `audit.py` on the rebuilt tables reproduces
`evidence/m25_factuality.json` **byte for byte**
(`e9b7a6ec64cac431a647cc5e27ca027493127d992519c1d411e8c5d3dd90fa5c`), so the
recomputation is on the same generation of evidence, not a lookalike.

## Boundaries

- This splits the estimand. It does not argue that the native tool is wrong to
  print the fixed-winner comparison, only that the label must be split.
- It does not validate the native implementation outside the exercised path.
- It says nothing about the threshold semantics (`>=` vs `>`, the hard-coded
  delta, the CI not entering the verdict branch) — that is finding A4.
- It is not a manuscript result, a scientific-readiness claim, an acceptance
  claim, or an arXiv authorization.
- The two controls are experiment-internal constructions.

## Reproduce

```bash
python3 tools/bench-noise-floor/make_m25_votes.py --out-dir <votes-dir> --task all
python3 run_estimand_split.py --preregistration preregistration.json \
  --external-root <native-root> --votes-dir <votes-dir> --output results/run-3.json
cmp -s results/run-1.json results/run-3.json
```

The preregistration is `preregistration.json` (v2.0.0); superseded attempts are
preserved under `attempts/` with their failure logs and hashes.
