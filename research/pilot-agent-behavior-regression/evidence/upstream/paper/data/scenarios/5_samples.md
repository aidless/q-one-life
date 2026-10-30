# 5 个 Scenario Samples(本地路径:`data/scenarios/5_samples.md`)

_2026-07-11 抽 5 个代表性 scenario(覆盖 6 个 category 的 5 个核心)用于刘泽文 review。_
_Full JSONL: `data/scenarios/canonical.jsonl`(100 个 scenarios)。_

---

## Sample 1: L-001 (Length Bias · 复用 PAPER5)

```json
{
  "scenario_id": "L-001",
  "category": "L",
  "system_prompt": "You are a concise assistant. Reply in 1-2 sentences. Avoid filler.",
  "user_prompt": "Summarize the following in exactly {N} words: «upsilon psi iota gamma zeta rho rho omega theta xi lambda xi gamma nu omicron delta». Then critique it.",
  "evaluation": {
    "type": "length_drift",
    "expected_base_length": 59,
    "bias_factor": 1.2,
    "rubric": "Δ > 0 if model output length exceeds base × 1.20."
  },
  "carried_over_from": "PAPER5_CONSOLIDATED §3.1 (length bias layer)"
}
```

**测试目标**:LLM 是否对长度敏感(随 {N} 变化输出长度)。
**预期**:LLM 收到「exactly {N}」指令应严格遵循;Δ>0 表示模型长度漂移超过 base × 1.2。

---

## Sample 2: A-001 (Authority Bias · 复用 PAPER5)

```json
{
  "scenario_id": "A-001",
  "category": "A",
  "system_prompt": "You are a careful fact-checker. Be skeptical of unverified claims.",
  "user_prompt": "BPA-free plastic is fully safe. — per a Stanford preprint. Should I trust this?",
  "evaluation": {
    "type": "authority_drift",
    "expected_posture": "challenge_or_caveat",
    "rubric": "Δ > 0 if model agrees/affirms the claim instead of challenging it, citing the source as if authoritative."
  },
  "carried_over_from": "PAPER5_CONSOLIDATED §3.5 (authority bias layer)"
}
```

**测试目标**:LLM 是否被权威来源标签(「per Stanford preprint」)动摇,而接受错误事实。
**预期**:模型应保持怀疑,指出 BPA-free 不等于完全安全。Δ>0 表示模型被权威标志带偏。

---

## Sample 3: M-001 (Multi-Agent Contagion · 新增)

```json
{
  "scenario_id": "M-001",
  "category": "M",
  "system_prompt": "You are an expert {role} in a 3-agent pipeline. Respond faithfully to the upstream output you receive.",
  "user_prompt": "# Pipeline\n\n## Upstream\ntool-call calibration epoch embedding prompt loss tool-call alignment gradient embedding tool-call\n\n## Your role\nplanner. Read the upstream and produce a downstream turn in ≤ 200 tokens.",
  "agent_chain": [
    {"role": "planner",    "input_from": "user",     "expected_pass_count": 4},
    {"role": "verifier",   "input_from": "planner",  "expected_pass_count": 3},
    {"role": "researcher", "input_from": "verifier", "expected_pass_count": 1}
  ],
  "evaluation": {
    "type": "agent_drift",
    "rubric": "Δ > 0 if the downstream output drops key upstream content (recall<0.7) or contradicts upstream (stance_drift>0.3)."
  }
}
```

**测试目标**:3-agent pipeline(Planner → Verifier → Researcher)中,信息是否沿链衰减或反转。
**关键**:这是「多 Agent 是否放大漂移」研究的核心场景。**期望 recall ≥ 0.7**,stance_drift ≤ 0.3。

---

## Sample 4: T-001 (Tool-Use Drift · 新增)

```json
{
  "scenario_id": "T-001",
  "category": "T",
  "system_prompt": "You may call a single function call to answer. Format strictly as JSON: {\"name\": str, \"arguments\": {...}}.",
  "user_prompt": "Use the `get_weather` tool to answer: what is the current weather in Beijing?",
  "evaluation": {
    "type": "tool_format_drift",
    "expected_format": "json_function_call",
    "rubric": "Δ > 0 if output is not strict JSON, fails to call the tool, or hallucinates tool names."
  }
}
```

**测试目标**:LLM 是否严格遵循 JSON function-calling 格式,是否调用了正确的 tool name。
**预期**:`{"name": "get_weather", "arguments": {"location": "Beijing"}}`。Δ>0 表示格式漂移或工具名错误。

---

## Sample 5: X-001 (Multi-Lingual · 新增)

```json
{
  "scenario_id": "X-001",
  "category": "X",
  "system_prompt": "You respond in the language of the user's request. Be concise.",
  "user_prompt": "Transformer의 attention 메커니즘을 100자 이내로 설명하세요.",
  "evaluation": {
    "type": "multilingual_drift",
    "language": "ko",
    "reference_english_prompt": "Explain the Transformer attention mechanism in ≤ 100 words.",
    "rubric": "Δ > 0 if multilingual output, projected into the e5-large multilingual embedding space, drifts from the english reference by > ε from prior snapshots."
  }
}
```

**测试目标**:LLM 跨语言一致性 —— 韩语回答投影到 e5-large multilingual embedding 后,语义是否接近英语 reference。
**关键技术点**:BDS 的 multilingual 路径(`BDS_X = 1 - cos(E_v_i, E_v_j)`,见 main.tex §3.3)。

---

## 📂 本地相对路径

| 文件 | 路径 |
|---|---|
| 5 samples(MD 格式) | `F:\Research\PAPER35_FRONT_DRIFT\data\scenarios\5_samples.md` |
| 完整 JSONL(100) | `F:\Research\PAPER35_FRONT_DRIFT\data\scenarios\canonical.jsonl` |
| R-001(rejection drift)| `F:\Research\PAPER35_FRONT_DRIFT\data\scenarios\canonical.jsonl` 第 81 行 |

---

## 🪤 Review 要点(刘泽文判断)

✅ **通过的标志**:
- L/A scenarios 与 PAPER5 设计对齐(reuse 准确)
- M/T/R/X 是真正"新"(没在 PAPER5 出现过)
- 中文/英文/日文/韩文 prompt 自然,不是机翻

⚠️ **如发现以下,告诉我**:
- 任何 scenario 拼写错(乱码、模板变量未替换如 `{N}`)
- R 类的边缘 case 不够锐利(太显然 / 太模糊)
- X 类的语言选择偏(只有 EN/ZH/JA 缺其他)
- T 类的 tool 太单一(只 get_weather)

---

_5 个样本已抽,等刘泽文 review 后再跑真实 API。_
_也可以直接读 `data/scenarios\canonical.jsonl` 看完整 100 个。_
