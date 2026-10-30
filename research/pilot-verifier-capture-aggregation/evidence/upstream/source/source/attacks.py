"""
attacks.py — 3 attack models for verifier capture
Status: W2 implementation. Implements the 3 attack families in
Definition 1.2 of the paper.

Each attack takes the original (honest) verifier output and the input
context (the running median of other verifiers) and returns the
captured output.

Attack interface:
    attack(honest_output: float, ctx: dict) -> float
where ctx may contain 'median_others', 'round', 'target', etc.
"""
from __future__ import annotations
import numpy as np


# =====================================================================
# 1. Prompt injection
# =====================================================================
class PromptInjectionAttack:
    """Fixed adversarial output, e.g. 'always output 0.9' or 'always output 0.1'.

    Two modes:
    - 'naive': always output target (no mimicry). Weak attack.
    - 'stealth': output target when honest would output correct,
                 output opposite-honest when honest would be wrong
                 (i.e. look like an honest verifier but flip every time).
                 Strong attack.

    Parameters
    ----------
    target : float
        The output the captured verifier is steered toward in 'naive' mode.
        In 'stealth' mode, this is unused; the attack always flips.
    mode : str
        'naive' or 'stealth'.
    """

    def __init__(self, target: float = 0.1, mode: str = "stealth"):
        self.target = target
        self.mode = mode

    def __call__(self, honest_output: float, ctx: dict | None = None) -> float:
        if self.mode == "stealth":
            # Flip: if honest outputs ~0.8, output ~0.2 (but in a stealthy way,
            # just flip the probability)
            return 1.0 - honest_output
        return self.target


# =====================================================================
# 2. Rubric injection
# =====================================================================
class RubricInjectionAttack:
    """Depends on input via hidden rubric bias.

    The captured verifier flips its decision based on a hidden feature
    of the input. Here we simulate this by flipping if the round number
    is in a target subset (proxy for input-feature-dependent bias).

    Parameters
    ----------
    flip_rate : float
        Fraction of inputs on which the verifier flips its decision.
    target_label : int
        The label the verifier pushes toward on flip-rounds (0 or 1).
    """

    def __init__(self, flip_rate: float = 0.4, target_label: int = 0,
                 seed: int = 0):
        self.flip_rate = flip_rate
        self.target_label = target_label
        self.rng = np.random.default_rng(seed)
        self._flip_mask: np.ndarray | None = None  # set on first call

    def __call__(self, honest_output: float, ctx: dict | None = None) -> float:
        if ctx is None or "T" not in ctx:
            T = 1
        else:
            T = ctx["T"]
            if self._flip_mask is None or len(self._flip_mask) != T:
                self._flip_mask = self.rng.random(T) < self.flip_rate
            t = ctx.get("round", 0)
            if self._flip_mask[t]:
                # Push toward target_label
                if self.target_label == 0:
                    return 1.0 - honest_output
                else:
                    return honest_output
        return honest_output


# =====================================================================
# 3. Majority bias
# =====================================================================
class MajorityBiasAttack:
    """Captured verifier mimics the running empirical mode of the others.

    Outputs the empirical mode (>=0.5) of the other verifiers, making
    the captured output indistinguishable from the majority.

    Parameters
    ----------
    smoothness : float
        Smoothing factor in [0, 1]: 0 = exact mimicry, 1 = no attack.
    """

    def __init__(self, smoothness: float = 0.0):
        self.smoothness = smoothness

    def __call__(self, honest_output: float, ctx: dict | None = None) -> float:
        if ctx is None or "median_others" not in ctx:
            return honest_output
        target = ctx["median_others"]
        return (1.0 - self.smoothness) * target + self.smoothness * honest_output


# =====================================================================
# Attack registry
# =====================================================================
ATTACKS = {
    "prompt_injection":   lambda: PromptInjectionAttack(target=0.1, mode="stealth"),
    "rubric_injection":   lambda: RubricInjectionAttack(flip_rate=0.4, target_label=0),
    "majority_bias":      lambda: MajorityBiasAttack(smoothness=0.0),
}


def apply_attack(honest_output: float, attack_name: str, ctx: dict | None = None,
                 attack_obj=None) -> float:
    """Apply a named attack to a single honest output."""
    if attack_obj is None:
        attack_obj = ATTACKS[attack_name]()
    return attack_obj(honest_output, ctx)


# =====================================================================
# Smoke test
# =====================================================================
if __name__ == "__main__":
    rng = np.random.default_rng(0)
    # Simulate 5 honest outputs
    honest = rng.uniform(0.6, 0.95, size=5)
    median = np.median(honest)
    print(f"Honest outputs: {np.round(honest, 3)}")
    print(f"Median of others: {median:.3f}")

    for name in ATTACKS:
        attack = ATTACKS[name]()
        ctx = {"median_others": median, "round": 0, "T": 100}
        captured = attack(honest[0], ctx)
        print(f"  {name:18s}  captured output = {captured:.3f}")