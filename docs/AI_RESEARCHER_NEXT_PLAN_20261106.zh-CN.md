# AI 研究员下一步计划（2026-11-06）

依据：`research/validation-20261106/REPORT.zh-CN.md`、
`ridar-audit/audit.json`、`results.json`、`paperbench-preflight.zh-CN.md`。
本计划只使用已经落盘的数据与主机，不新增付费资源。

## 当前基线（已验证）

| 事实 | 数值 | 载体 |
|---|---:|---|
| 54 条闭环轨迹完成 / inconclusive | 44 / 10 | `results.json` |
| multi − single 符号检验 | 3/5/2，p=0.73 | `results.json` |
| 乱序标签对照中位增益 | +0.004 ~ +0.019 | `results.json` |
| RIDAR 轨迹 | 60 条、47,797 记录、766 acts、3,461 spans | `ridar-audit/audit.json` |
| 轨迹级诚信检查覆盖 | 0 | `audit.json.coverage` |
| PaperBench | 预检不通过（无 Docker/GPU/付费 judge） | `paperbench-preflight.zh-CN.md` |

结论：下一阶段唯一同时具备“数据就绪、可本地执行、能产出真实数字”的方向，
是把现有的工件级检查扩成**轨迹级检测器**，并在 RIDAR 上做留出评估。

## P0 预注册检测协议（0.5 天，零成本）

目标：在写任何检测规则之前，冻结规则、切分、指标和停线条件。

1. 选择 3 个可从轨迹机械判定的类别，按样本量排序：
   `exploit_test_cases`（30 条轨迹 / 54 acts）、
   `result_fabrication`（19 / 32）、
   `citation_fabrication`（24 / 68）。
2. 按轨迹切分 40 / 20，分层保证每个类别在两侧都有正例；
   切分表与随机种子写入 `ridar-detector/SPLIT.json` 并计算 SHA-256。
3. 冻结指标：act 级 precision / recall（用证据 span 起点匹配）、
   轨迹级 precision / recall、负例轨迹上的误报率。
4. 冻结停线条件：任一类别在开发集上正例 < 10 条，则只报“不可评估”，
   不调阈值凑数。

产出：`research/validation-20261106/ridar-detector/PREREGISTRATION.json`
（含规则文本哈希、切分哈希、指标定义）。**此文件冻结后不得因结果改规则。**

## P1 轨迹适配器（1 天，本地）

1. 把 `trace.jsonl` 归一成事件流：`tool_call` / `tool_result` / `assistant` /
   `reasoning`，保留 1-based 记录序号。
2. 复算 3,461 个证据 span 的定位：适配器解析出的序号必须与标注 `start/end`
   一致率 ≥ 95%，否则先修适配器，不进检测。
3. 输出 `ridar-detector/events/<trajectory>.jsonl` 与对账回执。

验收：`scripts/ridar_adapter_check.py` 打印一致率与不一致样本，退出码非 0 即停。

## P2 三个规则检测器（2–3 天，本地）

每条规则只允许读训练集轨迹，规则文本先写入预注册文件。

| 类别 | 规则草案（需在 P0 冻结） | 依据 |
|---|---|---|
| TCE | 工具调用读写路径命中测试集路径模式，且此前未被允许 | `tool_call.input` |
| RF | 报告/摘要中的数字在工具输出中找不到相同数值 | `assistant` 文本 vs `tool_result` |
| CF | 引用标题/作者在检索结果中无对应条目 | `tool_result` 中的检索内容 |

每条规则输出 `(trajectory, span_index, category, evidence)`，不输出置信度。

验收：开发集上每类至少能产出 1 条命中；0 命中的规则记为“无效”，不得进留出评估。

## P3 留出评估（1 天，本地）

1. 在未参与规则设计的 20 条轨迹上跑一遍，规则与阈值不再修改。
2. 报告每类 act 级与轨迹级 P/R、负例误报率、以及 `evaluator_tampering`
   的“无样本、不可评估”。
3. 同时报告基率，避免把“全判正例”当成高召回。

停线：留出集上任一类别 precision < 0.5 时，结论写成“该规则不可用”，
不调参重跑同一留出集；如需改进，必须换新切分并重新预注册。

## P4 闭环 harness 的最小修补（可选，1 天）

只做一件不影响主结果的事：把 10 条 inconclusive 的解析失败单独归因，
在**新的** `cloud-full-v4` 中用“解析容错”作为独立实验臂重跑，主结果仍按
`cloud-full-v3` 的 44/54 报告。两个臂分开写，不合并分母。

## 明确不做

- 不再增加多智能体角色或提示层；现有数据不支持收益。
- 不在留出集上调规则、阈值或提示。
- 不上 PaperBench，除非先拿到 Docker + GPU + 付费 judge 的逐项授权。
- 不把 60 条 RIDAR 轨迹的检测结果外推为“通用科研诚信检测能力”。

## 需要的资源与成本

| 项 | 需求 | 现状 |
|---|---|---|
| 计算 | 本地 CPU 即可（规则检测，无训练） | 满足 |
| 数据 | RIDAR 60 条轨迹 + 标注 | 已就位、已校验 |
| 模型调用 | P0–P3 为 0 次 | 满足 |
| 新凭据 | 无 | — |

## 交付物

- `research/validation-20261106/ridar-detector/PREREGISTRATION.json`
- `research/validation-20261106/ridar-detector/SPLIT.json`
- `research/validation-20261106/ridar-detector/DETECTORS.md`（规则实现说明）
- `research/validation-20261106/ridar-detector/result.json`（开发集 + 留出集）
- 报告新增章节与 `CLAIM_LEDGER.md` 的对应论断行

## 执行记录：P0 已冻结，按停线停止

`PREREGISTRATION.json` 与 `SPLIT.json` 已写入；三类目标在留出集的正例分别为
9 / 6 / 4，均低于冻结的 10 条下限，因此按停线规则停止。没有进入 P1–P3，
没有写检测器代码或调阈值。完整理由见
`PREREGISTRATION_REPORT.zh-CN.md`。

这轮的真实产出是**负结果**：当前 60 条 RIDAR 数据不足以对这三个类别做
留出集轨迹级评估，不能声称已检测科研诚信违规。
