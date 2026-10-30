# Numeric carrier audit

Status marker: `agent-proposed, not human publication approval`

- Upstream carrier tool: `PASS=7 FAIL=0 NOT_VERIFIABLE=0`
- R1 per-seed records: 90
- R1 paired contrasts: 9
- v4-flash cells: 18
- Round-4 aggregate: 1,080 files / 36 cells / n=30

The R1 contrast means, t-statistics, p-values and paired effect sizes recompute
from the retained per-seed file. The v4-flash selected cell means and Round-4
reversal aggregate also match their retained artifacts.

The carrier tool result does not cover every exploratory value: its manifest has
seven rows and several manuscript values remain missing or header-only. This is
recorded as a package blocker rather than repaired by inference.
