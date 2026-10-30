# Independent Review: pilot-gemma / WRITEUP.md

Review type: method and statistics, read-only evidence review (scientific-reviewer subagent, 2026-10-30)

Reviewer: scientific-reviewer subagent (independent context, no prior)

## Frozen target

- Project: `research/pilot-gemma`
- Manuscript: `source/WRITEUP.md`
- Claim Ledger: `CLAIM_LEDGER.md` (C01-C04)
- Evidence: `evidence/toolselect_replay_audit.json`, `evidence/toolselect_recompute.json`, `evidence/toolselect_cross_model_analysis.json`

## Per-claim verdicts

- **C01 supported** — archive_rows=450; per_k scored_correct sum (24+60+36)=120 = recorded_substring_positives sum (24+60+36)=120. Dual-source consistent.
- **C02 supported** — whole_identifier_observed sum (18+48+30)=96; fully_recorded_longer_name_discrepancy sum (0+12+0)=12; unresolved_truncated_record sum (6+0+6)=12. Internal per-tier self-consistency holds.
- **C03 supported** — distinct_registry_record_pairs=75 (=5+20+50); each signature_multiplicities=[6]; rows/multiplicity=registry_size self-consistent.
- **C04 supported** — rows=48; qwen flat_contract_tool_correct=22, arguments=21; llama tool=10, arguments=7. Correct per cross_model_analysis.json indexing.

## Overall verdict

**supported (4/4)**. No refuted/needs-work/unverifiable claims.

## Residual observations (non-blocking)

1. [low] Evidence file model array order differs between `toolselect_replay_audit.json` (fresh_probe.models=[llama,qwen]) and `toolselect_cross_model_analysis.json` (models=[qwen,llama]). C04 indexes correctly (cross_model_analysis.json); future scripts should locate models by name field, not position.
2. [informational] C01's 120 verifiable from two independent sources (recompute + replay_audit), no conflict.
3. [informational] 12 discrepancies = 2 distinct signatures × 6 repeats; 12 unresolved = 2 × 6. Manuscript correctly says "two distinct preserved signatures, not twelve distinct observed failure mechanisms".
4. [informational] manuscript_identity_recovered.json confirms source/WRITEUP.md matches published source hash (2ad3ce3d...92d8); local GEMMA_REVISED.md is a pre-publish draft (aa25d33d...). Consistent with ledger's Strong Assertion Review note.
