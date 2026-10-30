# tmlr_p6 — R16 对抗审阅摘要

## R16 gate rerun 2026-08-19

- Ledger: **7 PASS / 0 FAIL / 2 WARN**; taint **0/0**; scoped statistics **0 error classes**; scoped TMLR **0 failures**; compile **0 errors** with six orphan labels.
- C05 remains blocked: timestamped snapshots disagree and the manuscript mixes a synthetic stand-in with a 20 Newsgroups framing. A single canonical dataset/provenance chain is required.
- C06 remains blocked pending calibration-after-resampling baseline, Brier/NLL/ECE intervals, neural-classifier comparison, effect sizes, and stronger seed/model coverage.

## 裁决

形式门禁通过，但稿件仍是 Major Revision，未达到 Strong Accept。核心风险是结果快照、数据集身份和正文 headline 不一致。

## 关键问题

1. 四个时间戳 supplementary snapshot 的 ECE/AUROC 不同，正文摘要值无法唯一映射到某个 JSON；必须指定 canonical run 并解释其余快照。
2. Methods 写有 synthetic stand-in，而摘要/标题使用 20 Newsgroups；需提供真实数据来源、许可证、预处理和 hash，或全篇改为 synthetic study。
3. 需要 calibration-after-resampling baseline，报告 Brier/NLL/ECE 与置信区间，而不只给单一 ECE。
4. 目前缺少神经分类器/embedding 组合的完整比较和 practical magnitude；应报告效应量及跨 seed 方差。
5. N-sensitivity 只有 5 seeds，不能支撑稳定排名；需扩大 seeds 或收窄结论。

## 门禁

- TMLR scoped：PASS（0 failures）
- taint/stats/hallucination：PASS（仅说明格式与可复算性）
- LaTeX：0 errors（仍有 orphan-label/uncited-bib warnings）
- Claim ledger：关键 provenance claim BLOCKED
- Strong Accept：**BLOCKED**

## P0 修订

- 选择并冻结 canonical snapshot，重算所有表格/摘要/图；其余结果放 supplementary 并标注 exploratory。
- 统一真实 20 Newsgroups 与 synthetic 数据声明，补齐数据/运行时/模型 metadata。
- 增加 calibration-after-resampling、Brier/NLL、效应量和多重比较校正。
- 扩展 seeds、神经模型和外部数据集，或明确降级为 pilot/provenance report。
