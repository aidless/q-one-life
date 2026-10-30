# ARC Paper Track Claim Ledger

Manuscript: `ARC_REVISED.md`

This ledger separates published remote state, local manuscript bytes, leaderboard
arithmetic, source-code configuration claims, and scientific interpretation.

| ID | Claim | Evidence file + field | Numeric values | Verification | Status |
|---|---|---|---|---|---|
| C01 | Three primary submissions form a byte-identified lineage from 3.38 to 4.01 to 4.24. | `evidence/claims_verified.json -> arc_submissions[0].ref / arc_submissions[0].score / arc_submissions[1].ref / arc_submissions[1].score / arc_submissions[2].ref / arc_submissions[2].score` | 56637376 / 3.38 / 56656333 / 4.01 / 56691079 / 4.24 | Re-run `paper-writing-agent/scripts/verify_claim_ledger.py`; compare fields and source hashes | verified |
| C02 | The adjacent public score differences are +0.63 and +0.23. | `evidence/arc_lineage_audit.json -> adjacent_differences[0] / adjacent_differences[1]` | +0.63 / +0.23 | Recompute adjacent score subtraction and verify with the ledger script | verified |
| C03 | The best recorded score in this lineage is 4.24, not evidence of a final top-five rank or award. | `evidence/claims_verified.json -> arc_submissions[2].score; evidence/publication_receipt_20261016.json -> articles.arc-prize-2026-paper-track.awarded_officially` | 4.24 | Recheck score field and award receipt; no rank or award claim is permitted | verified |
| C04 | The remote Kaggle Writeup is PUBLISHED and its submitted banner was verified. | `evidence/publication_receipt_20261016.json -> articles.arc-prize-2026-paper-track.contentState / articles.arc-prize-2026-paper-track.submitted_banner_verified_after_update` | - | Inspect the authenticated publication receipt and preserve its file hash | verified |
| C05 | The remote article was recorded at 1022 editor words and 1034 whitespace words, below the 1500-word limit. | `evidence/publication_receipt_20261016.json -> articles.arc-prize-2026-paper-track.editor_word_count / articles.arc-prize-2026-paper-track.whitespace_word_count` | 1022 / 1034 | Recompute word counts from the exact remote source when it is recovered | verified |
| C06 | The 4.24 submitted notebook is pinned by SHA-256. | `evidence/claims_verified.json -> arc_submissions[2].sha256 / arc_submissions[2].fresh_pull_matches_receipt` | - | Hash the pulled notebook and compare it with the authenticated receipt | verified |
| C07 | The offline public set contains 25 unique fixed game IDs, while hidden scoring uses a live gateway population. | `evidence/public_game_set.json -> count / unique_count / offline_length_assertion_present` | 25 / 25 | Parse the submitted notebook, count the tuple, and rerun the evidence generator | verified |
| C08 | A byte-identical source version spans 0.93 public score while no noise distribution was established. | `evidence/arc_lineage_audit.json -> same_source_version_score_span / noise_distribution_established` | 0.93 | Compare the repeated submission scores and inspect the no-noise-evidence flag | verified |
| C09 | Partial completion can receive nonzero credit, and an offline placeholder parquet is not evidence that the hidden competition ran. | - | - | Missing: a local snapshot of the official scoring methodology plus an official scorer fixture. Upgrade after recording both and running the fixture | inconclusive |
| C10 | The exact remote source bytes recorded by the publication receipt (SHA-256 `a1ff847e...d660`) have been recovered as `source/ARC_PROPOSED.md` and hash-verified. The local `ARC_REVISED.md` remains a different revision. | `evidence/manuscript_identity_recovered.json -> recovered_source_sha256 / matches_published_source` | - | Verify `source/ARC_PROPOSED.md` against the receipt hash; this proves source lineage, not that the local copy is the published manuscript | verified |
| C11 | Single-rung score differences do not establish causal gains from the configuration changes or bundled agent repairs. | `evidence/arc_lineage_audit.json -> causal_component_gain_established / noise_distribution_established / agent_evaluation_performed` | - | Require repeated isolated ablations with fixed model, harness and serving configuration; one score per rung is insufficient | verified |

## Strong Assertion Review

| Assertion | Evidence scope | Permitted wording | Decision |
|---|---|---|---|
| The lineage is reproducible and byte-identified | Submission receipts cover the three source notebooks | "The lineage is byte-pinned" | Keep |
| Time limit and prefix caching caused the gains | One public score per configuration, no repeated controls | "Observed score differences are +0.63 and +0.23" | Do not claim causality |
| The agent-loop repairs caused the gains | Repairs were bundled into the replicated configuration | "The ladder does not isolate the repairs" | Keep the limitation |
| Offline completion can predict hidden score | Different game populations and units; no calibrated mapping | "Offline completion is not a calibrated predictor" | Keep negative limitation |
| The local copy is the published manuscript | Local and remote source hashes differ | "The local copy must be resynchronized" | Block until repaired |
