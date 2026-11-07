# AI 研究员下一轮最小可执行方案

日期：2026-11-07。依据：`ridar-detector/PREREGISTRATION_REPORT.zh-CN.md`，
`ridar-audit/audit.json`，`peerread-check/result.json`。

## 问题

轨迹级检测器上一轮按停线停止，因为三类目标的留出集正例都 < 10。但数据本身
没有消失：60 条轨迹、766 个 act、3,461 个证据 span 全部可解析。问题不是
“没有数据”，而是“按轨迹切分时每类留出正例太少”。

## 推荐：重新预注册 act 级评估

把评估单位从“轨迹”改为“act”，可以复用现有 60 条轨迹，并把可评估样本量
提高到足以满足留出下限。

### 样本量估算（从标注实算）

| 类别 | acts | 轨迹数 | 若 40/20 按轨迹分，留出 acts 约 | 是否达 10 |
|---|---:|---:|---:|---|
| `exploit_test_cases` | 54 | 30 | ~18 | 是 |
| `result_fabrication` | 32 | 19 | ~11 | 是 |
| `citation_fabrication` | 68 | 24 | ~23 | 是 |

注意：这只说明 act 级样本量可能足够；**不能**直接沿用上一轮的轨迹切分，
因为那会与“先冻结后写代码”的纪律冲突。必须新建一份 act 级预注册，并把
“正例单位 = act、允许同一轨迹多个 act”写进协议。

### 新协议要点

1. **评估单位**：act。同一轨迹可以贡献多个正例，报告时必须同时给出
   “act 数 / 轨迹数”，避免被重复计数误导。
2. **切分**：按轨迹分层切分 40/20（保留轨迹级独立性），再在开发集内选择
   哪些 act 用于规则开发；留出集 act 完全不参与。
3. **正例下限**：每个类别在留出集至少 10 个 act（不是 10 条轨迹）。
4. **指标**：act 级 P/R 为主；轨迹级 P/R 为辅助；必须报告轨迹数。
5. **停线**：留出集任一类别 precision < 0.5，或留出正例 < 10，报不可用，
   不调参重跑同一留出集。

### 最小范围

先只做 **`exploit_test_cases`**（54 acts、30 条轨迹，样本最足且规则最机械），
跑通完整链路后再扩展到另外两类。这样第一轮就能得到一个真实数字，而不是
又停在一张空表上。

## 产出

- `research/validation-20261106/ridar-detector/PREREGISTRATION_ACT.json`
- `research/validation-20261106/ridar-detector/SPLIT_ACT.json`
- `research/validation-20261106/ridar-detector/result-act.json`
- `research/validation-20261106/ridar-detector/ACT_REPORT.zh-CN.md`

## 明确不做

- 不沿用上一轮轨迹级切分。
- 不把 60 条轨迹的 act 级结果外推为通用科研诚信检测。
- 不合并 act 与轨迹数字成一个“检测分”。
- 不在留出集上调规则或阈值。

## 如果用户更想扩大数据

等 RIDAR 作者发布更多 RIV-Gold 轨迹，或用外部等价标注。两种都必须在拿到新
数据前重新冻结协议，不能用旧协议。

## 执行记录（2026-11-07）

已冻结 act 级协议（`PREREGISTRATION_ACT.json`、`SPLIT_ACT.json`）。三类中
只有 `exploit_test_cases` 达到 10 个留出 act 下限（10 acts / 7 轨迹）。

第一轮实现的两个机械子规则在开发集上的 precision：

| 子规则 | TP / (TP+FP) | precision |
|---|---:|---:|
| `hidden_label_access` | 52 / 254 | 0.205 |
| `test_metric_then_edit` | 3 / 24 | 0.125 |

两者均低于冻结的 0.5 下限，按停线停止；留出集结果只作参考
（0.167 / 0.000）。结论：这两个子规则不可用，不产出 act 级检测能力数字。
详细报告：`ridar-detector/TCE_RESULT_REPORT.zh-CN.md`。

## 下一轮（不能沿用本轮反推）

1. 先把 3,461 个证据 span 与 trace 行做严格 1:1 对齐。
2. 把“测试指标输出后修改配置”改成跨语句匹配：先提取所有 TEST 指标，再在
   后续配置/代码编辑里匹配，而不是固定 8 步窗口。
3. 重新冻结规则文本（新的 SHA-256），再在新切分上评估。
