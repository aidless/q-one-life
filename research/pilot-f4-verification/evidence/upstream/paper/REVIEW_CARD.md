# REVIEW CARD — MERGED_FLAGSHIPS/F4_Verification（2026-09-04）

## 题目
Merged Flagship F4: Verification, Trust Scores and Ablation

## 裁决：1/10（D 否决）→ 不可投，先修数据
- A 证据 1：Table f4 全部 6 个 p 按表内自述 b/c 精确 McNemar 重算不通过；CI 不含自身点估计（复制粘贴）。
- B 兴趣 2：六研究合并卷无单一问题，矛盾淹没诚实性。
- C 清晰 1：规划注（"12 页扩展版"）+ 审计/物流注泄漏；Theory 电报体（L115）；无任务定义。
- D 否决成立：Zenodo placeholder ×3 + 规划注 + headline 统计与自述数据不符。

## 重算（subagent，scipy.binomtest）
| 行 | 论文 p | 重算 | χ²_cc 论文/重算 |
|---|---|---|---|
| Historical 38/14/52 | 1.53e-3 | 2.39e-3 | 10.02/10.17 |
| Prod 36/12/48 | 5.02e-3 | 1.44e-3 | 9.19/11.02 |
| Seed-pooled 44/11/55 | 8.69e-6 | 1.74e-5 | 18.62 ✓ |
| Single-44 31/9/40 | 9.40e-3 | 1.36e-3 | 6.70/11.03 |
| Finance 9/4/13 | 0.146 | 0.534 | 1.23 ✓ |
| Mimicry 21/18/39 | 0.42 | 0.75 | 0.10 ✓ |
- evidence/per_seed_b_c.jsonl 池化 44/12/56 ≠ 表内 44/11/55；CD=1.47 与 "no significant" 自相矛盾（rank 差 1.7>CD；Nemenyi 最小可行 CD≈3.7）；mimicry 与 F45 同名策略结论相反且互不引用；manifest 指纹陈旧（main.tex 3054B ≠ 27973B）。

## TODO
1. 用 per_seed/cells 重算整张 f4 修 p/χ²/CI。
2. 删全部规划注/审计注/占位 DOI，补真实数据链接。
3. 六研究逐一补任务/数据集/参数定义。
4. 与 F45 对齐 mimicry 协议或明示差异。

## 备注
审计外壳比证据厚。修好前整族 F4 系列（含 F4_Single/F45）都禁止进入投稿线。