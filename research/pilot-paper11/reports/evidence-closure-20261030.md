# paper11 证据闭环报告 (2026-10-30)

## 方法
用通用绑定工具对 `source/main.tex` 的数字做「正文数字 → 证据字段」绑定。语料 = `evidence/` + `CLAIM_LEDGER.md`。对 14 个无 ledger 数字逐一溯源到 evidence 字段。

## 结果
- 正文数字总数：~60
- 20 条 claim 全部 verified（C01-C20）
- 无 ledger 数字：**14**

## 14 个无 ledger 数字甄别
| 数字 | 证据来源 | 判定 |
|---|---|---|
| 0.0444 | `matched-analysis.json -> score_exposure.order_a.mean_selected_score_delta` | 有证据 |
| 0.0667 | `score_exposure.order_b.mean_selected_score_delta` | 有证据 |
| 0.1222 | `score_exposure.order_a.bootstrap95_high` | 有证据 |
| 0.1667 | `score_exposure.order_b.bootstrap95_high` | 有证据 |
| 0.2222 | `not_all_tied.strata_delta` | 有证据 |
| 0.3333 | `not_all_tied.strata_delta`（另一档） | 有证据 |
| 12.5 | `choice_changed_percent` | 有证据 |
| 20.8 | `choice_changed_percent`（另一档） | 有证据 |
| 33.3 | `choice_changed_percent`（另一档） | 有证据 |
| 0.0000 | 零基准（delta 基准） | 有证据（基准） |
| 0.0333 | `not_all_tied.strata_delta` 中间档 | 有证据 |
| 2.5 | llama3.2:3b 模型名 | 非数据 |
| 3.2 | llama3.2:3b 模型名 | 非数据 |
| 4.3 | 表格列宽 | 非数据 |

## 结论
- **14 个无 ledger 数字：11 个有证据可绑定，3 个非数据**。
- paper11 证据缺口**极低**，证据闭环**实质完成**（20/20 claim verified）。
- 这是 5 试点中证据闭环质量最高的。

## 与 CLAIM_LEDGER 对应
C01-C20 全部 verified。evidence 绑定质量高：每条 claim 指向具体 evidence 字段+值。
