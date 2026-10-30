# A3 k-fold common support

This experiment tests independent review finding A3: the reported
`LOO_on_kfold_domain` margin is computed after restricting the k-fold floor and
leaderboard to one domain, but without restricting each generator to its own
defined LOO gold. Missing LOO gold is then dropped from that generator's
denominator.

The frozen runner rebuilds the four m25 vote tables, reproduces the recorded
k-fold and leaky LOO values, and recomputes both arms on:

```text
S_joint = main gold
          intersect every generator's LOO gold
          intersect every generator's k-fold gold
          intersect every generator and ranked-system answer row
```

Accepted output:

- `results/run-1.json` and `results/run-2.json` are byte-identical.
- Their SHA-256 is `93455b86334d9345f220b0e93b4a4067783f1ff0846d2af0bd93dac1695e6391`.
- All five preregistered gates pass.

The result is narrow: it identifies the reported non-zero LOO margin as a
support artifact on these fixed m25 carriers. It does not show that k-fold
restores ranking validity, does not close review finding A4, and does not
authorize an arXiv upload.
