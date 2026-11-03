# Research pipeline

Source: `<WORKSPACE_ROOT>/kaggle-control-20261013/paper-evidence/GEMMA_REVISED.md`
Source SHA-256: `aa25d33d83b55c4bff5716f2777f420b182122faf93b26a78694b5ce9c5ea798`

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
