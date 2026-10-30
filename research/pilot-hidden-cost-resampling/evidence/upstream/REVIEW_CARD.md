# REVIEW CARD — tmlr_p6（2026-09-04）

## 题目
The Hidden Cost of Resampling: How Imbalance Correction Degrades Probability Calibration in Tree Ensembles

## 裁决：2/8（D 否决 + 熔断）→ 弃投（文件头已自认并入 tmlr_p12）
- A 证据 1-2：Table1 数字无 raw 可复算，且被 newsgroups raw 反向证伪。
- B 兴趣 2：重采样伤校准是真问题，但正文从未做重采样（标题与内容不符）。
- C 清晰 2：文件头残留 "DEPRECATED 已并入 tmlr_p12"。
- D 否决成立：串稿（三套数字混杂）+ 标签串换（newsgroups 数据标成合成分类）。

## Critical（subagent 重算，路径见下）
1. **Table1 vs 引言自相矛盾**：L50-52 称 MLP ECE≈0/RF 欠自信≈0.028，Table1 却报 MLP 0.131 最差、RF 0.094-0.102（newsgroups 旧版残留）。
2. **newsgroups raw 复算方向相反**：MLP ECE≈0.074（最优）、RF-Hybrid≈0.099、Isotonic≈0.050——与 Table1 全不符；results/analysis.json 是无关的 270-cell 模拟。
3. **Table2 标签串换**：N-sensitivity 数字逐格复现自 n_sensitivity_newsgroups.json（dataset=newsgroups, bge-zh），正文却写成合成 style-classification。
4. **规划注泄漏**：文件头 "DEPRECATED 已并入 tmlr_p12" + 标题含 Resampling 但正文无重采样。
- Minor：MLP r=+0.078 复算异号（-0.09~-0.12）；99% vs 96% 减幅矛盾；Finding3=Finding5 重复；双 Limitations。

## TODO
1. 弃投：按文件头规划并入 tmlr_p12（p12 吸收其 newsgroups 口径）。
2. 若坚持独立：发 synthetic per-seed raw 对齐 Table1（或改回 newsgroups 口径统一数字）、删串稿与 newsgroups 附录图、删 DEPRECATED 头注并修标题。
3. 复核 MLP r 符号。

## 备注
家族合并信号：p6 明确标记 p12 为正典继承者，本卡不单独推进。