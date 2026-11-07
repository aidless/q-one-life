# 打造 AI 研究员：Q-One Research Factory 详细建设计划

状态：草案 v1（2026-11-05）
定位：在现有「证据可审计工厂」之上，补齐 ScientistTwo 式「自主生产闭环」。

## 1. 目标与非目标

### 目标

让 Research Factory 能从一个人给出的研究问题出发，自动完成：

1. 生成并进化候选假设；
2. 在小子集上筛选，避免把算力押在坏想法上；
3. 设计并提交实验到云端；
4. 回收结果、生成论断账本；
5. 对账本做对抗评审；
6. 把可执行异议转成反驳实验；
7. 写作、自动审稿、按审稿意见再迭代。

每一步都保留哈希回执与 fail-closed 语义。

### 非目标

- 不追求「无人值守发论文」。投稿、上传、对外发布永远需要人工授权。
- 不把自动审稿分数当成真实录用结论。
- 不声称能自动解决「新颖性/重要性」类异议。AppliedScientist
  (arXiv:2609.14738) 显示这类修订成功率仅 11.1%。
- 不在本机跑长实验。计算一律走云端执行器。

## 2. 现状与差距

| 环节 | ScientistTwo | Q-One 现状 | 差距等级 |
|---|---|---|---|
| 问题登记 | 输入 problem | `register_question` 已有 | 无 |
| 假设生成 | Idea Generator 多轮进化 | 只能手工登记一条假设 | P0 |
| 假设筛选 | Evaluator 小子集筛选 | 无 | P0 |
| 实验计划 | Analyzer 自动设计消融 | 计划结构已有，靠人填 | P1 |
| 云端执行 | 全自动 | `cloud_executor` 已有 | 无 |
| 结果回收 | 自动 | `collect_results` 已有 | 无 |
| 论断账本 | 自动 | `write_claim_ledger` 已有 | 无 |
| 对抗评审 | Peer-Review Agent | `adversarial_review` 已有 | 无 |
| 反驳实验 | Rebuttal Agent 真跑实验 | 只生成计划，未接线 | P0 |
| 写作 | Writer Agent | `write_draft` 只接收现成稿 | P1 |
| 自动审稿 | ScholarPeer / Stanford | 无统一 rubric | P1 |
| 元评审循环 | Meta-Review 控制迭代 | 无 | P2 |
| 规模化 | 107 题并行 | 17 pilot，0 端到端 | P2 |

## 3. 目标架构

在现有七阶段之上增加三个辅助层，不改变原有阶段编号与回执格式：

```
question
  └─ [autopilot] hypothesis generation → screening → top-k
hypothesis
experiment_plan
cloud_execution
results
claim_ledger
  └─ [adversarial] attack → objections
  └─ [rebuttal] classify → executable rebuttal plan
draft
  └─ [rubric] mechanical checks + model review → score
```

三个辅助层都输出独立回执，不伪造阶段状态：

- `q-one-hypothesis-candidates-v1`
- `q-one-hypothesis-screening-v1`
- `q-one-rebuttal-plan-v1`
- `q-one-review-rubric-v1`

## 3.1 相关工作与设计借鉴

| 工作 | 核心做法 | 对本计划的修改 |
|---|---|---|
| ScientistTwo (arXiv:2609.19644) | 六 agent 闭环；Idea Generator → Evaluator → Analyzer → Writer → Peer-Review → Meta-Review | 闭环骨架与阶段划分 |
| AppliedScientist (arXiv:2609.14738) | 迭代修订对执行类缺陷有效 85.3%，对想法类仅 11.1% | rebuttal 只对执行类生成实验；novelty 显式标为闭环外 |
| Simjecture (arXiv:2611.03721) | 反例驱动证伪 + 假设修复；**数值仪器资格与科学论断评审分离** | rubric 的机械检查与模型评分必须分开报告，不能合成一个"通过" |
| Autonomous Research Agents (arXiv:2610.39620) | 审稿人**从记录重跑研究**再修改；跨模型家族评审 | P1 增加 replay 检查；rubric 记录模型家族，禁止自评 |
| Auto-Research Arena (arXiv:2610.35866) | **可采纳性（admissibility）与改进（improvement）分离** | 假设筛选先过滤不可执行/超预算，再比较分数 |
| RIDAR (arXiv:2610.31372) | 14 类科研诚信违规（RIVT）+ 运行时干预 | 新增诚信审计层；只实现可确定性判定的 6 类，其余标 `not_assessed` |
| VerifiedLab (arXiv:2610.37923) | PI / librarian / specialists / gate / critic；release 或 withhold | `meta_review` 增加 `withhold`；不把未检查当成通过 |
| RubricAtlas (arXiv:2610.36878) | 从专家报告挖掘 type-level rubric | P3 校准按论文类型共享 rubric，而非每篇重写 |
| Scientist World (arXiv:2611.08478) | 每篇论文变成可执行环境，1,000 个验证基线 | P2 增加 environment manifest 与基线注册表 |

## 4. 分阶段实施

### P0：闭环最小可用（本次实现）

实施状态（2026-11-05）：**已完成本地可逆部分**，未触发云端作业、
未调用付费模型、未上传。

| 项 | 文件 | 测试 |
|---|---|---|
| 假设生成 | `src/qone_life/research_factory/autopilot.py` | `tests/test_autopilot.py` |
| 假设筛选 | 同上 | 同上 |
| 反驳登记映射 | `src/qone_life/rebuttal_loop.py` | `tests/test_rebuttal_loop.py` |
| 反驳计划挂载 | `src/qone_life/research_production.py` | `tests/test_research_production.py` |
| 自动审稿 rubric | `src/qone_life/research_factory/review_rubric.py` | `tests/test_review_rubric.py` |
| CLI 接入 | `src/qone_life/cli.py` | 手工冒烟 |

**P0-6 科研诚信审计（2026-11-06 追加）**

- 新增 `src/qone_life/research_factory/research_integrity.py`。
- 采用 RIDAR RIVT 的 14 类定义（原文附录 A），但只对其中 6 类做
  确定性检查：`RF`、`CF`、`SR`、`CV`、`ODDC`、`ET`。
- 其余 8 类一律 `not_assessed`；`release=withhold` 除非全部通过。
- `meta_review.decide` 新增 `integrity` 输入：`violation → withhold`，
  `incomplete` 不允许 `stop`。
- 测试：`tests/test_research_integrity.py`、`tests/test_meta_review.py`。

18 篇同类系统的对比与距离评分见
`docs/AI_RESEARCHER_LANDSCAPE.zh-CN.md`；完整摘要索引见
`docs/research/auto-research-frameworks-2026-11.json`。

验证命令：

```bash
PYTHONPATH=src python3 -m pytest \
  tests/test_autopilot.py tests/test_review_rubric.py \
  tests/test_rebuttal_loop.py tests/test_research_production.py -q
```

**P0-1 假设生成器**

- 新增 `research_factory/autopilot.py`。
- `generate_hypotheses(question, model_call, n=5)`：
  - 要求模型返回严格 JSON 数组；
  - 每条必须含 `null_hypothesis`、`alternative_hypothesis`、
    `falsification_condition`、`novelty_rationale`、`required_resources`；
  - 解析失败或字段缺失 → 整批拒绝，不做部分接受。
- 无模型时 fail-closed，返回 `AutopilotError`，不生成占位假设。

**P0-2 假设筛选器**

- `screen_hypotheses(candidates, scorer, top_k=2)`：
  - `scorer` 返回 0–1 的代理分或 `None`；
  - `None` 记为 `inconclusive`，不当作 0 分；
  - 若 `inconclusive` 超过半数，整批 `blocked`；
  - 输出排序、分数、理由与筛选回执。
- `scorer` 必须是显式注入的可调用对象，禁止隐式联网。

**P0-3 反驳实验接线**

- 扩展 `rebuttal_loop.py`：
  - `plan_to_registrations(plan)` 把可执行异议转成
    `register_experiment_plan` 所需的字段；
  - 资源需求固定写 `cloud`，让 `plan_experiment` 自动置
    `approval_required=True`，从而 `execute_cloud` 拒绝自动执行；
  - 没有 run script 时只生成 `rebuttal-plan.json`，不伪造实验计划。
- 新增 `ResearchProduction.attach_rebuttal_plan(slug, plan)`：
  - 要求 `claim_ledger` 已通过；
  - 写入 `rebuttal/REBUTTAL_PLAN.md` 与 `rebuttal/plan.json`；
  - 回执绑定两个文件的 SHA-256。

**P0-4 自动审稿 rubric**

- 新增 `research_factory/review_rubric.py`。
- 机械检查（本地可复算）：
  - 论断账本 verified 比例；
  - 是否存在 blocked 论断；
  - 是否有 Limitations / Reproducibility 段落；
  - 引用条目数量。
- 模型评分（注入 `model_call`）：
  - novelty、rigor、clarity 三项 1–5 分；
  - 任一项缺失 → 该项 `inconclusive`，且不计算总分。
- 总分只在机械检查全过且三项评分齐全时计算。

**P0-5 门槛**

- 全部本地实现，不触发云端作业、不调用付费模型、不上传。
- 新增测试覆盖：解析拒绝、fail-closed、inconclusive 不冒充 0 分、
  approval_required 传播。

### P1：写作与迭代

实施状态（2026-11-06）：**本地可逆部分已完成，含 type-level rubric 与 reward-hacking 负样本**。

| 项 | 文件 | 测试 |
|---|---|---|
| 数字可追溯写作 | `src/qone_life/research_factory/writer.py` | `tests/test_writer.py` |
| 元评审决策 | `src/qone_life/research_factory/meta_review.py` | `tests/test_meta_review.py` |
| CLI | `research-write`、`research-decide` | 手工冒烟 |
| type-level rubric | `src/qone_life/research_factory/rubric_types.py` | `tests/test_rubric_types.py` |
| reward-hacking 负样本 | `rubric_calibration.py` | `tests/test_rubric_calibration.py` |

- `writer.py`：从 claim ledger + results 生成 LaTeX 骨架，禁止编造数字，
  所有数字必须能回链到 results 文件。
- `meta_review.py`：把 rubric 分数、adversarial verdict、rebuttal 结果聚合成
  一个「继续/停止/回退」决策。
- `research-iterate` CLI：一轮完整迭代，最多 N 轮，每轮写回执。

验收：

- 同一输入两次迭代产生可比较的分数轨迹；
- 分数不升时自动停止，不无限循环；
- 每轮都保留上一轮草稿哈希。

### P2：规模化

实施状态（2026-11-06）：**本地批处理 + 环境清单 + 方向多样性 + 预测筛选已完成**；
并发上限仍为 2，未改动云端执行器语义。

| 项 | 文件 | 测试 |
|---|---|---|
| 批量生成+筛选 | `research_factory/autopilot.py:run_batch` | `tests/test_autopilot.py` |
| CLI | `research-batch` | 手工冒烟 |
| environment manifest | `src/qone_life/research_factory/environment_manifest.py` | `tests/test_environment_manifest.py` |
| 方向多样性 | `src/qone_life/research_factory/direction_diversity.py` | `tests/test_direction_diversity.py` |
| 预测筛选 | `src/qone_life/research_factory/outcome_predictor.py` | `tests/test_outcome_predictor.py` |

- 把 `cloud_executor` 的并发上限从 2 提到可配置，默认仍为 2。
- `research-batch`：从 portfolio 取 top-k 家族，并行跑 P0 闭环。
- 每个作业独立目录、独立回执，失败不污染其他作业。

验收：

- 批量运行中单作业失败不影响其他作业；
- 汇总报告能定位每个失败作业的失败阶段。

### P3：质量校准

实施状态（2026-11-06）：**校准层代码与负样本已完成；人工评分仍缺**。

| 项 | 文件 | 测试 |
|---|---|---|
| 校准层 | `src/qone_life/research_factory/rubric_calibration.py` | `tests/test_rubric_calibration.py` |
| CLI | `research-calibrate` | 回执 `partial` |

已执行：3 个负样本（无论断账本、blocked 论断冒充发现、缺
Limitations/Reproducibility）全部被机械检查拦下，不给总分；
`human_alignment` 在缺人工评分时返回 `human_labels_missing`，
不算 0 分、不冒充校准通过。

回执：`research/pilot-bench-noise-floor/reports/p3-calibration/calibration.json`，
`status=partial`，SHA-256
`4c93898e34532e8c40f0aa85d5342318ec5332c01b9d9fe10d469fd492fe7a89`。

仍未执行：真实已录用论文语料 + 独立人工评分（至少 20 对）。
只有 `status=calibrated` 后，rubric 分数才能进入 acceptance 决策。

- 用 20–30 篇已录用论文做 rubric 校准，报告与人工评分的相关性。
- 用 10 篇已知有缺陷的稿做负样本，检查 rubric 是否能识别。
- 只有校准通过后，rubric 分数才能进入决策，否则仅作参考。

## 5. 证据与安全约束

- 所有新回执必须含 `schema`、`generated_at`、输入文件 SHA-256。
- 任何模型输出都视为不可信输入，必须经过结构校验。
- 任何 `None`/超时/解析失败都记为 `inconclusive`，不得静默降级为通过。
- 云端执行仍需 `approval_required` 门；本计划不改变该语义。
- 不上传、不投稿、不创建 public package。

## 6. 计算位置

| 任务 | 位置 |
|---|---|
| 单元测试、解析、回执生成 | 本机 |
| 假设生成/筛选的模型调用 | Magpie 网关（短调用） |
| 真实实验 | 云端执行器（AMD/ECS/Kaggle） |
| 长批量 | 云端，detached + checkpoint |

## 7. 风险

| 风险 | 缓解 |
|---|---|
| 模型生成看似合理但不可执行的假设 | 强制 falsification_condition + 筛选器 |
| 自动审稿分数被误当录用结论 | 文档与回执中显式声明边界 |
| 反驳循环无限扩张 | 每轮最多 top-k 条，且必须人工批准执行 |
| 规模化后回执爆炸 | 每作业独立目录 + 汇总索引 |
| 依赖外部模型导致不可复现 | 模型调用与回执解耦，记录模型名与提示哈希 |

## 8. 时间线（建议）

- 第 1 周：P0（本次）
- 第 2 周：P1 写作与迭代
- 第 3 周：P2 批量化
- 第 4 周：P3 校准 + 第一轮真实端到端

## 9. 完成定义

P0/P1/P2 完成的标准：

- 新增模块与测试全部通过；
- 不改变现有阶段编号与回执 schema；
- `research-rebuttal`、`research-autopilot`、`research-screen`、
  `research-review`、`research-write`、`research-decide`、
  `research-batch` 七个 CLI 命令可用；
- 文档记录命令、边界与未验证项。

当前验证结果（2026-11-06）：全量 **316 passed**（cleanroom 完整依赖环境，
22 subtests 通过）。此前 cleanroom 基线为 pytest 256 / unittest 230 /
desktop 42，现均已覆盖新增模块。

未验证项：

- Magpie 真实调用已用于 `research-review` 与 `research-adversarial`；
  `research-autopilot` / `research-screen` 仍只用注入假模型冒烟；
- 未在云端执行任何反驳实验（C02-C04 都是本地只读审计）；
- P3 校准未启动；
- 未提交、未推送、未上传。

### A3 amendment v1.1 与 P3（2026-11-06）

A3 的 runner 哈希漂移已按正式 amendment 处理：

- `amendments/preregistration-v1.0.0-frozen.json` 与
  `amendments/run_common_support-v1.0.0.py` 保留冻结字节；
- 主预注册升 `v1.1.0`，只重钉 runner 哈希
  `f688db9c70c01934a08eae4f343ca41a8f7656e702e89a4e53f8038c0c74a07c`；
  没有改任务、seed、支持集、门、bootstrap 次数或输出 schema；
- `--selftest` 改为从 `QONE_WORKSPACE_ROOT` 解析外部根路径；
- `SHA256SUMS.txt` 重新生成，覆盖所有 v1.1 文件。

云端 v1.1 双跑：`a3_v11_run1.json` 与 `a3_v11_run2.json` 字节一致，
SHA-256 `4fd64d0e3aa64f2f884de1295dc444574428f338da165c45c07062babd0a6ffb`，
F1-F5 全过，`decision.status=passed`，绑定 v1.1 prereg
`ae6f12e4dfec14770f7f2121af133dec9e78eea19e5f27f621de4ad60e520323`。

P3 校准层：`status=partial`，负样本 3/3 拦下；人工评分缺失，
不得把 rubric 分数当作录用/接受决策。

### 真实旧稿验收（2026-11-05）

对象：`research/pilot-bench-noise-floor`，完整记录见
`research/pilot-bench-noise-floor/reports/ai-review-20261105/RUN_REPORT.md`。

| 环节 | 结果 |
|---|---|
| 自动审稿 | 机械检查 5/6（2 条 blocked）；novelty 3 / rigor 2 / clarity 2；`total=null` |
| 对抗评审 | 定向 C02/C03/C04；C02 objected，C03/C04 clean，0 inconclusive |
| 反驳分类 | executable 1、out_of_loop 0、unclassified 0 |
| 元评审 | `rollback`：机械检查失败 + 1 条异议未关闭 |

这次验收同时暴露并修复了两个真实问题：

1. 6 列账本（状态在第 6 列）原本无法解析 → 改为按表头定位 `State/Status` 列。
2. 评审模型试图读文件并返回工具调用轨迹 → 提示禁止用工具，且把工具轨迹
   记为 `inconclusive`，不再当作异议。

验收边界：只覆盖 3 条论断，不是全稿结论；未执行反驳实验，未上传。

### 追加反驳实验（2026-11-05）

| 实验 | 结果 | 回执 |
|---|---|---|
| C02 哈希一致性 | `stands`：当前源码与 manifest 不一致，8+/5- | `d6fdb3ef…f8067fb` |
| C03 构造效度 | `narrowed`：源码已采用 A1 建议的窄主张 | `99e71d03…e83fa3` |
| C04 disjoint-field | `refuted`：3,200 boards 中 0 READABLE（3020 UNREADABLE + 180 MARGINAL） | `18834762…207b7` |

账本变化：C04 由 `candidate` 更正为 `blocked`；新增 C15（窄主张，verified）
与 C16（0 认证的 disjoint 测量，verified）。详情见
`research/pilot-bench-noise-floor/CLAIM_LEDGER.md` 与
`reports/ai-review-20261105/RUN_REPORT.md`。

## 11. 先导验证结果（2026-11-06）

完整矩阵已在 AMD 云实例执行：6 任务 × 3 seed × 3 变体 = 54 条轨迹，
188 次模型调用，804,272 tokens。报告与账本：

- `research/validation-20261106/REPORT.zh-CN.md`
- `research/validation-20261106/CLAIM_LEDGER.md`
- `research/validation-20261106/results.json`
- `research/validation-20261106/verification.json`

| 指标 | 结果 |
|---|---|
| 完成 / inconclusive | 44 / 10 |
| 输出哈希不符 | 0 |
| 独立重跑不一致 | 0 |
| 测试集参与选择 | 0 |
| 故障注入检出 | 10/10，正常对照 2/2 放行 |
| multi − single 符号检验 | 3 胜 5 负 2 平，p=0.73 |
| multi − no_rebuttal 符号检验 | 2 胜 4 负 4 平，p=0.69 |
| 乱序标签对照中位增益 | +0.004 ~ +0.019（个别 +0.052） |

10 条 inconclusive 全部是模型输出违反候选 schema（`null` strength、越界、
非 JSON），不是训练或回执故障。按协议保留为 inconclusive，未重试后当作完成。

### 对建设计划的修正

1. **停止**继续增加多智能体角色或提示层。现有证据不支持“角色分工带来更好的
   研究结果”，继续堆角色只会增加调用成本。
2. **优先**把预算放到三类缺口数据：送审版本对齐的论文—评审对、RIDAR 全量
   轨迹与人工标签、可执行的端到端复现任务（PaperBench 或等价基准）。
3. **保留**回执、重跑、测试集隔离和故障注入，这四项是本轮唯一稳定成立的能力。
4. 下一阶段的验收门槛：至少 20 个外部任务、每任务独立重跑一致、负对照无
   系统性增益、评审相关在留出 split 上仍为正。

## 12. 开放科研员五步推进（2026-11-06）

| 步骤 | 状态 | 结果 |
|---|---|---|
| 1. 保住已验证工作 | 完成 | commit `f298e2c`，835 个文件入库 |
| 2. PaperBench dev 沙盒 | 阻断 | 上游代码与 3 个 dev 任务文本已备齐；卡在 Docker Hub 拉取 `ubuntu:24.04` 构建 `pb-env` |
| 3. 代码生成 + 沙盒执行 + 隐藏测试 | 完成 | `research-code generate/execute/test`，7 项测试通过 |
| 4. RIDAR LLM 辅助语义标注 | 开发集完成 | 12 条：TP/FP/FN/TN = 3/0/3/6，precision 1.0，recall 0.5；未做留出 |
| 5. 10 个外部任务评测 | 准备中 | 已有 PaperBench 3 个 dev 任务，尚未构建 `pb-env`，未产生分数 |

### 第 3 步当前能力

`research-code generate` 只允许生成 `run(data) -> dict` 的 Python 函数；
`execute` 在独立临时目录、受限环境、超时与输出上限内运行；`test` 由主机
侧定义隐藏测试，测试内容不发给模型。这打破了固定候选 schema，但仍不是
任意自主代码：模型不能联网、多进程、读外部文件或执行 shell。

### 第 4 步当前能力

LLM 辅助标注只完成 12 条开发轨迹，没有留出结果。它显示零假阳性、低召回，
下一版必须改为轨迹分段窗口，并重新预注册；不能直接声称 RIDAR 检测器可用。

### 第 5 步当前边界

PaperBench 3 个 dev 任务的论文和 rubric 已就位；缺少 `pb-env:latest` 基础
镜像。因为没有镜像，不能跑 agent rollout、reproduction 或 grading，也不能
产生任何 PaperBench 分数。

### 轨迹级检测器预注册（2026-11-07）

已按“先冻结规则、后写代码”的顺序建立 40/20 切分与停线，结果见
`research/validation-20261106/ridar-detector/PREREGISTRATION_REPORT.zh-CN.md`。

三类目标在留出集的正例分别为 9 / 6 / 4，全部低于冻结的 10 条下限，按停线
规则停止。结论：当前 60 条 RIDAR 轨迹不足以对这 3 类做留出集轨迹级评估，
不产出“检测能力”数字。下一轮若要继续，必须扩大样本或重新预注册 act 级
评估，不能用本轮结果反推。
