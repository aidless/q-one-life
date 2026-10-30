# Q-One 简历项目包

## 一句话定位

> Q-One：本地优先、证据可审计的个人决策 Agent。普通 Agent 给出建议；Q-One 同时绑定候选、输入摘要、来源和可复算回执，无法验证时回退规则或拒绝发布。

## 30 秒介绍

“这是一个独立开发的本地 AI 决策桌面应用。前端是 Electron/TypeScript，业务层是 FastAPI/SQLite，通过 PyInstaller sidecar 和一次性 capability 隔离本地服务。它没有模型也能完成目标、推荐、行动和复盘；可选 Qwen3-0.6B 本地推理，失败时自动回退规则。我重点做的是消费级运行边界和证据链：上下文隔离、跨平台锁、AES-256-GCM 备份恢复、稳定错误码、trace hash 以及 Research Factory 的 claim 门禁。”

## 简历主条目

### 版本 A：AI 应用 / Agent 工程

**Q-One｜本地优先、证据可审计的个人决策 Agent（独立开发）**

- 设计 Electron/TypeScript + FastAPI/SQLite + PyInstaller sidecar 架构，使用随机回环端口、一次性 256 位 capability、`contextIsolation` 和最小 preload API 隔离本地服务。
- 实现规则与本地模型双路径推荐；固定 Qwen3-0.6B GGUF、SHA-256 校验和 OpenAI-compatible loopback provider，模型缺失或格式失败时安全回退。
- 实现 AES-256-GCM 备份、Argon2id 恢复密钥、原子迁移、staging 恢复和跨平台文件锁，故障路径保留原数据。
- 建立可复算验证链：干净源码快照安装后，178 个 pytest、88 个 unittest、42 个桌面单测和 5 个真实 Electron E2E（含本地模型、benchmark 与截图采集）通过；6 个固定任务在两种推荐路径下均完成目标匹配与 trace 绑定。

### 版本 B：LLM 评测 / Agent Eval

**Q-One Research & Evaluation Factory｜可审计 Agent 与论文证据门禁（独立开发）**

- 构建覆盖 17 个 research pilot 的 claim/evidence 账本，将论断绑定到文件哈希、字段复算和 clean-room compile，阻断 85 个未闭合 claim 进入发布候选。
- 设计确定性规则基线与本地模型对照 harness，对 6 个固定任务记录目标匹配、trace 绑定、可执行性、延迟和 Electron 工作集；规则均值 55ms，本地模型均值 4,540ms。
- 将引用、候选归档、source identity、arXiv package audit 和 review packet 做成稳定 JSON schema；29/29 当前引用键解析成功。
- 所有结论由 `artifacts/resume-kit/evidence.json` 与 `SHA256SUMS.txt` 绑定，明确区分工程通过、内部证据和科学就绪。

### 版本 C：桌面 / 全栈平台

**Q-One Desktop｜本地优先 AI 桌面运行时（独立开发）**

- 交付 Electron 主进程、preload、Python sidecar 生命周期、单实例、数据迁移、崩溃恢复、日志脱敏和双语消费级界面。
- 设计会话级安全边界：静态页面可匿名加载，全部 `/api/*` 需要 capability，危险桌面操作另需 control token；外部导航和 Renderer 秘密访问被拒绝。
- 构建 NSIS/DMG/AppImage/deb 发布基础、签名门、更新清单验证、SBOM 与 SHA-256 证据；未签名产物被明确判定为不可公开发布。
- 建立固定任务 benchmark、演示截图和可复现 clean-room 脚本，当前 Linux x64 真实链路通过。

## 证据表

| 指标 | 已验证结果 | 能说明什么 | 不能说明什么 |
|---|---:|---|---|
| Python pytest | 178 passed，32 subtests | 业务、恢复、研究门禁测试通过 | 真实用户效果 |
| unittest | 88 passed | 独立测试入口一致通过 | 外部研究有效性 |
| 桌面单测 | 42 passed | TypeScript 模块行为通过 | 三平台安装成功 |
| Electron E2E | 5 passed | 真实 sidecar + 固定 Qwen 模型闭环、benchmark 和截图采集 | 公开发布质量 |
| 规则 benchmark | 6/6 匹配、trace-bound、actionable | 无模型路径可完成固定任务 | 推荐质量普遍优秀 |
| 本地模型 benchmark | 6/6 匹配、trace-bound、actionable | 混合路径在当前机器可运行 | 收益、留存或用户偏好 |
| 规则延迟 | 平均 55ms | 当前固定任务上的本地规则时延 | 其他硬件/任务 |
| 模型延迟 | 平均 4,540ms | 当前 CPU 环境下本地模型时延 | GPU 或其他模型 |
| Research Factory | 17 pilots，85 blocked claims | 发布门禁能阻断证据不足内容 | 论文录用或科学正确 |

## 推荐投递方向

- AI 应用工程师。
- Agent 应用 / Agent Runtime 工程师。
- LLM 评测、Agent Eval、可信 AI 工程。
- 本地优先桌面端或全栈平台工程师。

暂不作为主成果投递：

- 以已发表论文或科研录用为主要考核的纯研究岗。
- 要求生产级三平台发布、真实用户规模或商业收入的岗位。

## 明确不要写

- “支持三平台正式发布。”
- “已发表多篇 arXiv 或全自动产出论文。”
- “生产级、百万用户、高并发。”
- “自研大模型。”
- “端到端加密。”
- 把 85 个 blocked claim 写成科研成功数量。
- 把 6 个工程任务的 6/6 写成模型质量或真实收益。

## 面试追问

### 为什么不是普通 CRUD + LLM？

因为核心约束在失败路径：本地服务的 capability 边界、规则降级、恢复失败不覆盖原数据、trace 与 claim 不能闭合时拒绝发布。普通 CRUD 不需要同时证明这些。

### 为什么规则路径也值得保留？

它提供离线可完成性和确定性基线。模型是增强项，不是完成目标的前置条件；模型不可用时用户仍能创建目标、接受行动、完成反馈和恢复备份。

### benchmark 为什么只有 6 个任务？

这是工程验收集，不是论文实验。目的是防止“能演示一次”冒充稳定闭环，并让延迟、实际 provider、trace 绑定和内存可以复算。下一阶段才需要扩大任务集、多人标注与外部基线。

### 这个项目最大的不足？

缺少签名后的三平台干净机器安装记录、真实用户测试和独立科学评审。当前证据足以支持工程能力描述，不足以支持商业成功、科研结论或公开发布承诺。

## 配套资产

- 架构图：`docs/images/qone-evidence-runtime-architecture.png`
- 三分钟脚本：`docs/demo/QONE_3_MINUTE_DEMO.zh-CN.md`
- 真实界面截图：`artifacts/resume-kit/demo/`
- 机器可读证据：`artifacts/resume-kit/evidence.json`
- 校验清单：`artifacts/resume-kit/SHA256SUMS.txt`
