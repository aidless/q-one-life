# F4 verification blocked audit

Status marker: `agent-proposed, not human publication approval`

## Reproduces

- 270 pilot-grid cells across 10 seeds.
- Mean `0.249278`, population SD `0.028931`.
- 42/42 citations and 28 references resolve.

## Does not reproduce

- The paper declares 18,000 trials; 270 pilot cells are archived.
- Frozen evidence split files found: 0/4.
- F4 table rows disagreeing with their own b/c inputs: 4/8.
- Carrier gate: `tmlr-f4-verification: PASS=30 FAIL=0 NOT_VERIFIABLE=2 (total 32)
  NOT_VERIFIABLE          5  line attestation failed: position 13 of the cited line prints '-5', not '5' -- two cells of one row exchanged is what this catches
  NOT_VERIFIABLE          3  line attestation failed: position 12 of the cited line prints '-3', not '3' -- two cells of one row exchanged is what this catches`.
- Manifest: 19/32 entries match; 7 mismatch and 5 are absent.
- Canonical and arXiv author blocks differ: True.

## Consequence

The pilot summary can be retained as a bounded result. The 18k, frozen-split and 2700-hold claims cannot be packaged until the per-observation records, statistic derivations and author metadata are restored and independently reviewed.
