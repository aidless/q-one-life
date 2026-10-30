# Research plan: Calibrating the Evaluator: Does Probability Calibration Mitigate Preference Coupling in LLM Agent Feedback Loops?

Paper ID: `qf-calibrating-the-evaluator-does-probabili-6544cd664a`
Validation: valid=`True`, ready=`False`

## Stages

| Stage | State | Notes |
|---|---|---|
| source-identity | candidate | The local source hash is checked; publication identity is separate. |
| claim-ledger | blocked | Claims must be registered and bound to evidence fields. |
| evidence-recomputation | blocked | Native gates passed: 0; bound to the current source: 0. A completed experiment is not a reproduced experiment. |
| citation-verification | verified | Passed citation gates bound to the current source: 1. |
| scientific-review | blocked | Open Critical or Major findings block the package. |
| arxiv-package | blocked | Mechanical packageability is separate from scientific readiness. |
| external-submission | locked | Upload, account use and publication require explicit user authorization. |

## Next actions

| Priority | Action | Owner | Done when |
|---|---|---|---|
| P0 | close_inconclusive_claims | agent | Each claim is verified, explicitly hedged with missing evidence, or removed. |
| P0 | close_scientific_review | agent | No open Critical or Major finding remains against the current hashes. |
| P0 | remove_or_repair_blocked_claims | agent | Blocked claims are absent from manuscript assertions or repaired. |
| P0 | repair_failed_native_gates | agent | Each failed gate is repaired or explicitly blocked in the manuscript scope. |
| P1 | build_bibliography | agent | Every citation resolves to a source record or is marked unresolved. |
| P1 | reproduce_required_numeric_claims | agent | Required numeric claims have a command, environment and matching output hash. |
| P1 | resolve_package_blockers | agent | The source tree, bibliography, compiled PDF and hashes are complete. |
| external | external_submission_gate | user | The user explicitly authorizes upload and checks metadata, license and author list. |

No submission action is implied by this plan.
