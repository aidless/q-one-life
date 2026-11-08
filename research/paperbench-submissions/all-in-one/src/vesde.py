"""Executable VESDE formula slice for `all-in-one`.

Implements Appendix A2.1 pure-math leaves only:
- zero drift f(x, t) = 0
- diffusion g(t) = sigma_min * (sigma_max/sigma_min)^t * sqrt(2 log(sigma_max/sigma_min))
- perturbation kernel p(x_t | x_0) = N(x_0, sigma(t)^2 I)
- sigma_min=1e-4, sigma_max=15, time interval [1e-5, 1]

No Simformer, no sbi training, no benchmark tasks, no real judge score.
"""

from __future__ import annotations

import math

SIGMA_MIN = 0.0001
SIGMA_MAX = 15.0
T_MIN = 1e-5
T_MAX = 1.0


def drift(x: float, t: float) -> float:
    return 0.0


def diffusion(t: float) -> float:
    return SIGMA_MIN * (SIGMA_MAX / SIGMA_MIN) ** t * math.sqrt(
        2 * math.log(SIGMA_MAX / SIGMA_MIN)
    )


def sigma(t: float) -> float:
    return SIGMA_MIN * (SIGMA_MAX / SIGMA_MIN) ** t


def perturbation_kernel_mean(x0: float, t: float) -> float:
    return x0


def perturbation_kernel_std(t: float) -> float:
    return sigma(t)


def sample_perturbation(x0: float, t: float, epsilon: float) -> float:
    """x_t = x_0 + sigma(t) * epsilon, epsilon ~ N(0, 1)."""
    return x0 + sigma(t) * epsilon


def run_vesde_slice() -> dict:
    checks = {
        "drift_zero": drift(1.0, 0.5) == 0.0,
        "diffusion_t0": diffusion(0.0),
        "sigma_t0": sigma(0.0),
        "sigma_t1": sigma(1.0),
        "kernel_mean": perturbation_kernel_mean(3.0, 0.5),
        "kernel_std_t05": perturbation_kernel_std(0.5),
        "sample_zero_noise": sample_perturbation(3.0, 0.5, 0.0),
    }
    return {
        "paper_id": "all-in-one",
        "status": "vesde_formula_slice",
        "sigma_min": SIGMA_MIN,
        "sigma_max": SIGMA_MAX,
        "time_interval": [T_MIN, T_MAX],
        "checks": checks,
        "note": "Pure formulas only; no Simformer, sbi, training or judge.",
    }
