# PAPER_PLAN.md — ARC-AGI-3 Attribution

Generated 2026-10-30. This file is the plan the draft already follows, reconstructed from the draft: it is a *reconciliation*, not a promise about work not yet done.

## What this paper argues

From the draft's own abstract, verbatim (source `ARC_REVISED.md`):

> This report studies attribution in an interactive competition where the submitted agent is evaluated on hidden games. We retain a three-submission lineage, pin its notebook bytes, and separate observed leaderboard differences from demonstrated component effects. Scores were 3.38, 4.01, and 4.24. The latter two submissions changed a per-game time limit and prefix caching, respectively. These are single observations, without a measured noise distribution. They establish a reproducible configuration lineage, but do not establish causal gains. We also correct two interpretation errors: partially completed games can receive credit, and an offline completion measure cannot be converted directly into the official action-efficiency score. Repeated visible-game evaluation and hidden scoring answer different questions; both need explicit records.

## Section plan, as the draft implements it

1. **Task and scoring** — the official scoring methodology; the correction that partial progress can earn nonzero credit (C09-inconclusive → requires official scorer fixture).
2. **Byte-pinned configuration lineage** — three submissions 3.38 → 4.01 → 4.24 (C01, C02, C06); adjacent differences +0.63 / +0.23 (C02).
3. **Offline evaluation and hidden scoring** — the offline completion measure is not a calibrated predictor (C07, C08, C09).
4. **Contribution verification and remaining experiments** — what the lineage does not establish (C11); the needed ablations.
5. **Limits and conclusion** — no rank/award claim (C03); published-state record (C04, C05); source identity (C10).

## How the numbers in it were checked

`validation_path: bounded_subset_rerun` — 1 printed number (3.08) re-derived; bound directly to `evidence/arc_lineage_audit.json -> observations[3].score` (submission 56820768 / date 2026-10-04 / notebook arc3-duck-7450-v1). 11 registered claims (C01-C11); C09 inconclusive (needs official scoring methodology snapshot + scorer fixture), all others verified.

## Evidence Record

- **live draft**: `ARC_REVISED.md` (local revision; differs from published source — see Notes)
- **published source recovered**: `source/ARC_PROPOSED.md` (SHA-256 `a1ff847e...d660`, hash-verified against receipt; C10)
- **Claim Ledger**: `CLAIM_LEDGER.md` (11 claims C01-C11)
- **evidence**: `evidence/claims_verified.json`, `evidence/arc_lineage_audit.json`, `evidence/publication_receipt_20261016.json`, `evidence/public_game_set.json`, `evidence/manuscript_identity_recovered.json`
- **validation_path basis**: `bind_numbers_tool.py --run` (re-executed)

## Notes for the drafting phase

- **C09 remains inconclusive**: no local snapshot of the official scoring methodology plus no official scorer fixture. The correction statement (partial progress can earn credit) depends on the official methodology; before it enters strong prose, the methodology snapshot and a scorer fixture must be recorded.
- **Source identity**: local `ARC_REVISED.md` is a different revision from the published source. The pilot's first-stage blocker is to resynchronize the local copy with the published source bytes.
- No new numeric claim without a registered evidence field.
- The "single observation, no causality" qualifier (C11) must stay attached to the +0.63/+0.23 differences.
