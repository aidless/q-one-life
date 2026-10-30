# arc-paper-track 证据闭环报告 (2026-10-30)

## 方法
用通用绑定工具对 `source/ARC_PROPOSED.md` 的数字做「正文数字 → 证据字段」绑定。语料 = `evidence/` 全部 JSON + `CLAIM_LEDGER.md`。

## 结果
- 正文数字总数：~20（含表格 4 个 score）
- 10 条 claim verified / 1 inconclusive
- 无 ledger 数字：**1**（3.08）

## 1 个无 ledger 数字甄别
| 数字 | 正文位置 | 证据来源 | 判定 |
|---|---|---|---|
| 3.08 | line 5/22（表格 score） | `evidence/arc_lineage_audit.json -> observations[3].score` | **有证据**（官方 submission 记录） |

## 结论
- **3.08 有直接证据**（arc_lineage_audit.json observations[3]，submission 56820768/date 2026-10-04/notebook arc3-duck-7450-v1/source_version 353563241）。
- arc 证据闭环**实质完成**。唯一无 ledger 数字已绑定。
- 其他 score（3.38/4.01/4.24）同样在 observations[0..2]，已绑定。

## 与 CLAIM_LEDGER 对应
10 verified claims：source lineage/同版本分数差 0.93/私有字节未捆绑/无 agent 评测/无新官方分/无因果组件增益/无噪声分布/无最终 top5。1 inconclusive：offline→hidden 映射（需更多观测）。
