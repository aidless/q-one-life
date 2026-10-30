# Research pipeline

Canonical source:
`evidence/upstream/paper/main.tex`

Canonical SHA-256:
`379e1632302e979ded0c0462eeba32a07fa82653796ca72d4f9f55e46f8d5cec`

Current overlay source:
`source/main.tex`

| Stage | State | Required output |
|---|---|---|
| source-identity | candidate | Exact canonical, duplicate and superseded source hashes |
| claim-ledger | blocked | Fourteen claims separated into verified, candidate and blocked |
| evidence-recomputation | blocked | 176 carrier checks pass; proof and held-out gates remain |
| citation-verification | passed | All seven cite keys resolve to local bibitems |
| scientific-review | blocked | Independent proof and meta-review closure |
| arxiv-package | compiled | Deterministic three-file candidate archive |
| external-submission | locked | User metadata, license and upload authorization |

Unknown evidence is not converted to zero. A ready state requires every
applicable gate to pass against the same source hash.
