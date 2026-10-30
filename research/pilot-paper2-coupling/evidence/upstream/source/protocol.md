# Protocol: reproducing the 11-condition impossibility-triangle experiment

This document specifies the end-to-end reproduction protocol for the experiment described in `main.tex` as the joint measurement of the impossibility triangle across 11 evaluator–agent conditions, the within-condition convergence dynamics, and the Chatbot Arena external validation. It is written for `reproduce_peer`: a separate reproducer should be able to run the API calls, recompute `gamma`, `H`, and `CV(N)`, and compare the outputs to the paper-level claims.

Code, prompt templates, and lightweight audit artifacts are released at
`https://github.com/Anonymous/impossibility-triangle-audit` (MIT license, sibling
of `calibration-contagion-audit`). The local companion implementation exposes
`reproduce_peer/seed_lock.py`, `reproduce_peer/run_protocol.py`, and
`reproduce_peer/impossibility_calculator.py`; the latter wraps
`tools/evaluator_calculator.py` from the source repository. Do not hard-code
API keys in any file — load them from environment variables or a `.env` file
outside the repository.

## 1. Experimental target and condition registry

The paper contains three validation programs that must all be reproducible from
the same JSONL log.

1. **Between-subjects (11 conditions).** Four evaluator families (GPT-4o,
   DeepSeek-V3, Qwen-3.7, Claude-3.5) are crossed with three executor models
   over two protocols (self-evaluation and cross-model), plus two ablation
   levels (mid, max). For each condition we run `N in {5, 8, 10, 30}`
   independent TTRL seeds.
2. **Within-subjects convergence dynamics.** A single LLM (DeepSeek-chat) is
   used as both executor and evaluator. The independent variable is
   evaluator feedback strength `alpha_eval in {0, 0.5, 1.0}` for the
   falsifiable predictions and `alpha_eval in {0, 0.4, 0.8, 1.5, 2.0}` for
   the convergence-dynamics study. Configuration: `N >= 20` seeds, `T >= 30`
   rounds, 6 tasks, 11 strategies.
3. **External validation (Chatbot Arena).** 55,000 human preference judgments
   over 20 LLM models, used to compute the `gamma`–`H` correlation
   `r = -0.895` (p < 0.001).

Use the 11 condition identifiers from the paper so that every output row can
be matched back to `main.tex` Table 1:

| condition_id | paper role              | evaluator family    | executor model      | `alpha_eval` | `N` (seeds) |
|--------------|-------------------------|---------------------|---------------------|--------------|-------------|
| C1           | DS Self-Eval            | DeepSeek-V3         | DeepSeek-V3 (self)  | 0.0          | 30          |
| C2           | DS x Qwen               | DeepSeek-V3         | Qwen-3.7            | 0.4          | 30          |
| C3           | Qwen x DS               | Qwen-3.7            | DeepSeek-V3         | 0.8          | 10          |
| C4           | Ablation mid            | mixed               | mixed               | 0.8          | 10          |
| C5           | Ablation max            | mixed               | mixed               | 1.5          | 10          |
| C6           | Qwen 3.7                | Qwen-3.7            | Qwen-3.7 (self)     | 1.5          | 8           |
| C7           | Ablation no-S0          | mixed (no-S0)       | mixed               | 1.5          | 5           |
| C8           | Qwen asym               | Qwen-3.7            | mixed asym          | 0.8          | 5           |
| C9           | Qwen sym                | Qwen-3.7            | mixed sym           | 1.5          | 5           |
| C10          | DeepSeek asym           | DeepSeek-V3         | mixed asym          | 0.8          | 5           |
| C11          | DeepSeek sym            | DeepSeek-V3         | mixed sym           | 1.5          | 5           |

`mixed` denotes a randomly drawn evaluator drawn from {GPT-4o, DeepSeek-V3,
Qwen-3.7, Claude-3.5} for each call (uniform over the four families). For
ablations `no-S0` removes the first strategy from the comparison set. `asym`
uses asymmetric reweighting (`alpha_win = 0.08`, `alpha_lose = 0.04`);
`sym` uses symmetric reweighting (`alpha_win = alpha_lose = 0.06`).

The within-subjects protocol is registered separately as `condition_id =
W01` … `W05` (one per `alpha_eval` level) and uses `N=50` seeds of 30
rounds each, with the same seed set across all five `alpha_eval` levels
(true within-condition design).

## 2. Models, snapshots, endpoints, and rate limits

The paper names four families directly (OpenAI/GPT, DeepSeek, Qwen, Claude);
the reproduction harness includes the same four families. Use these pinned
aliases and record the provider response model/version string for every call:

| family        | model alias / snapshot                                       | endpoint                                                          | role                       | conservative limit             |
|---------------|--------------------------------------------------------------|------------------------------------------------------------------|----------------------------|--------------------------------|
| OpenAI        | `gpt-4o-2024-05-13`; if unavailable, record the exact `gpt-4o-*` deployment name | `https://api.openai.com/v1/chat/completions` (or Azure OpenAI compatible) | C3, C6, C7, GPT-4o ablation | 30 requests/minute, 2 s cooldown |
| DeepSeek      | `deepseek-chat` (alias `deepseek-v3` for v3)                 | `https://api.deepseek.com/v1/chat/completions`                    | C1, C2, C10, C11, executor | 30 requests/minute, retry after 429 |
| Qwen / DashScope | `qwen3.7-plus`                                            | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` | C3, C6, C8, C9             | 30 requests/minute             |
| Anthropic Claude | `claude-3-5-sonnet-20241022`                              | `https://api.anthropic.com/v1/messages`                          | ablations only             | 20 requests/minute             |

Temperature settings: solver (executor) calls use `temperature=0.7` for
generations and `temperature=0.3` for evaluators. The deliberately-perturbed
"mixed" evaluator draws a new family per call to mimic the ablation
conditions; record the family in the JSONL output. Set `max_tokens=512` for
solver calls and `max_tokens=32` for evaluator A/B calls. All provider keys
must come from environment variables (`OPENAI_API_KEY`, `DEEPSEEK_API_KEY`,
`DASHSCOPE_API_KEY`, `ANTHROPIC_API_KEY`).

**Snapshot drift warning.** GPT-4o coupling measurements can drift between
API versions: in May 2026, GPT-4o produced `gamma ~ 1.176` (N=8); in June
2026 the same model produced `gamma = 0.000` (N=8, 100% zero coupling).
The reproducer must record the model version string for every call and
report the snapshot date in the final metrics. The reference snapshot for
all paper claims is `gpt-4o-2024-05-13`.

## 3. Multi-agent setup and prompt topology

Each condition uses a single executor agent that maintains a probability
vector `w in Delta^{K-1}` over `K=11` strategies. The evaluator is a
separate API call (potentially from a different family in the
cross-model conditions). The topology is round-by-round adaptive
multiplicative reweighting:

1. Sample strategy `s_t ~ w^{(t)}`.
2. Generate response `r_t` using `s_t`.
3. Generate a baseline response `b_t` using `step_by_step` (constant
   reference strategy).
4. Ask the evaluator to compare `r_t` against `b_t` and return `A` or `B`.
5. Apply the asymmetric TTRL update:
   `w[s_winner] *= (1 + alpha_win)`,
   `w[s_loser]  *= (1 - alpha_lose)`,
   floor every weight at `0.001`, then renormalize.
6. Repeat for `T` rounds.

For the within-subjects protocol, steps 1-3 are simulated (no API call) and
the evaluator signal is a deterministic reward function
`R(s) = R_task(s) + alpha_eval * R_eval(s) + noise`; the same `T=30`
`K=11` strategy pipeline is used so the metrics are directly comparable.

For the 11 between-subjects conditions, a baseline `w_0 = (1/K, ..., 1/K)`
is recorded before round 0 so the coupling coefficient `gamma` can be
computed as the L2 distance from the baseline at the end of the run.

## 4. Prompt templates (copy-paste exact text)

### 4.1 Strategy catalog (K=11)

```text
step_by_step, direct, analogical, decomposition, evidence_based,
unit_analysis, estimation, working_backward, substitution, pattern_matching, guess_and_check
```

### 4.2 Solver system prompt (executor)

```text
You are a helpful AI assistant. Answer the user's task using the
following approach:

{strategy_instruction}

Important: actually use this approach in your response. If asked to
be step-by-step, number your steps. If asked to be direct, give the
answer first. Do NOT mention the strategy name in your response.
```

### 4.3 Per-strategy instruction

```text
step_by_step:    "Think step by step. Break down your reasoning into clear, numbered steps. Show your work at each stage."
direct:          "Be direct and concise. Give the answer first, then briefly explain. Prioritize clarity over elaboration."
analogical:      "Use analogies and metaphors to explain. Make connections to familiar concepts. Prioritize intuition over formalism."
decomposition:   "Decompose the problem into independent sub-problems. Solve each sub-problem separately, then combine."
evidence_based:  "Base your answer on concrete evidence and citations. Reference specific facts, data, or established results."
unit_analysis:   "Carry units through every step. Verify dimensional consistency before stating the final answer."
estimation:      "Estimate the order of magnitude first, then refine. State your uncertainty explicitly."
working_backward:"Start from the target answer and derive the steps that lead back to the question."
substitution:    "Substitute concrete values for variables, simplify algebraically, and substitute back."
pattern_matching:"Identify the structural pattern of the problem and match it to a known template."
guess_and_check: "Make an initial guess, evaluate, and iterate. Report the convergence trajectory."
```

### 4.4 Baseline (step_by_step) prompt

```text
Think step by step. Break down your reasoning into clear, numbered steps. Show your work at each stage.
```

### 4.5 Pairwise evaluator prompt

```text
You are a fair and balanced evaluator. Evaluate responses based on
their overall quality, clarity, and correctness. Avoid favoring any
particular reasoning style.
Compare two responses and determine which is better.
Respond with ONLY: "A" or "B". Do NOT explain.
```

The neutral evaluator is used for the default `alpha_eval=0` condition; for
`alpha_eval > 0` the evaluator message is unmodified — the evaluator
strength is applied at the reweighting step, not in the prompt. For the
`mixed` evaluator ablation, prepend a short tag identifying the family
("You are evaluating as the GPT-4o family", etc.) so the JSONL log can
recover which family was used.

### 4.6 Task domain prompts (3 domains, drawn uniformly)

```text
math:          "Solve this math problem: {problem_text}"
code:          "Write a Python function that {problem_text}. Only output the function code."
summarization: "Write a concise summary of the following article in 2-3 sentences:\n\n{article}\n\nSummary:"
```

The math problem pool is a hand-curated 100-problem set covering arithmetic,
algebra, probability, and classical proofs (see `data/math_problems.jsonl`).
The code problem pool is a 100-problem HumanEval-style set spanning sorting,
graph algorithms, dynamic programming, and string manipulation
(see `data/code_problems.jsonl`). The summarization pool is a 50-article set
drawn from CNN/DailyMail-style short articles
(see `data/summarization_problems.jsonl`). All three files are released as
JSONL with `id`, `prompt`, and (where applicable) `reference_answer` fields.

### 4.7 Within-subjects reward function (deterministic, no API)

For `condition_id = W01` … `W05` the evaluator is replaced by a
deterministic reward function so the protocol is fully reproducible
without an API key:

```python
import numpy as np
rng = np.random.default_rng(42)
task_quality = 0.7 + rng.uniform(-0.03, 0.03, 11)        # flat, K=11
eval_pref    = rng.uniform(0.05, 1.0, 11)                # peaked
eval_pref    = (eval_pref - eval_pref.min()) / (eval_pref.max() - eval_pref.min() + 1e-8)

def reward(s_idx, alpha_eval):
    noise_scale = 0.30 * np.exp(-1.0 * alpha_eval) + 0.03
    noise = rng.normal(0, noise_scale)
    return task_quality[s_idx] + alpha_eval * eval_pref[s_idx] + noise
```

This reward profile is the only varying input; the strategy profile
(`task_quality`, `eval_pref`) is held fixed across `alpha_eval` levels
(true within-condition).

## 5. Impossibility-triangle methodology

The strategy state is a distribution over `K=11` strategies. Initialize all
weights uniformly. At each round, sample a strategy from the agent's current
weights, generate the solver response, generate or reuse the
`step_by_step` baseline, and ask the evaluator whether A or B is better.
Apply the asymmetric TTRL update (`alpha_win = 0.08`, `alpha_lose = 0.04`
unless the condition overrides), floor every strategy weight at `0.001`,
then renormalize.

Compute the three impossibility-triangle metrics as follows:

- `gamma = || w_condition - w_baseline ||_2 / || w_baseline ||_2`,
  where `w_baseline` is the uniform distribution `(1/K, ..., 1/K)`.
- `H = -sum_i w_i * log(w_i) / log(K)` (normalized Shannon entropy in
  `[0, 1]`).
- `CV(N) = std(gamma_hat over N-seed subsample) / mean(gamma_hat)`.
  Compute by drawing `B=5000` bootstrap samples of size `N` from the
  full seed set, estimating `gamma` for each bootstrap, and reporting
  the bootstrap CV.

Compute the product `gamma * H * CV(N)` and the per-condition minimum.
The paper-level claim is `min(gamma * H * CV) = 0.003` (95% CI
`[0.002, 0.005]`) at `N=30`, consistent with the tight bound
`c_min^(low) = sigma_w / (||w_0||_2 * sqrt(N)) ~ 0.004` (Proposition 4 of
`main.tex`).

### 5.1 K-dependent sweep

To reproduce Table 2 of `main.tex`, run the same protocol with
`K in {2, 5, 10, 50, 100}` using strategy subsets of size `K` drawn from
the catalog in 4.1 (pad with a neutral placeholder strategy if `K > 11`).
The expected values are `c_min(K) in {0.148, 0.157, 0.187, 0.335, 0.447}`.

### 5.2 Within-condition falsifiable predictions

For `condition_id = W01` … `W05`, the protocol makes three falsifiable
predictions:

- (P1) `corr(alpha_eval, gamma_meas) > 0`
- (P2) `corr(alpha_eval, H) < 0`
- (P3) `corr(gamma_meas, CV(N=8)) < 0`

The expected magnitudes (from the main paper): `r(alpha, gamma) ~ 0.95`,
`r(alpha, H) ~ -0.95`, `r(gamma, CV(N=8)) ~ -0.8`. Convergence half-life
should land in 14–19 rounds, with `sigma_final` increasing from
`0.0022` at `alpha_eval=0` to `0.0039` at `alpha_eval=2.0`.

## 6. Cost estimate and runtime

The within-subjects protocol is a deterministic simulation (no API
calls). The between-subjects protocol uses real API calls. With
`N` matched seeds per condition and the condition-level round counts
listed below, the total is:

| condition group | seeds | rounds per seed | calls per seed | total calls |
|-----------------|------:|----------------:|---------------:|------------:|
| C1 self-eval    |    30 |              10 |        30 calls |        900 |
| C2 cross-model  |    30 |              10 |        30 calls |        900 |
| C3 cross-model  |    10 |              10 |        20 calls |        200 |
| C4 ablation mid |    10 |              10 |        20 calls |        200 |
| C5 ablation max |    10 |              10 |        20 calls |        200 |
| C6 self-eval    |     8 |              10 |        16 calls |        128 |
| C7 ablation     |     5 |              10 |        10 calls |         50 |
| C8 Qwen asym    |     5 |              10 |        10 calls |         50 |
| C9 Qwen sym     |     5 |              10 |        10 calls |         50 |
| C10 DS asym     |     5 |              10 |        10 calls |         50 |
| C11 DS sym      |     5 |              10 |        10 calls |         50 |
| W01–W05 sim     |    50 |              30 |       0 (sim)   |          0 |
| **Total API**   |       |                 |                |  **2,778** |

Expected cost is approximately **$30–$60** for the full run under the
paper's internal estimate; before running, recompute with current
provider prices using the pilot token log
(`reproduce_peer/pilot_token_log.json`). Expected wall-clock time is
**1–2 hours** with three asynchronous workers and conservative rate
limits, or **3–4 serial API hours** if calls are made one at a time.

External validation (Chatbot Arena) requires no API calls. The dataset
`lmarena-ai/arena-human-preference-55k` is downloaded from Hugging Face
and processed in `<1 hour` on a single CPU. The K-dependent sweep adds
`5 * 2,778 = 13,890` additional simulation calls (no API), running
in `<30 minutes`.

## 7. Random seed handling

All random choices must flow through `reproduce_peer/seed_lock.py`. The
file should define a deterministic function equivalent to:

```python
def seed_for(condition_id: str, seed_id: int, round_id: int,
             base_seed: int = 20260708) -> int:
    import hashlib
    key = f"{base_seed}:{condition_id}:{seed_id}:{round_id}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest()[:16], 16) % (2**32)
```

Use this seed to choose the task index, sampled strategy, tie-breaking
order, and any stochastic ablation mask. For the within-subjects
simulation, the same `task_quality` and `eval_pref` profiles are
generated once with `base_seed=42` and reused across all
`alpha_eval` levels to guarantee a true within-condition design.

API models are not perfectly deterministic even at low temperature, so
reproducibility requires storing raw prompts, raw responses, provider
request IDs, model aliases, timestamps, and retry counts. Seeds are
matched across C1–C11: `seed_id=7` must see the same ordered problem
list in every condition, modulo the condition's shorter or longer
horizon. The W01–W05 within-subjects simulation uses `seed_id=0..49`
matched across all five `alpha_eval` levels.

## 8. Output format

Write one JSON object per round (API call or simulation step) to
`outputs/protocol_run.jsonl`. The required fields are exactly:

```json
{
  "condition_id": "C1",
  "seed_id": 7,
  "round": 4,
  "strategy": "step_by_step",
  "w_pre": [0.0909, 0.0909, "...", 0.0909],
  "w_post": [0.0979, 0.0880, "...", 0.0909],
  "gamma": 0.187,
  "H": 0.988,
  "alpha_eval": 0.4,
  "timestamp": "2026-07-08T00:00:00Z"
}
```

Recommended additional fields are `model_family`, `model_snapshot`,
`endpoint`, `task_domain`, `task_id`, `prompt` (full text sent to
provider), `response` (raw model response), `evaluator_response`,
`evaluator_family`, `is_correct`, `ground_truth`, `provider_request_id`,
`retry_count`, and `cv_subsample_size`. After completion, run
`reproduce_peer/impossibility_calculator.py --input outputs/protocol_run.jsonl`
to emit per-condition `gamma`, `H`, `CV(N)` for `N in {5, 8, 15, 30}`,
the per-condition minimum `gamma * H * CV`, the within-condition
correlations (P1, P2, P3), the convergence half-life, and the
K-dependent sweep. The expected aggregate is a single JSON
`outputs/summary.json` matching `main.tex` Tables 1–3 within the
`95%` CI bands stated above.

For the external validation, write a separate JSONL
`outputs/chatbot_arena.jsonl` with one row per model:

```json
{
  "model_id": "gpt-4o",
  "n_battles": 4219,
  "win_rate": 0.78,
  "entropy_proxy": 0.41,
  "cv": 0.12,
  "decisiveness": 0.65
}
```

The script `reproduce_peer/arena_analysis.py` reads this file and emits
the 20-model correlation `r(H, decisiveness) = -0.895` (95% CI
`[-0.95, -0.78]`, `p < 0.001`).
