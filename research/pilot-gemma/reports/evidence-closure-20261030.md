# gemma 证据闭环报告 (2026-10-30)

## 方法
用通用绑定工具对 `source/GEMMA_REVISED.md` + `source/WRITEUP.md` 的数字做「正文数字 → 证据字段」绑定。语料 = `evidence/` 全部 JSON + `CLAIM_LEDGER.md`。

## 结果
- 正文数字总数：**~90**（含表格计数）
- 8 条 claim 全部 PASS（C01-C08），证据绑定质量高
- 无 ledger 数字：**5**（-1.5, -2.0, 1.5, 2.5, 3.2）

## 5 个无 ledger 数字甄别（全部非数据）
| 数字 | 真实来源 | 判定 |
|---|---|---|
| -1.5 | `Qwen2.5-1.5B` 的连字符误解析 | 模型名，非数据 |
| -2.0 | `Apache-2.0` 的连字符误解析 | 许可证名，非数据 |
| 1.5 | `Qwen2.5-1.5B` / `qwen2.5:1.5b-instruct` | 模型名，非数据 |
| 2.5 | `Qwen2.5` 模型族 | 模型名，非数据 |
| 3.2 | `llama3.2:1b` | 模型名，非数据 |

## 结论
- **5 个无 ledger 数字全部是非数据**（模型名/许可证名），**零真数据缺口**。
- gemma 证据闭环**实质完成**。8/8 claim verified，数字全部绑定或非数据。
- 无待补条目。

## 与 CLAIM_LEDGER 对应
C01-C08 全部 verified（450 rows/120 substring positives/96 whole-id/75 distinct pairs/48 fresh rows/22-21-10-7 contract/1-3 false positives/8 checks）。
