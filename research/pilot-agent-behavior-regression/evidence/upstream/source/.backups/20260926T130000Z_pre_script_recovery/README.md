# PAPER35 — Agent Behavior Heterogeneity and Reproducibility (local models)

_2026-07-11 启动；2026-08-16 状态更新。TMLR (rolling submission)。_

> **✅ Status: manuscript complete with real local-model data.**
> full_run 1,200 cells (4 local models × 100 scenarios × 3 seeds) done;
> 3-agent chain pilot (10 M/T scenarios × 3 seeds × 4 models) done and
> written into main.tex §Multi-Agent Chain Divergence (Pilot) with
> recomputable numbers (`experiments/multi_agent/reproduce_chain_analysis.py`);
> analysis at `experiments/full_run/analysis/full_run_stats_20260813.json` +
> `experiments/multi_agent/analysis_repro_20260816.json`.

## 🎯 TL;DR

| | |
|---|---|
| **Title** | Agent Behavior Heterogeneity and Reproducibility Across Local LLM Families |
| **Venue** | TMLR (Diamond OA, Rolling submission) |
| **Scope change (2026-08)** | temporal-drift framing dropped: local models have no time snapshots → cross-model heterogeneity + seed reproducibility (Q1/Q2) |
| **Data** | 4 local Ollama models (deepseek-r1:7b / qwen2.5-coder:7b / qwen2:7b / qwen3:4b), temperature 0, 100 scenarios, 3 seeds |

## 📦 Current State (2026-07-11 15:00)

```
PAPER35_FRONT_DRIFT/
├── README.md                    ← this file
├── OPERATION_RECORD.md          ← completion protocol
├── protocol.md                  ← full reproducibility protocol (13.5 KB)
├── main.tex                     ← skeleton (12 pages, TMLR template) — 20.7 KB
├── refs.bib                     ← bibliography (carried over from PAPER5)
├── math_commands.tex            ← math macros
├── tmlr.sty                     ← TMLR style
├── tmlr.bst                     ← TMLR bibliography style
├── scripts/
│   ├── scenario_generator.py    ← generates 100 canonical scenarios
│   ├── run_protocol.py          ← drives 6 frontier models
│   ├── bds_evaluator.py         ← computes Behavior Drift Score
│   └── (future) drift_detector.py ← multi-agent amplification (follow-up work)
├── data/                        ← (created at runtime)
│   └── scenarios/canonical.jsonl
├── experiments/                 ← raw outputs
├── figures/                     ← output figures
├── reviews/                     ← review records
└── supplementary/               ← supplementary materials
```

## 🚦 Quick-start

```bash
# 1. Generate the 100 canonical scenarios (deterministic, seed=20260711)
python scripts/scenario_generator.py --out data/scenarios/canonical.jsonl

# 2. Set API keys (do NOT hard-code in scripts)
set "OPENAI_API_KEY=sk-..."           # OpenAI
set "ANTHROPIC_API_KEY=sk-ant-..."    # Anthropic
set "GOOGLE_API_KEY=AI..."            # Google Gemini (free tier OK)
# DEEPSEEK uses OPENAI_API_KEY (verified 7/11 — platform also accepts)
# OLLAMA local — pull qwen3:4b-instruct-q4_0 and llama-3.3-70b-instruct first

# 3. Run the protocol
python scripts/run_protocol.py --scenarios data/scenarios/canonical.jsonl

# 4. Compute BDS
python scripts/bds_evaluator.py --in data/raw --out data
```

## 📊 Target Deliverables (9/15 Target)

| artifact | status | target |
|---|---|---|
| `main.tex` (final) | 🟡 skeleton (20.7 KB) → draft + results | 8/30 |
| Tables 2-4 | 🟡 stubs → real numbers | 8/15 |
| Figures 2-5 | 🔴 not started → matplotlib rendered | 8/25 |
| `protocol.md` | ✅ done (13.5 KB) | — |
| `bds_table.csv` | 🟡 pipeline ready | 7/15 (after first run) |
| Companion code | 🟡 3 scripts ready, 1 to write | 7/20 |

## 🔑 Research Questions

- **Q1**: Do frontier LLMs exhibit statistically significant behavior drift?
- **Q2**: Are drift patterns consistent across model families?
- **Q3**: Does multi-agent context amplify drift?
- **Q4**: Can a regression test suite predict drift 60 days in advance?

## 🤝 Branching Into the #35 / R3 Critical

This paper is the academic counterpart of vulnerability #35 from the Agent
OS red-team round 3 (see `knowledge/analysis/agent-os-red-team-r3-2026-07-
11.md` for the original vulnerability specification). The vulnerability
identifies the *risk*; this paper provides the *measurement* and the
*mitigation tool*.

## 📂 Related Resources

- [`knowledge/analysis/agent-os-red-team-r3-2026-07-11.md`](knowledge/analysis/agent-os-red-team-r3-2026-07-11.md) — Vulnerability #35 origin
- [`knowledge/analysis/agent-os-critical-11-triage-2026-07-11.md`](knowledge/analysis/agent-os-critical-11-triage-2026-07-11.md) — Triage that prioritized this paper
- `F:\Research\PAPER5_CONSOLIDATED\` — Sibling paper; carried-over scenarios

---

_Started by 泰 (刘泽文指定), 2026-07-11 14:55._
