# Research pipeline

Source: `/home/liuzewen/F:\deepseek/agent-verifiability/manuscript/f-acceptance-arxiv/main.tex`
Source SHA-256: `4c59377876dfe6136c24dd016bca1111918e09a5ecbdf1a4109801795394f797`

| Stage | State | Required output |
|---|---|---|
| source-identity | candidate | Exact source hash and publication identity |
| claim-ledger | pending | Registered claims with evidence fields and recomputation |
| evidence-recomputation | pending | Reproduced numeric claims or explicit blockers |
| citation-verification | pending | Every citation resolved or marked unresolved |
| scientific-review | pending | Closed method, statistics, reproduction and writing findings |
| arxiv-package | pending | Clean source tree, bibliography, metadata and hashes |
| external-submission | locked | User authorization and account action |

Unknown evidence is not converted to zero. A ready state requires every
applicable gate to pass against the same manuscript hash.
