# Protocol — Seed Reproducibility and Cross-Model Heterogeneity of Local LLM Agent Behavior

_Reproducibility protocol for the paper **"Agent Behavior Regression Testing for Local LLM Systems: Seed Reproducibility and Cross-Model Heterogeneity across 100 Scenarios"** (TMLR submission, 2026)._

This document specifies the end-to-end reproduction protocol for the Behavior Drift Score (BDS) experiment described in Sections 4-5 of `main.tex`. A separate reproducer should be able to: (i) install dependencies, (ii) run the local model generations, (iii) recompute the BDS metrics, (iv) reproduce the tables and figures, and (v) compare outputs to the paper-level claims.

Code, audit artifacts, and analysis scripts are hosted at the anonymized companion repository (MIT license). Local companion implementation exposes `scripts/run_protocol.py`, `scripts/scenario_generator.py`, and `scripts/bds_evaluator.py`. No API keys are required: the experiment uses only local Ollama inference.

The protocol regenerates:
- **Table 1**: scenario suite composition (6 categories, 100 scenarios).
- **Table 2**: seed reproducibility (mean cross-seed BDS per model).
- **Table 3**: cross-model heterogeneity (mean BDS over 6 model pairs per category, with bootstrap 95% CIs).
- **Figure 1**: cross-model heterogeneity by category.
- **Figure 2**: seed reproducibility per model.

---

## 1. Experimental Target and Condition Registry

### 1.1 Research Questions

- **Q1** — Are local LLM agent behaviors seed-reproducible at temperature 0 on a common behavioral regression suite?
- **Q2** — How heterogeneous is behavior across model families on the same suite, and does heterogeneity depend on scenario category?

### 1.2 Model Cohort

Four local models served through Ollama at temperature 0:

| alias | model tag | size |
|---|---|---|
| ds-r1 | `deepseek-r1:7b` | 7B |
| coder | `qwen2.5-coder:7b` | 7B |
| qwen2 | `qwen2:7b` | 7B |
| qwen3 | `qwen3:4b` | 4B |

All generations use `temperature = 0.0`; the Ollama endpoint is the default local address.

### 1.3 Scenario Catalogue

100 canonical scenarios partitioned into 6 categories, generated deterministically from a seeded RNG (`scripts/scenario_generator.py`, seed = 20260711) and fixed as JSON Lines under `data/scenarios/canonical.jsonl`:

| category | code | count | provenance |
|---|---|---|---|
| Length compliance | L | 20 | carried over (length-bias layer) |
| Authority bias | A | 20 | carried over (authority-bias layer) |
| Multi-agent contagion | M | 20 | new |
| Tool-use | T | 10 | new |
| Refusal alignment | R | 15 | new |
| Multilingual | X | 15 | new |

Each scenario contains `scenario_id`, `category`, `system_prompt`, `user_prompt`, and an `evaluation` rubric.

### 1.4 Cells

4 models x 100 scenarios x 3 seeds = 1,200 cells, run as 12 jobs (one per model-seed pair). Each job writes one JSONL line per scenario with `scenario_id` and generated `text`. The manifest (`experiments/full_run/_manifest.json`) records start/finish times, wall-clock seconds, and per-job status (12/12 OK, ~1.7 h total).

## 2. BDS Computation

`scripts/bds_evaluator.py` implements the metric:

1. Whitespace tokenization (lowercase, punctuation stripped, tokens of length > 1).
2. Per-scenario pooled vocabulary of size K = 10,000.
3. Per-condition histograms with Laplace smoothing alpha = 1e-5.
4. BDS = mean KL divergence over all unordered condition pairs (3 seed pairs for Q1; 6 model pairs for Q2).

## 3. Analysis

`experiments/analyze_full_run.py` computes Q1/Q2 aggregates. Supplemental statistics for the manuscript (`experiments/full_run/analysis/full_run_stats_20260813.json`, `category_pairwise_20260813.json`) include:

- Per-model and per-category cross-seed BDS means.
- Per-category cross-model BDS means with bootstrap 95% CIs (B = 5,000).
- Paired Wilcoxon signed-rank test on per-scenario cross-model minus cross-seed BDS differences.
- Two-sided Mann-Whitney U tests across all 15 category pairs, Bonferroni-corrected to alpha' = 0.0033.

## 4. Reproducer Steps

1. Install Ollama and pull the four model tags.
2. `python scripts/scenario_generator.py` -> regenerates `data/scenarios/canonical.jsonl`.
3. `python scripts/run_protocol.py` -> regenerates the 12 JSONL raw files under `experiments/full_run/raw/`.
4. `python experiments/analyze_full_run.py` -> regenerates the analysis JSON.
5. `python experiments/stats_20260813.py` (released) -> regenerates the supplemental statistics.

## 5. Caveats

- The four models are local single-snapshot checkpoints; no temporal (vendor-release) drift is measured in this paper.
- BDS is a token-distribution metric, not a semantic metric.
- Multi-agent amplification (3-agent chains on the M scenarios) is planned follow-up work, not part of this submission.
