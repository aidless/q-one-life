# REVIEW CARD — PAPER5_CONSOLIDATED（2026-09-04）

## 题目
Memory Architecture Effects on Output-Length Responses under Controlled Multi-Agent Contamination

## 裁决：3/10（D 否决——串稿+重复复现块）→ **清理并入 F3_Single 或归档**
- A 证据 5：R1 V4-Chat dose-response 来自 live API per-cell logs；Round-4 反转已诚实报告；本地无 results/*.json 不可重算。
- B 兴趣 5：模型依赖架构排序 + 诚实负结果 + 实用指南，贡献面窄。
- C 清晰 3：双 Novelty（L58 正常 + L114 错配）+ 两份完全重复 Reproducibility（L689/L701）+ 破碎句（L201/L277）+ 旧标题残留。
- D 否决：Novelty≥2 + run_all_experiments 模板重复且与 abstract 协议矛盾。

## Critical / Major
1. L114 错配 boilerplate。
2. L693/L701 重复复现块（run_all_experiments.py）与 L53 abstract 协议矛盾。
3. abstract 头牌（p_adj=0.043）被 Round-4 反转（v4-flash +0.202 p=0.0001），L567 承认"不迁移"但 abstract 未降级。

## 版本判定
vs F3_Single/F3_Memory → **旧版/变体**（L86 自称 canonical 但不可投）→ **清理并入 F3_Single 或归档**。
可能新内容：L518-534 Round-4 反转表、v4-flash 18-cell grid、authority-marker arm。