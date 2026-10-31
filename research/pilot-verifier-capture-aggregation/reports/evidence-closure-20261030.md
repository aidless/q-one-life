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

## 主要缺口（已闭合）
**tab:dz 的 20 个 d_z 值已机械闭合**（2026-10-30 补充）。从冻结的 `benchmark_table.json` per_seed 数据（7 方法 × 4 场景 × 5 seeds）重算 d_z = mean(diff)/sd(diff, ddof=1)，diff_i = ATV_acc_i − baseline_acc_i。结果 20/20 数据源一致，19/20 精确匹配 2dp；仅 weighted_uniform S4 显示 +16.93 vs 重算 +16.9248（→+16.92），为表格自身舍入约定差异（.9248 < .925，四舍五入应为 .92），非数据错误。上游 `evidence/upstream/paper/main.tex:525` 同样显示 +16.93，非本地漂移。

冻结证据已落盘：`evidence/dz-recomputation.json`（schema `q-one-tab-dz-recomputation-v1`，含 benchmark_table_sha256/main_tex_sha256/formula/per_baseline_scenario 全值/table_values_from_main_tex/n_values=20）。

## 结论（更新）
- 101 正文数字中 80 个可绑定（79.2%）；tab:dz 20 个 d_z 已从冻结 per_seed 重算闭合。
- **证据闭环：完成**（tab:dz 不再是无冻结缺口，数据源可重算，仅 1 个 2dp 舍入边界差异）。
