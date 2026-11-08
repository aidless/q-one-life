import pytest
import torch

from src.cfg import (
    benchmark_manifest,
    cfg_logits,
    combine_logits,
    run_cfg_slice,
    unconditional_start,
)


def test_gamma_one_is_conditional():
    cond = torch.tensor([[1.0, 2.0]])
    uncond = torch.tensor([[9.0, 9.0]])
    assert torch.allclose(combine_logits(cond, uncond, 1.0), cond)


def test_gamma_one_point_five_matches_hand_calculation():
    cond = torch.tensor([[1.0, 3.0]])
    uncond = torch.tensor([[0.0, 1.0]])
    expected = torch.tensor([[1.5, 4.0]])
    assert torch.allclose(combine_logits(cond, uncond, 1.5), expected)


def test_unconditional_branch_starts_at_last_prompt_token():
    assert unconditional_start(4) == 3
    with pytest.raises(ValueError):
        unconditional_start(0)


@pytest.mark.parametrize("gamma", [-0.1, "1.5", True])
def test_invalid_gamma(gamma):
    logits = torch.tensor([[1.0]])
    with pytest.raises(ValueError):
        combine_logits(logits, logits, gamma)


def test_shape_mismatch_rejected():
    with pytest.raises(ValueError):
        combine_logits(torch.tensor([[1.0]]), torch.tensor([[1.0, 2.0]]), 1.5)


def test_cfg_alias_and_manifest():
    cond = torch.tensor([[2.0]])
    uncond = torch.tensor([[1.0]])
    assert cfg_logits(cond, uncond, 1.5).item() == 2.5
    manifest = benchmark_manifest()
    assert len(manifest) == 9
    assert all(row["available"] is False for row in manifest)


def test_run_slice():
    out = run_cfg_slice()
    assert out["status"] == "cfg_inference_slice"
    assert out["guided_logits"] == [[1.25, 2.75, 4.25]]
