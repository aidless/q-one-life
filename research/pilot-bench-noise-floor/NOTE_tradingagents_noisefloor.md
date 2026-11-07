# TradingAgents 判定结构 → 噪声地板论文：可用 / 不可用映射

> 说明：本笔记是分析产物，**不改论文正文**。遵守 AUTHORING_BRIEF.md 约束（只重组已注册 claim；禁发明数字/实验/引用；不升级 inconclusive/candidate；blocked 不入正文）。

## 1. 目标论文（真身）
- 稿：`q-one-life/research/pilot-bench-noise-floor/source/main.tex`（952 行，TMLR 模板 `tmlr.sty`）
- 标题：*When a Leaderboard Cannot Be Read: Three Rulers for the Noise Floor of LLM-as-Judge Evaluation*（见 `AUTHORING_BRIEF.md`；注意记忆里写成 "Three Principles"，实稿是 "Three Rulers"）
- 创作约束（`AUTHORING_BRIEF.md`）：只可总结/重组已注册 claim；禁发明数字、实验、引用、作者、许可证；不得把 `inconclusive` 升 `verified`、不得把 `blocked` 移入正文；上传/发布须另立用户动作。
- `CLAIM_LEDGER.md`：C02/C03 为 `blocked`；C04（真实公开榜、金标池与 ranked 系统不相交，产生 READABLE 判定）仍是 `candidate` 未达成。

## 2. 论文核心判据（据实摘录）
- 决策规则 `eq:rule`（`source/main.tex:174-175`）：leader 必须高于**最高**金标生成器，且超出量 > 声明阈值 δ；floor ≥ leader → `UNREADABLE`，超出 < δ → `MARGINAL`。比较用 max over generators 而非均值——「超过金标平均」不等于「超过最认同它的那个」。
- 决策域极窄（`source/main.tex:177`）：**≥3 个金标生成器，且该池是 ranked field 的真子集（strict subset）**。两个 m=2 语料失败第一条；m=25 构造与公开面板失败第二条（= Proposition 4）；人金集无模型金标。
- Proposition 4（`source/main.tex:196`）：当榜单排的正是造金的那些模型，floor 恒等于 leader 自身分数，margin 恒为 0，`MARGINAL`/`READABLE` 都不可达。
- 三类判决 + 两类拒绝（`source/main.tex:177,235`）：`READABLE`/`MARGINAL`/`UNREADABLE` 是判决；`UNDECIDABLE_DOMAIN_MISMATCH`（不共分母）与 `UNDECIDABLE_FLOOR_DEGENERATE`（<3 生成器）是拒绝。**拒绝 ≠ 判决**，拒绝仍把 floor/leader/差值/区间全打印但标为 reference。
- Related Work 已覆盖「多评委面板」一组（`source/main.tex:127` "Panels of judges in the wild"：verga2024juries / bedi2025medhelm / liu2025imperfect / potsawee-truthfulqa 17 judges）。
- 三 ruler：majority-vote floor / latent-variable / calibrated variant（§Method `source/main.tex:159+`；Table outcomes ~`:318-344`）。

## 3. TradingAgents 七角色结构（arXiv 2412.20138 v7）
4 分析师**并行**收集（fundamental/sentiment/news/technical）→ 多空研究者 n 轮**辩论** + facilitator 选 prevailing → Trader 出信号 → Risk 三视角（seeking/neutral/conservative）n 轮**辩论** → Fund Manager approve/execute。全 ReAct、共享 global state、结构化报告为主 / 自然语言只用于辩论（避免 telephone effect）。辩论轮次原文为 "nn rounds" 占位符，未给固定值。

## 4. 逐层映射（可用 / 不可用）
| TradingAgents 层 | 对应论文判据 | 可用? | 理由 |
|---|---|---|---|
| 4 分析师「并行」独立收集 | 多个独立 gold generator / judge 独立打分 | 部分可用 | 只有保持**独立不通信**才符合 floor 的「独立复现」前提；一旦共享上下文即退化 |
| 多空辩论 / risk 三视角辩论 | ——（无对应，且**违反**前提） | **不可用** | 辩论=judge 共享上下文、相互影响 → judge 相关，floor 变成「辩论收敛后的自洽度」而非「独立复现率」，正是 Proposition 4 / §panels 要拒绝的读数 |
| Fund Manager 最终 approve/execute（门控） | 决策规则 `eq:rule` + 拒绝出口 | 可用（精神） | 都是 gate；关键保留「明确拒绝」出口（对应 `UNREADABLE` / `DOMAIN_MISMATCH`） |
| 结构化报告为主 / NL 只用于辩论 | 结构化 schema + 打印字段 | 可用 | 与论文「拒绝也打印 floor/leader/区间」一致 |

## 5. 结论（诚实）
- TradingAgents 最有价值的用法是**反面 / 边界案例**，不是正面模板：它恰好演示「多代理辩论式评测」为何在 noise floor 意义下 `UNREADABLE`——辩论层让判定者相关，破坏「独立复现」这条承重前提。
- 论文 Related Work 的「Panels of judges」组目前只谈**独立多评委面板**，未区分**辩论式多代理框架**这一类别。可增补一句 argument（**非 finding**）：辩论式框架把 judge 相关化，其 floor 不可读——按 `AUTHORING_BRIEF.md` 只能作论证，不得包装成测量/数字，不得升级 C04。
- 若真要借其结构做评测：只借「并行独立收集 + 分层门控 + 显式拒绝 + 结构化输出」，**删掉所有辩论层**；且 judge 池必须与 ranked field 不相交（≥3 且真子集），否则 Proposition 4 直接判 `UNREADABLE`，无信息量。
