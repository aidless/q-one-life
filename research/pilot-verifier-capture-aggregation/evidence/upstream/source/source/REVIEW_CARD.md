# REVIEW CARD — PAPER6_CONSOLIDATED（2026-09-04）

## 题目
An Empirical Study of Aggregation Methods Under Verifier Capture in Multi-LLM Ensembles

## 裁决：2/10（D 否决——正文占位+串稿）→ **归档**（F4/F5/F45 旧版）
- A 证据 4：仅 synthetic pilot（majority/trust_median 并列 0.686），无 real-trace 基准；abstract 0.69/0.34 与 tab:per-attack majority=0.877 口径不一致。
- B 兴趣 5：诚实负结果（"no method beats majority"）+ 反直觉结论对工程有参考；纯 synthetic。
- C 清晰 2：**L565 正文显式占位 "[Placeholder body...]"** + 双 Novelty（L89/L559 均错配）+ 双 Reproducibility + 头部状态注。
- D 否决：占位 + Novelty≥2 + 复现模板。

## Critical / Major
1. L565 显式占位（未完成稿）。
2. L89/L559 错误主题 boilerplate（串稿）。
3. L992/L1000 模板与 synthetic 4 分钟口径矛盾。
4. L827-834 被证伪的 Theorem 2 仍保留声明。

## 版本判定
vs F4/F5/F45 合并正典 → **旧版/变体**（L1-5 自称 COMPLETE DRAFT 但含占位）→ **归档**。
可能新内容：CRV 形式化 threat model（L226-318）、negative-result 结构解释（L502-555）。