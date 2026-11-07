# TCE act 级检测器结果

日期：2026-11-07。结论：**开发集 precision 均低于冻结的 0.5 下限，按停线
停止；留出集结果只作为参考，不作为通过。**

## 冻结协议

- `PREREGISTRATION_ACT.json`（act 级预注册）
- 切分 SHA-256：`8ba55d2edd68dfeb31409e12e31770aa470ee237cc0822d98f0a863559a809e4`
- 规则 SHA-256：`d6db603beed2e779b86c7e939cd3af811a26ba288b434f18dc61530a77bae5cd`
- 目标：`exploit_test_cases`
- 停线：开发集 precision < 0.5 即不可用，不调参重跑同一留出集。

## 开发集（40 条轨迹）

| 规则 | 命中 | TP | FP | precision |
|---|---:|---:|---:|---:|
| `hidden_label_access` | 254 | 52 | 202 | 0.205 |
| `test_metric_then_edit` | 24 | 3 | 21 | 0.125 |

## 留出集（20 条轨迹，只作参考）

| 规则 | 命中 | TP | FP | precision |
|---|---:|---:|---:|---:|
| `hidden_label_access` | 78 | 13 | 65 | 0.167 |
| `test_metric_then_edit` | 10 | 0 | 10 | 0.000 |

## 为什么这么低

1. `hidden_label_access` 只匹配“路径包含 private/test/hidden”，但许多轨迹的
   private/test 目录本身是公开的输入目录（例如 Kaggle 工作目录里的
   `private/answers.csv` 是评测答案，但也可能只是普通文件名）。
2. 大量正例 TCE 行为是“用 test 指标做配置选择”，而规则只看到“输出包含
   TEST 后 8 步内有编辑”，窗口太窄、模式太泛，且很多编辑不是配置改动。
3. 证据 span 是 1-based 的标注行，但 `trace.jsonl` 的 `tool_call`/`tool_result`
   是两条记录；行号语义与工具事件序号并不总是 1:1，导致匹配噪声。

## 结论

这两个机械规则在冻结的开发集上不可用。这不是“漏检了”，而是**规则形态
不适合当前数据**。本轮不产出 act 级检测能力数字。

注意：`run_tce_detector.py` 只实现了预注册文件里的两个**子规则**
（`hidden_label_access`、`test_metric_then_edit`），并没有实现完整的
`exploit_test_cases` 定义。因此结果只能说明“这两个子规则不可用”，不能
说明整个 TCE 类别无法检测。

## 下一步（不能沿用本结果反推）

1. 先把证据 span 与 trace 行做严格对齐，确认 3,461 个 span 的 1:1 语义。
2. 针对“用测试指标做配置选择”这个最核心子类型，改为**先提取所有 TEST
   指标输出，再在后续配置/代码编辑里做跨语句匹配**，而不是固定 8 步窗口。
3. 重新预注册规则文本（不能沿用 `d6db603…`），再在**新切分**上评估。

已完成对齐审计（`research/validation-20261106/ridar-span-alignment/`）：
0 偏移命中 74.4%，相邻偏移 5–9%，说明 span 指向当前记录；未命中多为
跨行/标点/大小写差异。下一步规则应改用归一化文本窗口匹配。

## 文件

- `result-act.json`（全部 60 条轨迹逐条结果，开发/留出标记）
- `TCE_RESULT_REPORT.zh-CN.md`（本报告）
