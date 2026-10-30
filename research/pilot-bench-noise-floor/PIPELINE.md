# Research pipeline

Source: `/home/liuzewen/WorkBuddy/2026-10-23-23-32-00/arxiv/bench_noise_floor/main.tex`
Source SHA-256: `971008d73d83b6b9d212bf0789987d8af84bfd92267974ecd706edccecc48d36`

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
