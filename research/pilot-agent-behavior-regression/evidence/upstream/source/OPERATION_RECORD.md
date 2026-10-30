# Operation Record — PAPER35_FRONT_DRIFT

> Session log of decision steps, tests, and reversibility anchors for
> the Agent Behavior Heterogeneity and Reproducibility submission to TMLR.

## 2026-08-16 — Status Update (post-takeover)

### Decisions
| # | Decision | Rationale |
|---|---|---|
| D7 | Manuscript is complete with real data; only housekeeping remains | full_run 1,200 cells + chain pilot done; main.tex numbers verified against JSON |
| D8 | Chain-divergence numbers anchored to `reproduce_chain_analysis.py` (8.45/6.99/5.63/2.57) | previous `analysis_v2_20260814.json` had no generating script and could not be reproduced; the repro script is now the single source of truth |
| D9 | Bad v1 file `analysis_20260814.json` (all-zero placeholder) deleted | would mislead if used; real data is in `analysis_v2` + repro output |
| D10 | Cloud 30-scenario run (run_p35_cloud.py) has no local return artifact | not required for current manuscript (pilot scope is explicit); follow-up item |

### Artifacts
| artifact | purpose |
|---|---|
| `experiments/multi_agent/reproduce_chain_analysis.py` | recomputes chain-divergence stats from the 12 raw jsonl; writes `analysis_repro_20260816.json` |
| `experiments/multi_agent/analysis_repro_20260816.json` | repro output (mean/median/max per model, per-scenario means) |
| `main.tex` §Multi-Agent Chain Divergence (Pilot) | updated to repro numbers + script pointer |

### Residual risks
| risk | mitigation |
|---|---|
| chain pilot uses 10 scenarios, not protocol's 30 | explicitly labeled "Pilot" in text; full run is follow-up |
| cloud 30-scenario amplification results not retrieved | documented; not blocking submission of pilot-scoped manuscript |

---

## 2026-07-11 (Friday) — Session 1 (foundation)

### Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | Paper title: **Agent Behavior Regression Test Suite: Detecting Frontier Model Drift in Multi-Agent Pipelines** | Anchors on the *behavioral* (not cryptographic) regression dimension; aligns with vulnerability #35 |
| D2 | Venue: **TMLR** (Diamond OA, Rolling Submission) | Free (no APC); no deadline pressure; sibling PAPER5 already targets TMLR |
| D3 | Experimental scope: **6 frontier models × 100 scenarios × 3 snapshots × 3 seeds = 5,400 single-LLM cells + 1,080 multi-agent amplification** | Cover all major API families + 2 local (Ollama); scenario set carries over 40 from PAPER5 plus 60 new |
| D4 | Reuse PAPER5 scenarios for **L** (length) and **A** (authority) categories | Saves scenario-design time; ensures cross-paper comparability |
| D5 | BDS metric: histogram-binned KL over whitespace-tokenized outputs, top-K=10K vocab, Laplace smoothing α=10⁻⁵, averaged over 3 unordered snapshot pairs | Scale-invariant; model-tokenizer-agnostic; symmetric across pairs |
| D6 | Multi-agent amplification: 3-agent chain on \textsc{M} and \textsc{T} categories | Captures the *empirical* amplification effect |

### Artifacts Created

| artifact | size | purpose |
|---|---|---|
| `protocol.md` | 13.5 KB | Full reproducibility protocol (5 sections + computational cost estimate) |
| `main.tex` | 20.7 KB | Skeleton (Abstract + Intro + Related + Method + Setup + Results-stub + Discussion + Conclusion + Appendix) |
| `scripts/scenario_generator.py` | 11.4 KB | Deterministically generates 100 scenarios (40 carried-over + 60 new) |
| `scripts/run_protocol.py` | 13.6 KB | Drives 6-model × 100-scenario × 3-snapshot × 3-seed sweep across 4 API providers + Ollama |
| `scripts/bds_evaluator.py` | 6.6 KB | Computes BDS per (model, scenario); writes bds_table.json + bds_table.csv |
| `README.md` | 4.4 KB | Repository landing page |
| `math_commands.tex`, `refs.bib`, `tmlr.sty`, `tmlr.bst` | copied from PAPER5 | TMLR template reuse |

### Risks Identified

| risk | mitigation |
|---|---|
| Snapshot alias deprecation (OpenAI/Anthropic) | Record `response.model` verbatim; log warning; fall back to deployment string |
| Local Ollama snapshots are not temporally aligned | Treat Qwen/Meta as *model-variant* comparators, not calendar drift (acknowledge in §6.4 of `main.tex`) |
| Bootstrap null underestimates drift | Use 1,000 replicates; report 5% FPR via per-model calibration |
| Tokenizer-bias contamination of BDS | Use *whitespace* tokenizer (model-agnostic) + length-drift control proxy |
| Multi-agent chain length-bias amplification confounded with single-LLM amplification | Report both conditions; report amplification factor β per cell |

### Next Actions (D-Phase)

| task | owner | target |
|---|---|---|
| Run scenario_generator.py to materialize canonical.jsonl | 泰 | 7/12 (next session) |
| Manually inspect 5 random scenarios from each category | 刘泽文 | 7/14 |
| Run run_protocol.py for Qwen + DeepSeek (cheapest first) | 泰 | 7/15 |
| Run remaining 4 models in parallel on different machines | 刘泽文 + 泰 | 7/18 |
| Compute BDS and bootstrap drift detection | 泰 | 7/22 |
| Run multi-agent amplification cells | 泰 | 7/25 |
| Write tables 2-4 and figures 2-5 | 泰 | 8/05 |
| Write Results + Discussion sections | 泰 | 8/20 |
| Internal review (rr-responder + simulate reviewer) | 泰 | 9/05 |
| TMLR submission | 刘泽文 | 9/15 |

### Anchor Files

- `main.tex` — paper body
- `protocol.md` — reproducibility contract
- `scripts/run_protocol.py` — experimental runner

### Reversibility

- All scripts are idempotent (overwrite outputs on re-run).
- Raw outputs are versioned by snapshot alias and seed; deletion is non-destructive until a manual `rm -rf data/`.
- TMLR submission is **rolling** — there is no "missed deadline" penalty.

---

_Logged by 泰, 2026-07-11 14:55-15:10 session 1. Total wall-clock ~30 min._
