# PAPER6 实验协议 (W1 草稿, 2026-08-16 缩规模更新)

> 状态:W1 — 协议框架 + 已完成缩规模试点（N=7/f=2, T=1000, 5 seeds, 合成数据, 全表存档）
> 按 2026-08-12 接管计划 D 约束：缩规模、公开数据优先、≤120 cells 试点
> 全部数值(N, f, attack models)在 protocol_v1 锁定前可调

---

## 1. 实验目标

**核心问题**:在 N 个 LLM verifier 投票场景中,f 个 verifier 被攻击者"capture"(产出系统性偏差),决策正确性如何?我们提出的 \textsc{CRV} 协议相比 5 个 baseline 提升多少?

**次要问题**:
- capture 攻击模型不同(prompt / rubric / majority bias)→ CRV 鲁棒性差异
- N 和 f 不同(N=5/7/10,f=1/2/3)→ 协议扩展性
- 历史一致性窗口长度 → 协议敏感性

---

## 2. 实验设计

### 2.1 实验矩阵(2026-08-16 缩规模版, 已执行)

| 维度 | 取值 | 状态 |
|---|---|---|
| N(verifier 数) | {7} 主表; {5,7,10} sweep | ✅ 已跑 (benchmark_persist.py) |
| f(capture 数) | {2} 主表; floor(N/3) sweep | ✅ 已跑 |
| Attack model | {prompt-injection, rubric-injection, majority-bias} | ✅ 已跑 (persist_tables.py) |
| Dataset | 合成生成器 (校准至 leung2026rubricllm 统计量) | ✅ 已跑 |
| Baseline | {majority, BFT-PBFT, weighted, trust-score, verifier-chain} | ✅ 7 方法 |
| Proposed | \textsc{CRV} (已并入 trust-family 评估) | ✅ |

**主报告 cell 数**:4 scenarios × 7 methods × 5 seeds × T=1000 = 140 cells
**Ablation**:N sweep + f sweep → 额外 3×7×5×4×T=1000 cells (ensemble_sweep)

### 2.2 数据集

| Dataset | 公开 | 用途 |
|---|---|---|
| 合成生成器 (benchmark.py gen_scenario) | ✅ | 主战场, 校准至发布统计 |
| HELM / TruthfulQA 真实验证 | ✅ | 后续工作 (Real-LLM validation, 已在正文声明 sketch) |

### 2.3 攻击模型(已实现)

1. **Prompt injection** — 输出正确补集 (确定翻转)
2. **Rubric injection** — 随机比例翻转标签
3. **Majority bias** — 模仿其余 verifier 的运行中位数

### 2.4 Baseline

| Baseline | 来源 |
|---|---|
| Majority voting | 经典 |
| BFT-PBFT | Castro-Liskov 1999 简化版 |
| Weighted voting | trust score 单维度 |
| Verifier-chain | 串行过滤,后续 verifier 看到前者输出 |

### 2.5 Proposed: \textsc{CRV}

- 公式:weight_i = trust_i × (1 - inconsistency_i)
- trust_i:历史一致率 EMA
- inconsistency_i:与群体中位投票的偏差指数

---

## 3. 评估指标

| 指标 | 公式 | 用途 |
|---|---|---|
| Decision correctness | 聚合决策 == ground truth | 主要 KPI |
| Capture detection rate | 真正被识别的攻击 verifier / 总攻击 verifier | 安全 KPI |
| False positive rate | 正常 verifier 被误判为攻击 / 总正常 verifier | 副作用 KPI |
| Cost | compute / token | 工程 KPI |

---

## 4. 数据文件(2026-08-16 存档)

| 文件 | 内容 |
|---|---|
| experiments/benchmark_results/benchmark_table.json | 主表 S1-S4 × 7 方法 (5 seeds, T=1000) |
| experiments/benchmark_results/per_attack_table.json | per-attack 表 (3 攻击 × 7 方法) |
| experiments/benchmark_results/ensemble_sweep.json | N∈{5,7,10} sweep |
| experiments/pilot_results/summary_v2.json | 摘要 pilot 数字 (n=4000) |

**生成脚本**:benchmark_persist.py / persist_tables.py / benchmark.py / per_attack.py

---

## 5. 结论(负结果, 2026-08-16)

主表负结果: majority 在 4 scenarios 中 3 个最佳 (0.889/0.553/0.459/0.843); trust 方法持平或落后 1-3pp; \textsc{Atv} 从不胜出。结构解释: capture 与 honest-but-wrong 统计不可区分 → 偏差规则必然误伤诚实少数。

---

## 6. 时间表(更新)

| 周 | 工作 | 状态 |
|---|---|---|
| W1-W6 | 协议 + 实现 + 合成试点 | ✅ 完成 |
| W7 | 真实本地模型 verifier traces (预注册) | ⏳ 待预算/机器 (正文已声明 sketch) |
| W8 | TMLR 投稿 | 待用户拍板 |

---

_最后更新:2026-08-16 · DSH Agent (MISSION papers-takeover-all-2026, P5)_