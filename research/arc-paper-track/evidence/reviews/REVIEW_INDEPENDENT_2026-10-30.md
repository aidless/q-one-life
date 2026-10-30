# Independent Review: arc-paper-track / ARC-AGI-3 Attribution

Review type: method and statistics, read-only evidence review (scientific-reviewer subagent, 2026-10-30)

Reviewer: scientific-reviewer subagent (independent context, no prior)

## Frozen target

- Project: `research/arc-paper-track`
- Manuscript: `source/ARC_PROPOSED.md` (recovered published source)
- Claim Ledger: `CLAIM_LEDGER.md` (C01-C11; C09 inconclusive, out of scope)
- Evidence: `evidence/claims_verified.json`, `evidence/arc_lineage_audit.json`, `evidence/public_game_set.json`, `evidence/publication_receipt_20261016.json`, `evidence/arc_pins_verified.json`, `evidence/manuscript_identity_recovered.json`

## Per-claim verdicts

- **C01 supported** — arc_submissions[0/1/2] = {56637376, 3.38}, {56656333, 4.01}, {56691079, 4.24}, each fresh_pull_matches_receipt:true and distinct sha256. Ascending verified. (O1 wording tension)
- **C02 supported** — adjacent_differences=[0.63, 0.23]; recomputed 4.01-3.38=0.63, 4.24-4.01=0.23. Exact.
- **C03 supported** — 4.24; awarded_officially=false, final_official_top5=false. Manuscript correctly withholds rank/award.
- **C07 supported** (O2) — count=25, unique_count=25, all non-empty. Gateway half is platform-descriptive, not evidenced by JSON.
- **C08 supported** (O3) — same_source_version_score_span=0.93, noise_distribution_established=false; recomputed 4.01-3.08=0.93. Confounders named.
- **C11 supported** — causal_component_gain_established=false, noise_distribution_established=false, agent_evaluation_performed=false. Correlation vs causation separated.

## Overall verdict

**supported (6/6 reviewed claims), 4 observations to resolve, no refutations.** C09 remains inconclusive (out of scope).

## Issue list (preserved verbatim)

- O1 (C01): Manuscript §2 "this audit did not perform a fresh source pull" but claims_verified.json + arc_pins_verified.json both record fresh_pull_matches_receipt:true. Reconcile wording with evidence state; does not invalidate byte-identified lineage.
- O2 (C07): public_game_set.json documents only the offline side (25 unique IDs). "Hidden scoring uses a live gateway population" is platform-descriptive from §3, not independently evidenced by the JSON. Attribute as description, not evidenced numeric fact.
- O3 (C08): Byte-identity of 4.01/3.08 pair rests on both receipts recording same source digest + arc_lineage_audit shared source_version=353563241. No local SHA-256 for 56820768 present in reviewed evidence (only 3 primary submissions carry sha256). Span arithmetic exact; byte-identity for the 4th observation lacks local digest cross-check.
- O4 (scope/header): CLAIM_LEDGER.md header names ARC_REVISED.md as manuscript; review subject is recovered source ARC_PROPOSED.md. Consistent with C10 caveat (local a07872cc... != recovered a1ff847e..., matches_published_source=true), but ledger header should be updated to point at recovered source.
