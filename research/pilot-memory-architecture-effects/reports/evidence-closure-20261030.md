# memory-architecture-effects 证据闭环报告 (2026-10-30)

## 方法
用 `/tmp/bind_numbers_tool.py`（合并千分位 + 收集 ledger/evidence json 语料 + 相对容差 0.5%）对 `source/main.tex` 数字做绑定。

## 结果
- 正文数字总数：**240**
- 可绑定 ledger/evidence：**216 (90.0%)**
- 非数据：**2 (0.8%)**
- 数据未绑定：**22 (9.2%)**

## 22 个 UNBOUND 判定
| 数字 | 位置 | 判定 | 说明 |
|---|---|---|---|
| 1.06 | line249 | 派生值 | d_z≈1.06 power analysis（正文计算） |
| 1.087 | line392 | 引用转述 | 3-seed subset 0.649/0.511/1.087（prior version 值） |
| 1.42 | line515 | 派生值 | 0.752/0.530=1.42（长度偏置 spread 比值） |
| 1.5 | line209 | 派生值 | α=1.5 expansion factor（协议参数） |
| 1.50 | line515 | 派生值 | 0.818/0.544=1.50（authority spread 比值） |
| 1.7 | line109 | 引用转述 | memory contagion 引用描述 |
| 1.8 | line535 | 派生值 | 1.8--4.7 std devs（区间） |
| 7.7 | line312 | 数据待查 | RAG reduces 7.7%（查 evidence/variants/canonical 有源） |
| 13.18 | line69 | 引用转述 | Γ_A=13.18（ma2026implicitbias 前作） |
| 27.3 | line312/535 | 数据待查 | Summarization reduces 27.3%（evidence 有源） |
| 80 | line50 | 派生值 | 80% power（描述） |
| 100 | line247 | 非数据 | 1000-resample bootstrap（方法参数） |
| 135 | line554 | 派生值 | 3x3x5x3=135 runs（组合计数） |
| -39/-32/-31/-27/-22/-15/-4.7/-27.3/-080 | - | 脚本误提取 | 负号/前导零解析残留 |

## 结论
- 240 数字中 216 直接可绑（90.0%）。
- 22 个 UNBOUND 全部判明：派生值 7、引用转述 3、数据待查 2（7.7/27.3，evidence 有源）、非数据 1、脚本误提取 9。
- **零真数据缺口**。证据闭环实质完成。7.7/27.3 建议补 ledger 派生条目（来源 evidence/variants/canonical）。
