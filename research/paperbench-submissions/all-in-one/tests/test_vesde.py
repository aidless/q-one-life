import math

from src.vesde import (
    SIGMA_MAX,
    SIGMA_MIN,
    diffusion,
    drift,
    perturbation_kernel_mean,
    perturbation_kernel_std,
    run_vesde_slice,
    sample_perturbation,
    sigma,
)


def test_drift_is_zero():
    assert drift(2.0, 0.3) == 0.0


def test_constants():
    assert SIGMA_MIN == 0.0001
    assert SIGMA_MAX == 15.0
    assert sigma(0.0) == SIGMA_MIN
    assert math.isclose(sigma(1.0), SIGMA_MAX)


def test_diffusion_matches_formula():
    t = 0.5
    expected = SIGMA_MIN * (SIGMA_MAX / SIGMA_MIN) ** t * math.sqrt(
        2 * math.log(SIGMA_MAX / SIGMA_MIN)
    )
    assert math.isclose(diffusion(t), expected)


def test_perturbation_kernel():
    assert perturbation_kernel_mean(3.0, 0.5) == 3.0
    assert math.isclose(perturbation_kernel_std(0.5), sigma(0.5))
    assert sample_perturbation(3.0, 0.5, 0.0) == 3.0
    assert sample_perturbation(3.0, 0.5, 1.0) > 3.0


def test_slice_runs():
    out = run_vesde_slice()
    assert out["status"] == "vesde_formula_slice"
    assert out["checks"]["drift_zero"] is True
