# Research pipeline

Canonical source:
`evidence/upstream/paper/main.tex`

Canonical SHA-256:
`42fe9b13f6a17af326f346aaa1afb7228fa1e8f4478126fadbce0fc7cea80cc3`

Current overlay source:
`source/main.tex`

| Stage | State | Required output |
|---|---|---|
| source-identity | passed | Canonical, legacy, ingest, submission and backup hashes |
| claim-ledger | blocked | Eleven claims separated; universal claims blocked |
| evidence-recomputation | passed | 4 scenarios and 7 methods recompute from per-seed records |
| local-pilot-replay | passed | Descriptive 20-question, 3-seed recomputation |
| citation-verification | passed | All cited keys resolve |
| scientific-review | blocked | Upstream review and held-out validation |
| arxiv-package | compiled | Deterministic five-file candidate archive |
| external-submission | locked | User metadata and upload authorization |

Unknown evidence is not converted to zero. A ready state requires every
applicable gate to pass against the same source hash.
