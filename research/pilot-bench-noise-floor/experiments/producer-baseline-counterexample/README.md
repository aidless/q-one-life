# Producer-baseline necessity counterexample

This directory contains a frozen synthetic witness for the construct-validity
issue raised in independent review finding A1.

The experiment asks one narrow question:

> Is clearing the producer-baseline gate a necessary condition for every
> deterministic, deletion-stable top ordering?

The critical construction has three perfect producers, so their leave-one-out
floor is 100%, and two external systems at 90% and 50%. The 90% system is
correct on every item where the 50% system is correct, the paired discordance
has 280 one-way and 0 reverse observations, and the ordering remains unchanged
after deleting any one of the 700 items. The declared gate nevertheless
refuses because no system exceeds the 100% floor.

Positive control: three producers have disjoint 100-item error blocks followed
by 400 common items, so each leave-one-out producer is scored on 500 defined
items and is correct on 400. Its floor is exactly 80%, a 90% candidate clears
it, and the same gate returns readable.

Negative control: the exact-producer construction is rerun with the candidate
order reversed; the runner must detect the reversed order and still refuse.

This is a logical counterexample, not an estimate of how often real
leaderboards behave this way. It does not show that a producer floor is always
uninformative, and it does not establish the scientific readiness of the
manuscript.

Run:

```bash
python3 run_counterexample.py \
  --preregistration preregistration.json \
  --output results/run-1.json
```
