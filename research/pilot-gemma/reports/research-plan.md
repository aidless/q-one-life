# Research plan: Your Tool-Selection Benchmark May Be Scoring Wrong Calls as Correct

Paper ID: `qf-your-tool-selection-benchmark-may-be-sco-85ad80aa80`
Validation: valid=`True`, ready=`False`

## Stages

| Stage | State | Notes |
|---|---|---|
| source-identity | blocked | The local source hash is checked; publication identity is separate. |
| claim-ledger | blocked | Claims must be registered and bound to evidence fields. |
| evidence-recomputation | pending | A completed experiment is not a reproduced experiment. |
| citation-verification | pending | A bibliography file is only a candidate until citations resolve. |
| scientific-review | pending | Open Critical or Major findings block the package. |
| arxiv-package | blocked | Mechanical packageability is separate from scientific readiness. |
| external-submission | locked | Upload, account use and publication require explicit user authorization. |

## Next actions

| Priority | Action | Owner | Done when |
|---|---|---|---|
| P0 | remove_or_repair_blocked_claims | agent | Blocked claims are absent from manuscript assertions or repaired. |
| P0 | resynchronize_published_source | agent | The exact source is recovered or the publication receipt is refreshed. |
| P1 | build_bibliography | agent | Every citation resolves to a source record or is marked unresolved. |
| P1 | reproduce_required_numeric_claims | agent | Required numeric claims have a command, environment and matching output hash. |
| P1 | resolve_package_blockers | agent | The source tree, bibliography, compiled PDF and hashes are complete. |
| external | external_submission_gate | user | The user explicitly authorizes upload and checks metadata, license and author list. |

No submission action is implied by this plan.
