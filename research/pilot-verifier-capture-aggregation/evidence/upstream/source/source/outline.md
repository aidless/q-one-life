# PAPER6_CONSOLIDATED — TMLR 论文大纲（自动生成）

> 生成时间：2026-09-01
> 输入：`claims.yaml`（5 条主张）
> 状态：**草稿**，需作者 review 后用于写作

## 一、论文核心信息

| 项 | 值 |
|---|---|
| 论文 | PAPER6_CONSOLIDATED |
| 主张数 | 5 |
| 建议章节数 | 1 |

## 二、章节大纲

### Experiments（实验）

*目标*：设置→主结果→消融→分析；≥3 数据集，≥5 基线，≥3 消融
*质量门*：证据充分性、统计严谨性

**The benchmark contains four scenarios, seven aggregation met**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C01 | The benchmark contains four scenarios, seven aggregation met… | `evidence/main_results/benchmark_table.json` | 结果表/数据图（从 JSON 提取数值） |

**Plain majority is the strongest or tied method in the four h**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C02 | Plain majority is the strongest or tied method in the four h… | `evidence/main_results/benchmark_table.json` | 结果表/数据图（从 JSON 提取数值） |

**The three attack families are prompt injection, rubric injec**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C03 | The three attack families are prompt injection, rubric injec… | `attacks.py; benchmark.py; evidence/main_results/per_attack_table.json` | 结果表/数据图（从 JSON 提取数值） |

**A local real-model pilot contains 20 questions, four local m**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C05 | A local real-model pilot contains 20 questions, four local m… | `evidence/real_llm_results/summary.json` | 结果表/数据图（从 JSON 提取数值） |

**The local pilot gives identical rounded mean accuracy  for a**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C06 | The local pilot gives identical rounded mean accuracy (0.916… | `evidence/real_llm_results/summary.json` | 结果表/数据图（从 JSON 提取数值） |


## 三、TMLR 质量门自检清单

对照 `TMLR_QUALITY_CHECKLIST.md` 逐项自检：

| 维度 | 达标线 | 当前状态 | 缺口 |
|---|---|---|---|
| 新颖性 | ≥7/10 | 待评估 | 需确认贡献点 2-4 个、与最相关工作区分 |
| 证据充分性 | ≥8/10 | 待评估 | 每主张绑证据；VERIFY 门禁应全 PASS |
| 统计严谨性 | ≥8/10 | 待评估 | 需报告均值/方差/样本量/检验/CI |
| 写作质量 | ≥8/10 | 待评估 | 需多轮审稿 + AI 腔检测 |
| 结构完整性 | ≥8/10 | 待评估 | 章节逻辑 + 贡献对应 |
| 可复现性 | ≥8/10 | 待评估 | 需代码/数据/种子/环境 |
