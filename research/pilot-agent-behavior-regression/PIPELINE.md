# Research pipeline

Canonical source:
`evidence/upstream/paper/main.tex`

Canonical SHA-256:
`d1eac66806754899440a12bb30446c3944ed230191a077b1bbd331a2ae7a02f0`

Current overlay source:
`source/main.tex`

| Stage | State | Required output |
|---|---|---|
| source-identity | passed | Canonical, legacy, ingest, submission and backup hashes are reconciled |
| claim-ledger | blocked | Eleven claims separated; only C01 and C07 are verified |
| evidence-recomputation | blocked | Eight carriers pass; raw 1,200-cell recount is missing |
| citation-verification | passed | All 13 citation keys resolve to local bibitems |
| scientific-review | blocked | Independent method, BDS-sensitivity and hierarchical-inference review |
| arxiv-package | compiled | Deterministic nine-file candidate archive |
| external-submission | locked | User metadata, license and upload authorization |

Unknown evidence is not converted to zero. A ready state requires every
applicable gate to pass against the same source hash.
