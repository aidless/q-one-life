"""extended_methods.py — Expanded method zoo for the benchmark paper.

Includes classical aggregation methods + adaptive variants designed
to bridge the gap we observed in W2 demos. The goal of the benchmark
is to identify which aggregation rule is most robust under LLM-verifier
capture across a range of attack strengths.

Methods:
  CLASSICAL:
    - majority:        plain majority vote
    - bft_pbft:        PBFT-style 2f+1 threshold
    - weighted_uniform: uniform-weighted mean

  TRUST-BASED (soft weighting):
    - trust_score_mean: trust-score weighted mean
    - trust_score_median: trust-score WEIGHTED MEDIAN (new direction)
    - kalman_trust:    Kalman-filter trust tracking (new direction)

  ADAPTIVE HYBRIDS (proposed candidates):
    - ATV (Adaptive Trust-Weighted Voting): switches between
      soft-weight-mean and hard-trimmed-median based on detected
      cluster consensus. Designed to recover when CRV-style hard
      exclusion fails.
"""
from __future__ import annotations
import numpy as np


# =====================================================================
# Classical baselines (also re-exported here for self-containment)
# =====================================================================
def majority(votes, threshold=0.5):
    binary = (votes >= threshold).astype(int)
    s = binary.sum(axis=1)
    N = votes.shape[1]
    return (s > N / 2).astype(int)


def bft_pbft(votes, f=2):
    N = votes.shape[1]
    threshold_count = (N + f + 1) // 2
    binary = (votes >= 0.5).astype(int)
    s = binary.sum(axis=1)
    return (s >= threshold_count).astype(int)


def weighted_uniform(votes):
    N = votes.shape[1]
    s = votes @ (np.ones(N) / N)
    return (s >= 0.5).astype(int)


# =====================================================================
# Trust-based soft weights
# =====================================================================
def trust_score_mean(votes, alpha=0.9):
    """Trust EMA on consistency, weight the mean."""
    T, N = votes.shape
    tau = np.ones(N) * 0.5
    decisions = np.zeros(T, dtype=int)
    for t in range(T):
        p_t = votes[t]
        med = np.array([np.median(np.delete(p_t, i)) for i in range(N)])
        # weighted mean (SOFT, not hard exclusion)
        w = tau / (tau.sum() + 1e-9)
        s = np.sum(w * p_t)
        decisions[t] = int(s >= 0.5)
        # update
        c = 1.0 - np.abs(p_t - med)
        tau = alpha * tau + (1.0 - alpha) * c
    return decisions


def trust_score_median(votes, alpha=0.9):
    """Trust EMA + trust-WEIGHTED median (not mean). New direction.

    Idea: weighted median is robust to outlier (a single high-weight
    extreme value cannot swing the median the way it swings a mean).
    """
    T, N = votes.shape
    tau = np.ones(N) * 0.5
    decisions = np.zeros(T, dtype=int)
    for t in range(T):
        p_t = votes[t]
        # weighted median via cumulative-weight crossing 1/2
        order = np.argsort(p_t)
        cum = np.cumsum(tau[order])
        half = tau.sum() / 2.0
        idx = np.searchsorted(cum, half)
        idx = min(idx, N - 1)
        decisions[t] = int(p_t[order[idx]] >= 0.5)
        # update trust
        med = np.array([np.median(np.delete(p_t, i)) for i in range(N)])
        c = 1.0 - np.abs(p_t - med)
        tau = alpha * tau + (1.0 - alpha) * c
    return decisions


def kalman_trust(votes, alpha=0.9, R=0.05):
    """Kalman-style trust tracking with process variance R.

    Treats consistency observation as noisy measurement; trust is the
    filtered estimate. Smoother than EMA under noisy verifier streams.
    """
    T, N = votes.shape
    tau = np.ones(N) * 0.5
    P = np.ones(N) * 0.1  # uncertainty
    Q = np.ones(N) * 0.01  # process noise
    decisions = np.zeros(T, dtype=int)
    for t in range(T):
        p_t = votes[t]
        med = np.array([np.median(np.delete(p_t, i)) for i in range(N)])
        # predict
        tau_hat = tau
        P_hat = P + Q
        # update with c observation
        c = 1.0 - np.abs(p_t - med)
        K = P_hat / (P_hat + R)
        tau = tau_hat + K * (c - tau_hat)
        P = (1 - K) * P_hat
        # decision = weighted mean
        w = tau / (tau.sum() + 1e-9)
        s = np.sum(w * p_t)
        decisions[t] = int(s >= 0.5)
    return decisions


# =====================================================================
# Adaptive Hybrid: ATV (proposed new method)
# =====================================================================
def atv(votes, alpha=0.9, beta=5.0, tau_split=0.5):
    """Adaptive Trust-Weighted Voting.

    Adaptive rule:
    - If trust scores are highly concentrated (tau std < tau_split):
        → use weighted MEAN (uniform regime, all verifiers trustworthy)
    - Else (high trust disagreement):
        → use weighted MEDIAN (capture suspected, robust to outliers)

    The motivation: CRV failed because hard exclusion was wrong under
    bimodal honest; trust_only_mean failed because mean is sensitive.
    Weighted median handles outliers AND doesn't exclude — it downgrades.
    """
    T, N = votes.shape
    tau = np.ones(N) * 0.5
    decisions = np.zeros(T, dtype=int)

    for t in range(T):
        p_t = votes[t]
        # inconsistency (kept for monitoring; not used for exclusion)
        med = np.array([np.median(np.delete(p_t, i)) for i in range(N)])
        xi = 1.0 / (1.0 + np.exp(-beta * np.abs(p_t - med)))

        # update trust
        c = 1.0 - np.abs(p_t - med)
        tau_new = alpha * tau + (1.0 - alpha) * c
        tau = tau_new

        # adaptive decision
        tau_std = tau.std()
        if tau_std < tau_split:
            # uniform regime: weighted mean
            w = tau / (tau.sum() + 1e-9)
            s = np.sum(w * p_t)
            decisions[t] = int(s >= 0.5)
        else:
            # capture-suspect: weighted median
            order = np.argsort(p_t)
            cum = np.cumsum(tau[order])
            half = tau.sum() / 2.0
            idx = np.searchsorted(cum, half)
            idx = min(idx, N - 1)
            decisions[t] = int(p_t[order[idx]] >= 0.5)
    return decisions


# =====================================================================
# Registry for clean iteration
# =====================================================================
METHODS = {
    "majority":          majority,
    "bft_pbft":          bft_pbft,
    "weighted_uniform":  weighted_uniform,
    "trust_mean":        trust_score_mean,
    "trust_median":      trust_score_median,
    "kalman_trust":      kalman_trust,
    "ATV":               atv,
}


# =====================================================================
# Smoke test
# =====================================================================
if __name__ == "__main__":
    rng = np.random.default_rng(0)
    T, N, f = 1000, 7, 2
    gt = rng.integers(0, 2, size=T)
    votes = np.zeros((T, N))
    for t in range(T):
        correct = gt[t]
        for i in range(N):
            if i < f:
                votes[t, i] = 0.85 if correct == 0 else 0.15  # wrong strong
            else:
                if rng.random() < 0.6:
                    votes[t, i] = 0.75 if correct == 1 else 0.25
                else:
                    votes[t, i] = 0.25 if correct == 1 else 0.75
                votes[t, i] = float(np.clip(votes[t, i] + rng.normal(0, 0.05), 0, 1))
    print("BFT boundary test (T=1000, f=2, honest bimodal):")
    for name, fn in METHODS.items():
        d = fn(votes)
        acc = (d == gt).mean()
        print(f"  {name:18s}  acc = {acc:.3f}")