# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: Three primary submissions form a byte-identified lineage from 3.38 to  :: evidence/claims_verified.json -> arc_submissions[0].ref / arc_submissions[0].score / arc_submissions[1].ref / arc_submissions[1].score / arc_submissions[2].ref / arc_submissions[2].score = [56637376, 3.38, 56656333, 4.01, 56691079, 4.24]
- PASS C02: The adjacent public score differences are +0.63 and +0.23. :: evidence/arc_lineage_audit.json -> adjacent_differences[0] / adjacent_differences[1] = [0.63, 0.23]
- PASS C03: The best recorded score in this lineage is 4.24, not evidence of a fin :: evidence/claims_verified.json -> arc_submissions[2].score = [4.24]; evidence/publication_receipt_20261016.json -> articles.arc-prize-2026-paper-track.awarded_officially = [False]
- PASS C04: The remote Kaggle Writeup is PUBLISHED and its submitted banner was ve :: evidence/publication_receipt_20261016.json -> articles.arc-prize-2026-paper-track.contentState / articles.arc-prize-2026-paper-track.submitted_banner_verified_after_update = ['PUBLISHED', True]
- PASS C05: The remote article was recorded at 1022 editor words and 1034 whitespa :: evidence/publication_receipt_20261016.json -> articles.arc-prize-2026-paper-track.editor_word_count / articles.arc-prize-2026-paper-track.whitespace_word_count = [1022, 1034]
- PASS C06: The 4.24 submitted notebook is pinned by SHA-256. :: evidence/claims_verified.json -> arc_submissions[2].sha256 / arc_submissions[2].fresh_pull_matches_receipt = ['e53788bed53c014951342d9c2517ee59137cfe820f73084f3892268c9be0bdc4', True]
- PASS C07: The offline public set contains 25 unique fixed game IDs, while hidden :: evidence/public_game_set.json -> count / unique_count / offline_length_assertion_present = [25, 25, True]
- PASS C08: A byte-identical source version spans 0.93 public score while no noise :: evidence/arc_lineage_audit.json -> same_source_version_score_span / noise_distribution_established = [0.93, False]
- PASS C09: Partial completion can receive nonzero credit, and an offline placehol :: INCONCLUSIVE status - needs hedge wording in prose + named missing evidence (evidence not verified by design)
- PASS C10: The exact remote source bytes recorded by the publication receipt (SHA :: evidence/manuscript_identity_recovered.json -> recovered_source_sha256 / matches_published_source = ['a1ff847e3361d8c6b2b21578e559baf5ab11d768c8f617bae97765691f9fd660', True]
- PASS C11: Single-rung score differences do not establish causal gains from the c :: evidence/arc_lineage_audit.json -> causal_component_gain_established / noise_distribution_established / agent_evaluation_performed = [False, False, False]

## Summary: 11 PASS, 0 FAIL, 1 WARN

## Inconclusive entries (hedge + name missing evidence): 1

## Numeric literals in text without any ledger value: 1
3.08