"""benchmark.py — Full benchmark table for the A4 paper (post X+Z pivot).

Compares 7 methods × 4 scenarios × 2 attack strengths.
Outputs a tabular summary that becomes Table 1 in the paper.

Scenarios:
  S1: high-honest, weak-attack   (typical production)
  S2: medium-honest, weak-attack (typical real)
  S3: medium-honest, strong-attack (boundary)
  S4: high-honest, strong-attack (capture fighting back)

Methods tested: 7 (majority, bft_pbft, weighted_uniform, trust_mean,
trust_median, kalman_trust, ATV).
"""
from __future__ import annotations
import numpy as np
from extended_methods import METHODS


# =====================================================================
# Scenario generators
# =====================================================================
def gen_scenario(T, N, f, honest_acc, attack_strength, seed):
    """honest_acc: prob each honest verifier outputs correctly
    attack_strength: prob captured verifier outputs WRONG with high conf

    Returns (votes, gt).
    """
    rng = np.random.default_rng(seed)
    gt = rng.integers(0, 2, size=T)
    votes = np.zeros((T, N))

    for t in range(T):
        correct = gt[t]
        # honest
        for i in range(N - f):
            if rng.random() < honest_acc:
                votes[t, i] = 0.75 if correct == 1 else 0.25
            else:
                votes[t, i] = 0.25 if correct == 1 else 0.75
            votes[t, i] = float(np.clip(votes[t, i] + rng.normal(0, 0.05), 0, 1))
        # captured: outputs WRONG direction with probability attack_strength
        for i in range(N - f, N):
            if rng.random() < attack_strength:
                votes[t, i] = 0.85 if correct == 0 else 0.15
            else:
                # confused captured: random
                votes[t, i] = rng.uniform(0, 1)
            votes[t, i] = float(np.clip(votes[t, i] + rng.normal(0, 0.02), 0, 1))
    return votes, gt


SCENARIOS = [
    ("S1: high-honest, weak-attack",      dict(honest_acc=0.85, attack_strength=0.6)),
    ("S2: med-honest, weak-attack",         dict(honest_acc=0.65, attack_strength=0.6)),
    ("S3: med-honest, strong-attack",      dict(honest_acc=0.65, attack_strength=0.9)),
    ("S4: high-honest, strong-attack",     dict(honest_acc=0.85, attack_strength=0.9)),
]


def run_table(T=1000, N=7, f=2, n_seeds=5):
    """Average accuracy across n_seeds for stability."""
    headers = ["Method"] + [s[0] for s in SCENARIOS] + ["mean"]
    print(" | ".join(h.ljust(20) for h in headers))
    print("-" * 130)
    summary = {name: [] for name in METHODS}
    for name in METHODS:
        row = [name]
        for sc_name, params in SCENARIOS:
            accs = []
            for seed in range(n_seeds):
                votes, gt = gen_scenario(T=T, N=N, f=f, seed=seed, **params)
                fn = METHODS[name]
                if name == "bft_pbft":
                    d = fn(votes, f=f)
                else:
                    d = fn(votes)
                accs.append((d == gt).mean())
            mean_acc = np.mean(accs)
            row.append(f"{mean_acc:.3f}")
            summary[name].append(mean_acc)
        row.append(f"{np.mean(summary[name]):.3f}")
        print(" | ".join(s.ljust(20) for s in row))
    print()
    # Best per scenario
    print("Best per scenario:")
    for i, (sc_name, _) in enumerate(SCENARIOS):
        scores = [(name, summary[name][i]) for name in METHODS]
        scores.sort(key=lambda x: -x[1])
        print(f"  {sc_name}: {scores[0][0]} ({scores[0][1]:.3f})")
    return summary


if __name__ == "__main__":
    run_table()