# CompoNet — Self-Composing Policies for Scalable Continual RL (Reproduction)

Paper: Malagón, Ceberio, Lozano — "Self-Composing Policies for Scalable Continual
Reinforcement Learning" (CompoNet).

## What is implemented

1. `src/encoder.py` — ALE CNN encoder: conv(32,8) -> conv(64,4) -> conv(64,3) ->
   dense(512). One encoder per policy module; a new module's encoder is
   initialized from the previous module's weights.
2. `src/componet.py` — the self-composing policy module:
   - `Φ^{k;s}` matrix of the `k-1` previous module outputs, shape `(k-1, |A|)`
   - output attention head: q = h_s W_out^Q, K = (Φ + E_out) W_out^K, V = Φ
   - input attention head: P = [v ; Φ], q = h_s W_in^Q, K = (P + E_in) W_in^K,
     V = P W_in^V
   - internal policy: concat(h_s, input-head output) -> 2-layer MLP
   - output = output-head vector + internal policy vector (normalised for
     continuous action spaces)
   - only W_out^Q / W_out^K, W_in^Q / W_in^K / W_in^V and the MLP are learnable
3. `src/metrics.py` — average performance, forward transfer and reference
   forward transfer (Sec. 5.1), plus success-rate and matching-rate helpers.
4. `src/baseline.py` — single-module baseline (FT-1 / FT-N reference), plus
   parameter-growth accounting used in the scalability analysis.
5. `run_smoke.py` — CPU smoke test on random tensors: builds a 6-module chain,
   checks shapes, freezing behaviour, linear parameter growth and the metrics
   code paths.

## Not implemented (explicitly)

- Full SAC/PPO training for 1M timesteps x 10 seeds on Meta-World, SpaceInvaders
  and Freeway. That requires GPU hours and the ALE/Meta-World stacks.
- PackNet / ProgressiveNet / CompoNet-per-task training runs.
  The buffers needed for those runs are handled as a separate training job.

## Usage

```bash
pip install -r requirements.txt
python run_smoke.py --modules 6 --out results/smoke.json
python -m pytest -q tests
```
