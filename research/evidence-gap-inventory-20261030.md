# 全局证据缺口清单 (2026-10-30) — D31-D45 交付物

## 目的
「Top-20 证据缺口可计算」——枚举 17 个 pilot 的证据闭环状态，识别仍有严重缺口的 pilot，供 D46+ 处理排序。

## 全局汇总（17 pilot）

| Pilot | 状态 | PASS | FAIL | WARN | 无ledger数字 | 证据闭环 | 优先级 |
|---|---|---|---|---|---|---|---|
| paper11 | review_pending | 20 | 0 | 0 | 14（11有证据/3非数据） | **实质完成** | 低 |
| gemma | revision | 8 | 0 | 0 | 5（全非数据） | **实质完成** | 低 |
| arc-paper-track | revision | 11 | 0 | 1 | 1（有证据） | **实质完成** | 低 |
| f-acceptance | review_pending | 13 | 0 | 1 | 120（~97%可绑） | **实质完成** | 低 |
| bench-noise-floor | revision | 14 | 0 | 2 | 540（99.4%可绑） | **实质完成**（C02/C03 需发表决策） | 中 |
| verifier-capture-aggregation | review_pending | 11 | 0 | 4 | 101 | 需绑定 | 中 |
| agent-behavior-regression | revision | 11 | 0 | 4 | 105 | 需绑定 | 中 |
| closing-calibration-landscape | revision | 16 | 0 | 5 | 111 | 需绑定 | 中 |
| hidden-cost-resampling | archived | 19 | 0 | 12 | 154 | 需绑定 | 中 |
| f2-k-generalization | blocked | 21 | 0 | 16 | 140 | 需绑定 | 高 |
| f4-verification | blocked | 21 | 0 | 15 | 192 | 需绑定 | 高 |
| paper2-coupling | review_pending | 14 | 0 | 2 | 247 | 需绑定（B 已做 proof audit） | 高 |
| n-sensitive-calibration | archived | 159 | 0 | 4 | 255 | 需绑定 | 高 |
| memory-architecture-effects | review_pending | 20 | **7** | 4 | 275 | **有 FAIL，需修复** | **最高** |
| calibration-fatigue | blocked | 14 | 0 | 6 | 337 | 需绑定 | 高 |
| calibrating-evaluator | archived | 14 | 0 | 6 | 342 | 需绑定 | 高 |
| conditional-communication-effects | blocked | 15 | 0 | 5 | 415 | 需绑定 | 高 |

## 关键发现
1. **memory-architecture-effects 是唯一有 7 FAIL 的 pilot**——证据绑定有实际错误（不是缺口，是矛盾）。
2. **paper11/gemma/arc/f-acceptance/bench 5 个已实质闭环**（D31-D45 的完成标准）。
3. **bench-noise-floor** 虽 540 个无ledger，但 99.4% 可绑定（C02/C03 需发表决策/独立评审，非编码）。
4. 剩余 12 个 pilot 的证据闭环需逐层绑定（多数 no_ledger 是宏/表格值，与 bench 类似大概率可绑）。

## 与 90 天计划对应
- D31-D45「Top-20 证据闭环」：**5/17 实质完成**，1 个有 FAIL 待修（memory-architecture）。
- 下一步优先：memory-architecture-effects（7 FAIL）→ paper2-coupling（247）→ conditional-communication（415，blocked）。
