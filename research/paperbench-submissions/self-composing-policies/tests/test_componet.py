import torch
import pytest

from src.agent import CompoNetAgent
from src.baseline import growth_report, componet_param_count, progressive_param_count
from src.componet import CompoNetModule, cosine_positional_matrix
from src.encoder import ALEEncoder
from src.metrics import average_performance, forward_transfer, matching_rate


def test_encoder_output_and_frozen_backbone():
    e = ALEEncoder()
    assert e(torch.zeros(2, 4, 210, 160)).shape == (2, 512)
    assert e.conv1.out_channels == 32 and e.conv1.kernel_size == (8, 8)
    assert e.conv2.out_channels == 64 and e.conv2.kernel_size == (4, 4)
    assert e.conv3.out_channels == 64 and e.conv3.kernel_size == (3, 3)


def test_new_encoder_inherits_previous_weights():
    e = ALEEncoder()
    e(torch.zeros(1, 4, 210, 160))
    clone = e.clone_with_init()
    assert torch.equal(clone.conv1.weight, e.conv1.weight)


def test_first_module_has_empty_phi():
    m = CompoNetModule(512, 64, 6)
    out, v = m(torch.randn(3, 512), torch.zeros(3, 0, 6))
    assert out.shape == (3, 6) and v.shape == (3, 6)


def test_chain_shape_and_constant_module_parameters():
    h = torch.randn(2, 512)
    m1 = CompoNetModule(512, 64, 6)
    phi = m1(h, torch.zeros(2, 0, 6))[0].unsqueeze(1)
    counts = []
    for n in range(2, 7):
        m = CompoNetModule(512, 64, 6)
        out, _ = m(h, phi)
        counts.append(m.core_parameter_count())
        phi = torch.cat([phi, out.unsqueeze(1)], dim=1)
    assert len(set(counts)) == 1
    assert phi.shape == (2, 6, 6)


def test_continuous_output_is_normalised():
    m = CompoNetModule(512, 64, 6, continuous=True)
    out, _ = m(torch.randn(2, 512), torch.randn(2, 2, 6))
    assert torch.allclose(out.norm(dim=-1), torch.ones(2), atol=1e-5)


def test_positional_matrix_matches_target_shape():
    P = torch.randn(4, 6)
    assert cosine_positional_matrix(4, 6).shape == P.shape


def test_freeze_all_but_last():
    a = CompoNetAgent(n_actions=6)
    a.add_module()
    a.add_module()
    a.freeze_all_but_last()
    frozen = [sum(p.requires_grad for p in m.parameters()) for m in a.policy_modules]
    assert frozen[0] == 0 and frozen[1] > 0


def test_parameter_growth_is_linear_and_rivals_quadratic():
    per_module = 104_106
    assert componet_param_count(20, per_module) == 20 * per_module
    assert progressive_param_count(20, 1_000_000) == 1_000_000 * 20 * 21 // 2
    g = growth_report(6, per_module, 1_000_000)
    assert g["componet_total"] == 6 * per_module


def test_metrics():
    assert average_performance({"a": [0.4, 0.6], "b": [0.8]}) == pytest.approx(0.65)
    assert forward_transfer([0.8, 0.6], [0.8, 0.4]) == pytest.approx(0.5)
    assert matching_rate([[1, 0], [0, 1]], [[1, 0], [1, 0]]) == pytest.approx(0.5)
