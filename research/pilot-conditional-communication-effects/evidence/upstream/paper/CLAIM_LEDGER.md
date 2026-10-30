# Claim ledger — PAPER13_MERGED

| ID | 声明（章节） | 证据文件+字段 | 数值 | 如何验证 | 状态 |
|---|---|---|---|---|---|
| C01 | Face-1 strategy result is scoped to C5 real-image condition, ΔCAF=-0.107 with overlapping CIs; other matched pairs are not uniformly positive. | evidence/canonical_results_v5.json -> [0].gamma_mean | 0.14434833552009504 | Recompute from canonical condition table; report overlap and scope | verified |
| C02 | Calibration matrix separates temporal-horizon and synchronization contrasts; initial ECE gap +0.228 decomposes into +0.207 temporal and +0.021 synchronization. | evidence/e4_n15_results.json | 0.228 / 0.207 / 0.021 | Recompute matched 2x2 contrasts from archived runs | verified |
| C03 | Pure temporal contrast is reported as 0.207 with 95% CI [0.181,0.234], d=4.85, 90.8% of total. | evidence/FINDING1_DATA_SEARCH_VERDICT.md | 0.207 / 0.181 / 0.234 | d=4.85 与 90.8% 在全稿 61 个制品中 0 命中；0.207/0.181 仅以 results.uncalibrated[*].jsd_TV 撞值存在；正文 main.tex 自述 t/d 属 pending re-verification | not-verified（正文自述待重验） |
| C04 | DeepSeek-v4-flash independent reproduction did not reproduce temporal fatigue effect. | evidence/analyses/p1_heldout_v4pro_20260813.json | reproduction status | Check held-out run status and hedge | inconclusive |
| C05 | Joint experiment has 4,000 calls; balanced-subset ANOVA and corrected pairwise contrasts are reported as exploratory. | evidence/joint_full_F_v10_results.json -> metadata.total_calls | 4000 | Verify call count from metadata; independently audit ANOVA before upgrading its inferential status | verified |
| C06 | Confidence-gated TTRL reduces evaluator coupling by 29.4–30.8% on 30-seed expansion; simulation grid does not support universal noise increase. | evidence/e4_30seed_calibrated.json -> n_seeds / calibrated.gTV / uncalibrated.gTV | 30 / 0.7485 / 1.0811 | Compare calibrated vs uncalibrated coupling and inspect five-method grid | verified |
| C07 | E4 external evaluator coupling is gTV=1.081 (uncalibrated) versus prior self-evaluation ~0.03; comparison is cross-configuration, not causal isolation. | evidence/e4_30seed_calibrated.json -> uncalibrated.gTV | 1.0811 | Verify 30-seed archive and retain non-causal hedge | verified |
| C08 | Landscape noise relation is metric-conditional; five complete conditions are used for triangle correlations. | evidence/landscape_5conditions.json -> n / conditions | 5 | Check complete triples and avoid universal claim | verified |
| C09 | Joint deepseek-v4-flash grid contains 5 tasks, n=5 seeds, 125 completed cells and 4,000 calls. | evidence/joint_full_F_v10_results.json -> metadata.n_tasks / metadata.n_seeds / metadata.total_cells_completed / metadata.total_calls | 5 / 5 / 125 / 4000 | Verify metadata against logs | verified |
| C10 | Conclusions are empirical labels (“strategy convergence”, “calibration degradation”), not identified causal processes. | evidence/README.md | scope statement | Cross-check limitations and causal-control requirements | verified |

## Strong-claim audit

“First decomposition” and “metric-conditional relation” are retained only with scope qualifiers and evidence links. No causal mechanism or universal model claim is asserted.
