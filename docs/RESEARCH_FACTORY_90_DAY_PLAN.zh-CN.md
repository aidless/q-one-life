# Q-One Research Factory v2：90 天迭代计划

日期：2026-10-27（D1）至 2027-01-24（D90）

## 1. 结论先行

下一阶段不是让模型“凭空写 131 篇论文”，而是把 Q-One 变成一条可审计的论文生产系统：

1. 131 个论文族全部获得人工可审核的状态和下一步；
2. 证据充分的论文可以由 Agent 从 Claim Ledger 起草、编译、打包；
3. 证据不足的论文只能生成补证据或补实验计划，不能自动补数字；
4. 首批打通 5 篇试点，形成可复用模板，再按批次扩产；
5. arXiv 上传、账号、作者、许可和最终提交始终保留为用户门。

“所有论文发 arXiv”拆成两个不同目标：

- **组合覆盖 100%**：每个发现都有规范项目、状态、处置和下一步，不丢失旧稿与负结果。
- **提交覆盖不承诺 100%**：只有通过证据门、独立评审门和打包门的项目才进入 arXiv 准备队列。当前 131 个族不能都自动视为独立、可投论文。

## 2. 当前基线

已记录事实：

- 发现 704 个论文项目根；
- 归并为 131 个论文族；
- 255 个精确重复根被合并；
- 200 个标题版本变体被归族；
- 118 个支持对象与论文族分开；
- 当前仅 ARC 有第二阶段证据覆盖层；
- ARC 11 条 Claim 中 9 条 verified、1 条 inconclusive、1 条 blocked；
- 全局就绪分保持 `null`。

因此 D1 的真实状态是“可观测”，还不是“可批量生产”。

### 本次已经落地的第一切片

- 新增 `research-triage`：131 个族已生成生产队列，人工处置仍全部保留为 `unreviewed`；
- 新增 `research-scaffold`：五个 pilot 均有不修改原稿的外置覆盖层；
- Paper11 覆盖层已绑定 20 条 Claim、20/20 ledger PASS、隔离编译回执和可解包重编的内部 arXiv candidate archive；
- Gemma 覆盖层已绑定 8 条 Claim（7 verified、1 blocked），并明确本地稿与远端源哈希不一致；
- Noise Floor、f-acceptance 的现有 LaTeX 源树已通过机械包检查；
- 机械包检查、cleanroom 编译和 candidate archive 都明确 `ready_for_upload=false`，未执行任何上传。

## 3. 里程碑

| 日期 | 交付物 | 通过条件 |
|---|---|---|
| D1–D15 | Research Factory 控制面：自动分流、优先级因子、论文覆盖层脚手架、后续行动计划、机械 arXiv 包检查 | 131 个族全部生成生产队列；任何建议处置都不覆盖人工状态；5 个试点各有覆盖层和明确阻塞；包检查能对缺失引用、绝对路径、占位符和危险文件失败 |
| D16–D30 | 131 个族的首轮人工处置：`arxiv-ready / repair / merge / archive / unreviewed` | 不再是 131 个全部 `unreviewed`；重复版本有规范源；合并、归档和放弃都保留路径与理由；不把未知当 0 分 |
| D31–D45 | Top-20 证据闭环：Claim Ledger、数字复算、引用解析、独立方法/统计评审 | Top-20 每条数字论断可指向证据字段和复算命令；没有无证据强断言；0 个未关闭 Critical；所有 unresolved 明确列出 |
| D46–D60 | Agent 起草闭环：文献、novelty、PAPER_PLAN、章节草稿、图表计划、审阅循环 | Agent 只能重排和表达已登记 Claim；新增数字必须触发证据缺失；中英文模板均可恢复；草稿与源哈希绑定 |
| D61–D75 | 首批 5 篇 arXiv 包：clean-room 编译、BibTeX、元数据、许可证、哈希、PDF 文本检查 | 5 篇各自通过机械打包；至少 3 篇通过证据与独立评审；未通过的论文保留为内部包，不进入公开提交 |
| D76–D90 | 批次扩产与 Research Factory 1.0 RC | 下一批 10 篇按同一流水线进入准备队列；0 个未关闭 P0/P1；复现实验记录、失败记录和包哈希齐全；上传仍由用户逐篇授权 |

日期计算：D1=`2026-10-27`，D15=`2026-11-10`，D30=`2026-11-25`，D45=`2026-12-10`，D60=`2026-12-25`，D75=`2027-01-09`，D90=`2027-01-24`。

## 4. 五个首批试点

| 顺序 | 论文 | 优势 | 当前硬阻塞 | 第一阶段出口 |
|---|---|---|---|---|
| 1 | Paper11 / Harness Selection | 已有 Claim Ledger、引用核验、确定性分析和 arXiv 构建历史 | 需要把当前 v3 源、Claim、分析、PDF 和包回执绑定到同一哈希 | 建立覆盖层；重跑 ledger、数字、引用、编译和源包一致性检查 |
| 2 | Benchmark Noise Floor | 已有独立评审、完整 TeX 包和计算证据 | producer baseline 与“排名不可读”之间仍有概念效度缺口 | 决定重构为“共识金标审计空转”还是补独立校准；把决定写成显式论文范围 |
| 3 | f-acceptance / McNemar | 有真实、可定位、边界清楚的软件审计案例 | 需要将统计解释、接口承诺、当前源码和复现包重新绑定 | 关闭已识别的统计/接口问题；验证干净目录计算复现；建立 arXiv 覆盖层 |
| 4 | Gemma Tool Selection | 有公开数据包、复现实验、交叉模型诊断和 Kaggle 发布回执 | 本地 Markdown 与当前远端发布源哈希不一致 | 建立第二阶段覆盖层；修复源身份；形成可编译 arXiv source |
| 5 | ARC-AGI-3 Attribution | Claim Ledger 已建立，发布回执与提交血缘完整 | 本地稿不等于已发布源；官方 scoring methodology 未落盘 | 恢复已发布源字节；关闭 C09/C10；再生成 arXiv source |

## 5. Agent 自主等级

| 等级 | Agent 可以自动做 | 不能做 |
|---|---|---|
| L0 发现 | 扫描、哈希、去重、聚类、生成队列 | 猜测质量和录用概率 |
| L1 计划 | 生成 Claim 缺口、实验计划、审稿计划和投稿包清单 | 声称实验已经执行 |
| L2 写作 | 依据已登记证据起草、改写、压缩、生成图表说明 | 新增没有证据的数字、引用、作者和回执 |
| L3 验证 | 运行已授权本地测试、复算、编译和包检查 | 消耗付费/GPU 资源而不经授权 |
| L4 修订 | 根据证据和评审逐条修改草稿 | 把模型评审当成录用结论 |
| L5 打包 | 生成 arXiv source、BibTeX、manifest、哈希和干净目录回执 | 自动上传、发布、改账号或选不可逆许可证 |

这套等级是“自主产出论文”的安全含义：系统能完成大量可验证工作，但科学事实与外部动作仍需门禁。

## 6. 量化口径

Research Factory 不生成论文总分。它记录：

- `production_priority`：生产排序，只使用 Claim Ledger、BibTeX、PDF、evidence 目录、目标、状态、最近改动和试点 pin 等可观察信号；
- `claim_evidence_coverage`：有证据字段的 Claim 数 / 已登记 Claim 数；
- `claim_recomputation_coverage`：有可执行复算的数值 Claim 数 / 数值 Claim 数；
- `citation_verification_coverage`：已解析引用数 / 引用总数；
- `unresolved_critical`：未关闭 Critical 数；
- `package_completeness`：通过的包检查项 / 适用项；
- `source_identity`：本地源哈希与发布源哈希是否一致。

所有分母必须明确。未知、缺字段和未执行都不能转成 0 分或“通过”。

## 7. 门禁

### Claim 门

- 每个数字指向证据文件、字段、单位和复算命令；
- `blocked` Claim 不进入摘要、正文、图表或结论；
- `inconclusive` 只能使用保留条件的表述；
- 因果关系必须有人工或实验隔离，不由模型推断。

### 评审门

- Critical 必须关闭；
- Major 必须关闭或记录接受风险的理由；
- 模型评分只能作为线索；
- 评审回执必须绑定当前稿哈希。

### 包门

- 主文件、相对路径、输入文件、图、书目和清理规则通过；
- clean-room 编译成功；
- PDF 与 source 哈希进入 receipt；
- 作者、分类、许可证和摘要由用户作最终决定。

### 外部门

- arXiv 登录、上传、replacement、公开仓库、Zenodo DOI；
- 付费模型、GPU、云资源；
- 对外发布作者身份、邮箱、许可证和未发表数据。

## 8. D1–D7 开工顺序

| 日 | 工作 | 验收 |
|---|---|---|
| D1 | 生成 131 族生产队列；五个 pilot 固化 | priority、factor、suggestion、人工 disposition 分列 |
| D2 | 给 Paper11、Noise Floor、f-acceptance、Gemma、ARC 创建外置覆盖层 | 原稿零改动；每层 `research-validate` 可运行 |
| D3 | 为 Gemma 建立 Claim Ledger 和源身份记录 | 本地/远端源哈希不一致被明确记录 |
| D4 | 对 Paper11 v3 重跑 Claim、数字、引用和 package 检查 | 每个失败/缺失都有稳定 blocker |
| D5 | 对 Noise Floor 和 f-acceptance 做机械包检查 | 不把“能编译”写成“科学可投” |
| D6 | 对五个 pilot 生成 `research-plan` | 每篇都有按优先级排序的下一步和 external gate |
| D7 | 全量回归与工件哈希 | pytest、unittest、ruff、schema、artifact hashes 全通过 |

## 9. 批次策略

- 每批最多 5 篇进入深度证据审阅；
- 每篇先完成源身份，再登记 Claim；
- 同一时间只允许一篇进入 clean-room 打包；
- 任何一篇出现 P0，停止该篇而不是降低门禁；
- 每批结束重新扫描组合，防止新版本造成旧回执漂移；
- “完成”仅指当前哈希下的证据和工作完成，不是录用或发表。

## 10. D90 完成定义

满足以下条件才算 Research Factory v2 完成：

- 131 个论文族全部有规范源、状态、人工处置和下一步；
- Top-20 的证据缺口可计算，未知仍保持 unknown；
- 5 个试点有可恢复的 Claim、复现、评审和包工件；
- 至少 3 篇生成内部 arXiv-ready candidate package，但未自动上传；
- 1 篇在用户明确授权后完成真实 arXiv 提交的预检彩排，而不是由 Agent 自行提交；
- 所有失败、负结果、被归档版本和哈希均可追溯；
- 不宣称 131 篇都可投、录用、获奖或已上 arXiv。
