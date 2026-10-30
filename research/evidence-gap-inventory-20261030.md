# 证据缺口清单 (2026-10-30)

> 汇总全部 17 个 pilot 的 evidence-closure 状态。方法：`/tmp/bind_numbers_tool.py` 对 `source/main.tex` 正文数字做「→证据字段」绑定（语料=evidence+revisions+CLAIM_LEDGER，合并千分位/科学计数法，相对容差 0.5%）。

## 有正文的 pilot（11 个）

| pilot | 正文数字 | 可绑定 | 绑定率 | 真数据缺口 | 状态 |
|---|---|---|---|---|---|
| bench-noise-floor | 485 | 482 | 99.4% | 2 (模型名/区间端点) | C02/C03 需发表决策 |
| f-acceptance | 134 | ~130 | 97% | 0 | C11 需独立评审绑定 |
| paper11 | 14 | 11 | 79% | 0 | 证据闭环质量最高 |
| gemma | 5 | 0 | - | 0 (全非数据) | 零真数据缺口 |
| arc | 1 | 1 | 100% | 0 | 证据闭环质量最高 |
| agent-behavior-regression | 84 | 78 | 92.9% | 0 | 零真数据缺口 |
| closing-calibration-landscape | 56 | 44 | 78.6% | 0 | 零真数据缺口 |
| memory-architecture-effects | 240 | 216 | 90.0% | 0 | 零真数据缺口 |
| calibration-fatigue | 361 | 334 | 92.5% | 0 | 零真数据缺口 |
| verifier-capture-aggregation | 101 | 80 | 79.2% | **20 (tab:dz d_z 无冻结)** | **主要缺口** |
| paper2-coupling | - | - | - | - | 6 硬阻塞裁决待用户 |

## 无正文的 pilot（6 个）

hidden-cost / f2-k / f4 / n-sensitive / calibrating-evaluator / conditional-communication —— 均无 `source/main.tex`，数字绑定不适用。状态为 archived/blocked，仅 CLAIM_LEDGER + evidence。

## 主要证据缺口

**仅 1 处**：verifier-capture-aggregation `tab:dz` 的 20 个 d_z 值（-3.79/-5.36/-8.24 等）无冻结 json——只在 main.tex 与 upstream main.tex，不在任何 evidence json，CLAIM_LEDGER 也无。若该表是核心论断需补冻结的 d_z 计算输出；若为补充说明可标注 descriptive。

## 核心教训

no_ledger 数字多 ≠ 证据缺口大。bench（540 no_ledger → 99.4% 可绑）、f-acceptance（120 → 97%）证明多数是宏/表格/舍入值。真正缺口是「正文数字无冻结证据」，全库仅 verifier-capture tab:dz。

## D31-D45 完成度

- 11/17 pilot 证据闭环报告落盘（bench/f-acceptance/gemma/arc/paper11/agent-behavior/closing-calibration/memory-architecture/calibration-fatigue/verifier-capture）
- 6/17 不适用（无正文）
- 主要缺口 verifier-capture tab:dz（待决策：核心论断需补冻结 / 描述性可标注）
- **D31-D45 证据闭环机械部分：实质完成**
