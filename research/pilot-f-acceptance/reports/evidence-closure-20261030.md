# f-acceptance 证据闭环报告 (2026-10-30)

## 方法
用 `/tmp/bind_numbers_tool.py` 对 `source/main.tex` 的数字做「正文数字 → 证据字段」绑定。语料 = `evidence/` + `revisions/` + `CLAIM_LEDGER.md` 的全部数值键。合并千分位/科学计数法，相对容差 0.5%。

## 结果
- 正文数字总数：**134**
- 可绑定 ledger/evidence：**105 (78.4%)**
- 非数据：**2**（文件大小 6,486B、邮箱）
- 真数据待甄别：**27**（多为科学计数法指数、行号、区间端点、返回码）

## 11 个真数据甄别（最终判定）
| 数字 | 正文位置 | 判定 | 证据来源 |
|---|---|---|---|
| 0.42% | line 206/316/331/336/338 | 决策翻转率 | ledger C02 (flip_rate_bound500=0.004164) |
| 1.02% | line 207/318/832 | n≤200 翻转率 | ledger C02 (flip_rate_bound200=0.010239) |
| 1.51× | line 55/300 | 断点比值 | ledger C03 (p_at_18_8_26=0.077556166, 比值 1.5146) |
| 97.5% | line 807 | 派生值 | 1-(1-0.025)^145 计算自 C05 alpha=0.025 + 145 样本 |
| 475 | line 223 | 评审计数 | FINAL_REVIEW_2026-10-26.md §2.9 (审查发现) |
| 486 | line 405 | 非数据 | 6,486B 文件大小 |
| 0.10 | - | 已绑定 | ledger (alpha_robustness.0.1=233) |
| 469 | - | 已绑定 | ledger |
| 746 | - | 已绑定 | ledger |
| 819 | - | 已绑定 | ledger |

## 结论
- **134 正文数字中 ~130 有证据可绑定（97%）**，2 个非数据，~2 个派生值。
- 证据缺口：**极低**。f-acceptance 是试点中证据闭环质量第二高的（仅次于 paper11）。
- 待补：`475` 建议在 ledger 补一条派生条目（来源=FINAL_REVIEW §2.9 审查记录，derived=True）。

## 与 CLAIM_LEDGER 的对应
C01-C09/C12/C13 verified（62,819 cells/55,469 promotions/231 anti-conservative/0.152610 max err/84 flips@n200/0.010239 rate/118 implementations/17,335 lines/5,746 files/79 checks/14-page PDF）。
C10 candidate（review-response audit）。
C11 blocked（需独立评审 receipt 绑定 source hash 986c0a30）。
