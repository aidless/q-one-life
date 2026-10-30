# Paper 35 evidence-qualified claim ledger

Canonical upstream: `evidence/upstream/paper/main.tex`

Canonical SHA-256: `d1eac66806754899440a12bb30446c3944ed230191a077b1bbd331a2ae7a02f0`

Overlay source: `source/main.tex`

Overlay SHA-256: `77f690d40f60fdebd941cc1d2f9031354e050640d21fbef4e3a60444bb76b553`

This ledger separates the native `C01..C11` claims from the evidence that can
currently be replayed. A manifest count is not a raw-cell recount, and a
successful package compile is not independent scientific review.

| ID | Claim | Evidence file and field | Values | Verification | Status |
|---|---|---|---|---|---|
| C01 | The canonical suite contains 100 scenarios across six behavior categories. | `evidence/native-audit.json` -> counts.scenarios / counts.category_counts | 100 | Canonical JSONL count and category-count audit. | verified |
| C02 | The frozen full-run manifest declares four models, 100 scenarios and three seeds, yielding 1,200 cells. | `evidence/upstream/paper/experiments/full_run/_manifest.json` -> scenarios_count / total_cells | 100 / 1200 | Declaration is bound to the manifest; raw per-cell files are absent, so this remains a candidate rather than a recount. | candidate |
| C03 | The frozen aggregate output reports near-zero cross-seed BDS for qwen2_7b. | `evidence/upstream/paper/experiments/full_run/analysis/full_run_analysis.json` -> q1_seed_reproducibility.qwen2_7b.mean_bds | 0.0295 | Aggregate field resolves; the 1,200 raw JSONL files are not present for per-cell recomputation. | candidate |
| C04 | The frozen output reports cross-model BDS 7.1547 and a cross-model minus cross-seed difference of 7.1374. | `evidence/upstream/paper/experiments/full_run/analysis/full_run_stats_20260813.json` -> q2_overall.mean / seed_vs_cross.mean_diff | 7.1547 / 7.1374 | Aggregate values resolve and the CSV mean matches; raw-cell provenance remains blocked. | candidate |
| C05 | The frozen output reports tool-use as the lowest category mean and multilingual as the highest. | `evidence/upstream/paper/experiments/full_run/analysis/full_run_analysis.json` -> q2_cross_model.by_category.T.mean_bds / q2_cross_model.by_category.X.mean_bds | 4.4761 / 9.4194 | Category aggregates resolve; category-level raw cells are not independently recounted. | candidate |
| C06 | The reported Wilcoxon comparison uses 100 paired per-scenario differences. | `evidence/upstream/paper/experiments/full_run/analysis/full_run_stats_20260813.json` -> seed_vs_cross.n_paired | 100 | Aggregate pairing count resolves; the paired raw rows required for replay are absent. | candidate |
| C07 | BDS is defined as a whitespace-token distribution proxy and is not claimed to be a semantic distance or a formal total-variation consistency theorem. | `evidence/upstream/paper/scripts/bds_evaluator.py`; `evidence/native-audit.json` -> checks.formal_consistency_claim_removed | true | The shipped evaluator inspects whitespace tokens and a pooled top-K vocabulary; the unsupported formal-consistency claim was removed in the overlay. | verified |
| C08 | The results generalize to frontier APIs, future snapshots or temporal model drift. | `evidence/upstream/paper/protocol.md`; `evidence/native-audit.json` -> checks.full_run_raw_present | 0 | No multi-snapshot, frontier-API or temporal replication exists; the claim is blocked. | blocked |
| C09 | The three-agent chain pilot demonstrates causal amplification of drift. | `evidence/upstream/paper/experiments/multi_agent/analysis_repro_20260816.json` | missing | The 12 available raw files support a descriptive chain run only; no controlled intervention or power analysis exists. | inconclusive |
| C10 | Model families are interchangeable after controlling for scenario category. | `evidence/upstream/paper/protocol.md` | missing | No prespecified hierarchical family-effect model or adequate external replication exists. | blocked |
| C11 | The regression suite predicts future deployment drift. | `evidence/upstream/paper/protocol.md` | missing | Prospective temporal validation is absent. | blocked |

`candidate` means the claim is supported only by a frozen aggregate and needs
the missing raw-cell replay before it can be promoted. `inconclusive` means the
available pilot is descriptive. `blocked` means the claim must not appear as an
established finding.

Only C01 and C07 are verified at the artifact level. No claim is asserted as
frontier-general, temporally predictive or causal.
