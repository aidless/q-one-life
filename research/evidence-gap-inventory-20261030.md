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
| memory-architecture-effects | review_pending | 20 | 0 | 4 | 275 | 需绑定 | 中 |
| calibration-fatigue | blocked | 14 | 0 | 6 | 337 | 需绑定 | 高 |
| calibrating-evaluator | archived | 14 | 0 | 6 | 342 | 需绑定 | 高 |
| conditional-communication-effects | blocked | 15 | 0 | 5 | 415 | 需绑定 | 高 |

## 关键发现
1. **全部 17 个 pilot 均为 0 FAIL**（早期汇总误读为 FAIL:7，实为 grep 把 WARN 计数的 0 FAIL 读错）。证据绑定无实际矛盾，只有「无 ledger 数字」缺口。
2. **paper11/gemma/arc/f-acceptance/bench 5 个已实质闭环**（D31-D45 的完成标准）。
3. **bench-noise-floor** 虽 540 个无ledger，但 99.4% 可绑定（C02/C03 需发表决策/独立评审，非编码）。
4. 剩余 12 个 pilot 的证据闭环需逐层绑定（多数 no_ledger 是宏/表格值，与 bench 类似大概率可绑）。

## 与 90 天计划对应
- D31-D45「Top-20 证据闭环」：**5/17 实质完成**，其余 12 个需绑定（无 ledger 数字多为宏/表格/舍入值，预计可绑 >90%）。
- 下一步优先：绑定 no_ledger 数字（按 pilot 逐一跑 bind 工具）→ 优先 paper2-coupling（B 已做 proof audit，离 ready 最近）→ 其余 blocked/archived。
