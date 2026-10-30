# Claim ledger verification report

Ledger: `CLAIM_LEDGER.md`
- PASS C01: The family has four packet source versions plus one source mirror, all :: evidence/variant-reconciliation.json -> variant_count / distinct_hashes / packet_variant_count / additional_variant_count = [5, 5, 4, 1]
- PASS C02: The overlay has one title, author block, end-document token, 24 unique :: evidence/native-audit.json -> structure.labels / structure.references / structure.citation_keys = [24, 26, 35]
- PASS C03: The R1 evidence contains 90 per-seed records and nine predeclared arch :: evidence/native-audit.json -> r1.records / r1.contrast_count / r1.n_seeds_per_contrast = [90, 9, [10]]
- PASS C04: The R1 Summarization-vs-Append-Only p=0.8 contrast is 0.0727 in favor  :: evidence/native-audit.json -> r1.canonical_r1_contrast.mean_diff_a_minus_b / r1.canonical_r1_contrast.t / r1.canonical_r1_contrast.p_raw / r1.canonical_r1_contrast.d_z = [0.07267473904552715, 3.7252353785030614, 0.004732175701544176, 1.1780228616309127]
- PASS C05: At p=0.2 RAG-vs-Append-Only has mean difference 0.1171, t=3.050, d_z=0 :: evidence/native-audit.json -> r1.contrasts[0].mean_diff_a_minus_b / r1.contrasts[0].t / r1.contrasts[0].d_z / r1.contrasts[0].p_raw = [0.11710675300839864, 3.0499498759396038, 0.964478835731713, 0.013794022864770371]
- PASS C06: The selected R1 cell means are 0.420/0.303 at p=0.2 and 0.266/0.193 at :: evidence/claim-values.json -> r1_selected_append_p02_mean / r1_selected_rag_p02_mean / r1_selected_append_p08_mean / r1_selected_summarization_p08_mean = [0.4203701436385292, 0.3032633906301305, 0.2661380511310935, 0.19346331208556639]
- PASS C07: The rebuilt v4-flash grid contains 18 cells with n=10 and reproduces t :: evidence/claim-values.json -> v4flash_cell_count / v4flash_authority_append_p05_mean / v4flash_authority_summarization_p08_mean / v4flash_authority_rag_p08_mean / v4flash_length_append_p08_mean = [18, 0.5209, 0.5208, 0.6067, 2.385]
- PASS C08: The Qwen3.7-Plus authority arm gives Summarization 0.544 and Append-On :: evidence/native-audit.json -> qwen_authority.summarization_mean / qwen_authority.append_only_mean / qwen_authority.construct_status = [0.5438641898144788, 0.8017628644639855, 'descriptive output-length response; not validated authority bias']
- PASS C09: The Round-4 validation aggregate records 1,080 seed-level logs across  :: evidence/native-audit.json -> round4.files / round4.cells / round4.all_cell_n = [1080, 36, [30]]
- PASS C10: The Round-4 reversal is +0.2024 (p=0.0001) on deepseek-v4-flash and +0 :: evidence/native-audit.json -> round4.replication.deepseek-v4-flash.diff_sum_app / round4.replication.deepseek-v4-flash.p_raw / round4.replication.deepseek-v4-pro.diff_sum_app / round4.replication.deepseek-v4-pro.p_raw = [0.2024, 0.0001, 0.0007, 0.9944]
- PASS C11: The external-judge audit covers 120 responses and its maximum absolute :: evidence/native-audit.json -> external_judge.total_judged / external_judge.max_abs_delta_ece = [120, 0.006249999999999978]
- PASS C12: The RAG threshold theta=0.1 was selected using a 5-seed sweep at p=0.5 :: evidence/native-audit.json -> theta_sweep.sweep_n_seeds / theta_sweep.chosen_theta / theta_sweep.sweep_p = [5, 0.1, 0.5]
- PASS C13: The upstream carrier tool reports seven PASS, zero FAIL, and zero NOT_ :: evidence/native-audit.json -> carrier_receipts.count / carrier_receipts.upstream_tool_result.tally = [7, 'PASS=7 FAIL=0 NOT_VERIFIABLE=0']
- PASS C14: The 35 citation keys resolve mechanically to 35 bibliography keys. :: evidence/native-audit.json -> structure.citation_keys / structure.bib_keys = [35, 35]
- PASS C15: The overlay compiles reproducibly in two isolated directories to a 26- :: reports/cleanroom/receipt.json -> pdf.pages / exit_codes[0] / exit_codes[1] = [26, 0, 0]
- PASS C16: The 10-file candidate archive is deterministic and compiles after extr :: reports/package/package-receipt.json -> archive.deterministic / extract_compile.pdf_pages / ready_for_upload = [True, 26, False]
- PASS C17: The authority-marker endpoint validates authority-bias propagation. :: evidence/native-audit.json -> qwen_authority.construct_status = ['descriptive output-length response; not validated authority bias']; BLOCKED status - keep out of manuscript
- PASS C18: The Round-4 raw per-seed logs required for a full independent rerun ar :: evidence/native-audit.json -> round4.raw_per_seed_logs_retained = [False]; BLOCKED status - keep out of manuscript
- PASS C19: Independent method and statistics review is closed against the current :: file evidence/upstream/paper/REVIEW_CARD.md exists (non-JSON); BLOCKED status - keep out of manuscript
- PASS C20: The package is authorized for upload. :: reports/package/package-receipt.json -> ready_for_upload = [False]; BLOCKED status - keep out of manuscript

## Summary: 20 PASS, 0 FAIL, 4 WARN

## Inconclusive entries (hedge + name missing evidence): 0

## Numeric literals in text without any ledger value: 275
+0.000, +0.001, +0.01, +0.015, +0.04, +0.11, +0.20, +0.202, +0.225, +0.32, +0.61, +0.88, +12.1, +12.2, +13.6, +14.3, +3.1, +4.8, +6.5, +8.2, +9.0, +9.8, -0.016, -0.02, -0.03, -0.046, -0.073, -0.08, -0.097, -0.142, -0.26, -0.37, -0.51, -0.66, -0.90, -2.0, -2.07, -2.074, -27.3, -27.9, -4.7, -5.2, 0.0, 0.00, 0.000, 0.0002, 0.0004, 0.005, 0.00556, 0.0063, 0.01, 0.014, 0.015, 0.01667, 0.0235, 0.0255, 0.029, 0.043, 0.045, 0.046, 0.05, 0.055, 0.06, 0.062, 0.065, 0.068, 0.07, 0.071, 0.0765, 0.088, 0.09, 0.092, 0.098, 0.10, 0.100, 0.106, 0.110, 0.117, 0.12, 0.121