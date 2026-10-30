# PAPER35_FRONT_DRIFT — TMLR 论文大纲（自动生成）

> 生成时间：2026-09-01
> 输入：`claims.yaml`（7 条主张）
> 状态：**草稿**，需作者 review 后用于写作

## 一、论文核心信息

| 项 | 值 |
|---|---|
| 论文 | PAPER35_FRONT_DRIFT |
| 主张数 | 7 |
| 建议章节数 | 1 |

## 二、章节大纲

### Experiments（实验）

*目标*：设置→主结果→消融→分析；≥3 数据集，≥5 基线，≥3 消融
*质量门*：证据充分性、统计严谨性

**The canonical suite has 100 scenarios across six behavior ca**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C01 | The canonical suite has 100 scenarios across six behavior ca… | `data/scenarios/canonical.jsonl; protocol.md` | 范围说明（用于讨论/局限/附录） |

**The main local run has four models, 100 scenarios, and three**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C02 | The main local run has four models, 100 scenarios, and three… | `experiments/full_run/_manifest.json` | 结果表/数据图（从 JSON 提取数值） |

**Temperature-0 cross-seed BDS is low in the tested local mode**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C03 | Temperature-0 cross-seed BDS is low in the tested local mode… | `experiments/full_run/analysis/full_run_analysis.json` | 结果表/数据图（从 JSON 提取数值） |

**Cross-model BDS is larger than cross-seed BDS in the tested **

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C04 | Cross-model BDS is larger than cross-seed BDS in the tested … | `experiments/full_run/analysis/full_run_stats_20260813.json` | 结果表/数据图（从 JSON 提取数值） |

**Heterogeneity varies by scenario category, with tool-use low**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C05 | Heterogeneity varies by scenario category, with tool-use low… | `experiments/full_run/analysis/full_run_analysis.json` | 结果表/数据图（从 JSON 提取数值） |

**The reported Wilcoxon comparison is based on paired per-scen**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C06 | The reported Wilcoxon comparison is based on paired per-scen… | `experiments/full_run/analysis/full_run_stats_20260813.json` | 结果表/数据图（从 JSON 提取数值） |

**BDS is a whitespace-token distribution metric, not a semanti**

| 主张 | 陈述 | 证据 | 图表 |
|---|---|---|---|
| C07 | BDS is a whitespace-token distribution metric, not a semanti… | `protocol.md; scripts/bds_evaluator.py` | 脚本说明（附录） |


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
