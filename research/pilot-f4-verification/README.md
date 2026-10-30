# Q-One research overlay: F4 Verification

Status marker: `agent-proposed, not human publication approval`

- Family: `qf-merged-flagship-f4-verification-trust-sc-88e8c3c2ce`
- Project: `qp-tmlr-f4-verification-08357385d7b0`
- Canonical SHA-256:
  `fa583f30f2e4ce1d36fdf69ec99b5b91a406a28b294e0ddb953bc29b95b80f46`
- Disposition: `blocked`
- Package: none
- Uploaded: no

## What is auditable

- One title, author block and end-document token; 15 unique labels and 28
  resolvable references.
- 42/42 citation keys resolve to the retained bibliography.
- The 270-cell pilot spans 10 seeds and reproduces `P_mean=0.2493`,
  population SD `0.0289`, and CI95 `[0.2458,0.2527]`.
- The pooled seed block is correctly recomputed from the primary carrier as
  `b=44`, `c=12`, `n_d=56`.
- The retained review is preserved rather than replaced or downplayed.

## Why the family is blocked

- The manuscript declares 18,000 trials, but the retained pilot has 270 cells.
- No explicitly named 192/144/90/40 frozen evidence bundle is present.
- The declared four GPU-hours have no per-family runtime carrier.
- The 2,700-hold, `0.686`, Friedman `0.002` and Nemenyi `1.47` headline values
  have zero machine-readable numeric hits.
- Four of eight F4 table rows disagree with their printed counts at the stated
  precision; two risk differences use a different denominator from the caption;
  and both copied Finance/Mimicry intervals exclude their own estimates.
- The manifest has 19 matches, 7 mismatches, 5 absent entries and 1 entry without
  a hash.
- The carrier gate is `PASS=30 FAIL=0 NOT_VERIFIABLE=2`; the two unverifiable
  rows are position-attestation failures, not passes.
- Printed BFCL/WebArena values disagree with both archived pilot and real40
  carriers.
- Canonical and arXiv variants carry different email/affiliation metadata.
- The native ledger is stale (`0.2502`, n=90) relative to the carrier (`0.2493`,
  270 cells), and no current-hash independent review exists.

No package was fabricated from declared but unarchived evidence.
