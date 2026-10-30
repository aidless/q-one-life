"""
crv.py — Capture-Resilient Voting algorithm and 5 baselines
Status: W2 implementation. Implements Algorithm 1 + 5 baselines.

All functions take a 2D numpy array of verifier outputs:
    votes: shape (T, N) — T rounds, N verifiers, values in [0, 1]
Each returns a 1D array of length T with binary decisions in {0, 1}.
"""
from __future__ import annotations
import numpy as np


# =====================================================================
# 1. CRV: Capture-Resilient Voting (proposed)
# =====================================================================
def crv(
    votes: np.ndarray,
    alpha: float = 0.9,
    beta: float = 5.0,
    f: int = 2,
    tau_init: float | None = None,
    xi_threshold: float = 0.5,
) -> tuple[np.ndarray, np.ndarray]:
    """CRV voting (Algorithm 1 in the paper).

    Key design choice (W2.5 fix): inconsistency xi is used as a HARD
    exclusion mask, not a soft weight multiplier. Verifiers with
    xi > xi_threshold are dropped from the vote entirely. This makes
    CRV qualitatively different from trust_score_only: where the latter
    softly scales weights (so the decision direction is invariant to
    uniform scaling), CRV replaces the soft scale with an exclusion
    rule that can flip the direction of the majority.

    The algorithm:
        1. Compute pairwise median of N-1 others for each i.
        2. Compute inconsistency xi_i = sigmoid(beta * |p_i - med|).
        3. Trust mask = [xi_i < xi_threshold].
        4. Decide:
            - If sum(mask) > N/2: majority among trusted verifiers.
            - Else: fall back to weighted mean of trusted verifiers
              (with weights = tau_i).
        5. Update trust scores via EMA.
    """
    T, N = votes.shape
    if tau_init is None:
        tau = np.ones(N) * 0.5
    else:
        tau = np.full(N, tau_init)
    decisions = np.zeros(T, dtype=int)
    trust_history = np.zeros((T, N))

    for t in range(T):
        p_t = votes[t]

        # 1. pairwise median for each i
        med = np.array([np.median(np.delete(p_t, i)) for i in range(N)])

        # 2. inconsistency
        xi = _sigmoid(beta * np.abs(p_t - med))

        # 3. trust mask (hard exclusion)
        trusted = xi < xi_threshold
        n_trusted = int(trusted.sum())

        # 4. decide
        if n_trusted == 0:
            # extreme case: all inconsistent — fall back to mean
            decisions[t] = int(np.mean(p_t) >= 0.5)
        elif n_trusted >= 3 and n_trusted * 2 > N:
            # trustworthy majority exists: use hard majority over trusted
            binary = (p_t[trusted] >= 0.5).astype(int)
            decisions[t] = int(binary.sum() * 2 > n_trusted)
        else:
            # too few trusted: weighted mean among trusted (safety fallback)
            w = tau[trusted]
            S = np.sum(w * p_t[trusted])
            decisions[t] = int(S >= 0.5 * np.sum(w))

        # 5. update trust scores
        c = 1.0 - np.abs(p_t - med)
        tau = alpha * tau + (1.0 - alpha) * c
        trust_history[t] = tau

    return decisions, trust_history[-1]


# =====================================================================
# 2. Baselines
# =====================================================================
def majority(votes: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """Plain majority voting: each verifier contributes binary vote at 0.5."""
    binary = (votes >= threshold).astype(int)
    s = binary.sum(axis=1)
    N = votes.shape[1]
    return (s > N / 2).astype(int)


def bft_pbft(votes: np.ndarray, f: int = 2) -> np.ndarray:
    """Simplified PBFT-style: prepare/commit phases via 2f+1 threshold.

    Returns majority vote where threshold = (N+f+1)/2 (i.e. tolerates f Byzantine).
    """
    N = votes.shape[1]
    threshold_count = (N + f + 1) // 2  # equivalent to > 2f/3 replicas
    binary = (votes >= 0.5).astype(int)
    s = binary.sum(axis=1)
    return (s >= threshold_count).astype(int)


def weighted(votes: np.ndarray, weights: np.ndarray | None = None) -> np.ndarray:
    """Weighted voting with static uniform weights (no trust tracking)."""
    T, N = votes.shape
    if weights is None:
        weights = np.ones(N) / N
    s = votes @ weights
    return (s >= 0.5).astype(int)


def trust_score_only(
    votes: np.ndarray,
    alpha: float = 0.9,
) -> tuple[np.ndarray, np.ndarray]:
    """Trust-score weighted vote WITHOUT inconsistency term. (one-signal baseline)"""
    T, N = votes.shape
    tau = np.ones(N) * 0.5
    decisions = np.zeros(T, dtype=int)
    for t in range(T):
        p_t = votes[t]
        med = np.median(np.tile(p_t, (N, 1)).T - np.eye(N) * 1e9, axis=1)
        # simpler: median over all per-row minus self (vectorized)
        med = np.array([np.median(np.delete(p_t, i)) for i in range(N)])
        S = np.sum(tau * p_t)
        decisions[t] = int(S >= 0.5 * np.sum(tau))
        c = 1.0 - np.abs(p_t - med)
        tau = alpha * tau + (1.0 - alpha) * c
    return decisions, tau


def verifier_chain(votes: np.ndarray) -> np.ndarray:
    """Serial verifier chain: each subsequent verifier sees prior outputs.

    Decision = last verifier's output (rounded).
    """
    return (votes[:, -1] >= 0.5).astype(int)


# =====================================================================
# Helpers
# =====================================================================
def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


# =====================================================================
# Quick smoke test
# =====================================================================
if __name__ == "__main__":
    np.random.seed(42)
    T, N = 100, 7
    # simulate: 80% honest + 2 of 7 captured
    base = np.random.beta(8, 2, size=(T, N))  # mostly correct
    # capture: indices 0, 1 biased toward 0
    base[:, 0] = np.random.beta(2, 8, size=T)
    base[:, 1] = np.random.beta(2, 8, size=T)
    ground_truth = np.ones(T, dtype=int)

    for name, fn in [
        ("majority",   lambda v: majority(v)),
        ("bft_pbft",   lambda v: bft_pbft(v, f=2)),
        ("weighted",   lambda v: weighted(v)),
        ("trust_only", lambda v: trust_score_only(v)[0]),
        ("vchain",     lambda v: verifier_chain(v)),
        ("CRV",        lambda v: crv(v, alpha=0.9, beta=5.0, f=2)[0]),
    ]:
        decisions = fn(base)
        acc = (decisions == ground_truth).mean()
        print(f"  {name:12s}  acc = {acc:.3f}")