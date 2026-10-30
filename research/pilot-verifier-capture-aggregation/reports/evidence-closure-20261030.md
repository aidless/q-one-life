# verifier-capture-aggregation 证据闭环报告 (2026-10-30)

## 方法
用 `/tmp/bind_numbers_tool.py` 对 `source/main.tex` 的数字做「正文数字 → 证据字段」绑定。语料 = `evidence/` + `revisions/` + `CLAIM_LEDGER.md` 的全部数值键。合并千分位/科学计数法，相对容差 0.5%。

## 结果
- 正文数字总数：**101**
- 可绑定 ledger/evidence：**80 (79.2%)**
- 数据未绑定：**21 (20.8%)**

## 21 个 UNBOUND 分类
| 数字 | 位置 | 判定 | 证据来源 |
|---|---|---|---|
| 0.889/0.553/0.459/0.843/0.686 | line 474 tab:main | 准确率表 | benchmark_table.json -> aggregate[method][scenario] (majority S1=0.8886/S4=0.843, trust_median mean=0.6863) |
| -3.79/-5.36/-8.24/+0.90/+0.35 等 20 个 | line 503-506 tab:dz | **d_z 效应量表** | **无冻结 json**（只在 main.tex，不在任何 evidence json） |
| 0.69/0.34/0.94/0.74 | line 75-77 | 描述值 | synthetic pilot (0.32 vs 0.41 at honest accuracy 0.6) |
| 256 | line 950/968 | SHA-256 说明 | 非数据（哈希长度说明） |
| 0.99/1.7 | line 290/554 | 描述值 | 定性描述（p_i=0.99、1.7 percentage points） |

## 主要缺口
**tab:dz 的 20 个 d_z 值无冻结证据**。效应量表只在 `source/main.tex` 与 `evidence/upstream/paper/main.tex` 中，不在任何 evidence json。CLAIM_LEDGER 也无这些值。这是 verifier-capture 的主要证据缺口——效应量计算无冻结源。

## 结论
- 101 正文数字中 80 个可绑定（79.2%）。
- 主要缺口 = tab:dz 的 20 个 d_z 值（效应量表无冻结 json）。
- 建议：若该表是核心论断，需补冻结的 d_z 计算输出；若为补充说明，可标注 descriptive。
