import torch
import pytest

from src.adapters import (
    ADAPTER_HIDDEN_DIM, FunctionalAdapter, RepresentationDescriptor,
    LoRAAdapter, ConvPassAdapter, ADAMAdapter,
)
from src.descriptor import RunningStats, should_skip_task
from src.data import class_split, BENCHMARKS, VTAB_ADAM_DOMAINS
from src.sema import _average_accuracy, _incremental_accuracy
from src.vit_sema import SemaViT


def test_functional_adapter_shape_and_bottleneck():
    a = FunctionalAdapter(768)
    assert a.down.out_features == ADAPTER_HIDDEN_DIM == 48
    assert a(torch.randn(2, 5, 768)).shape == (2, 5, 768)


def test_descriptor_projects_to_128_with_leaky_relu():
    d = RepresentationDescriptor(768)
    assert d.encoder.out_features == 128
    assert isinstance(d.act, torch.nn.LeakyReLU)
    assert d.decoder.in_features == 128
    z, recon = d(torch.randn(2, 3, 768))
    assert tuple(z.shape) == (2, 3, 128) and tuple(recon.shape) == (2, 3, 768)


def test_lora_convpass_adam_shapes():
    x = torch.randn(2, 8, 768)
    assert LoRAAdapter(768)(x).shape == x.shape
    assert ConvPassAdapter(768)(x).shape == x.shape
    assert ADAMAdapter(768)(x).shape == x.shape


def test_running_stats_zscore():
    s = RunningStats()
    for v in (1.0, 2.0, 3.0):
        s.update(v)
    assert s.mean == pytest.approx(2.0)
    assert s.zscore(4.0) == pytest.approx(2.0)


def test_skip_rule():
    assert should_skip_task(set()) is True
    assert should_skip_task({11}) is False


def test_expandable_layers_are_last_three():
    m = SemaViT(num_classes=10)
    assert m.expandable_layers == list(range(m.num_blocks - 3, m.num_blocks))


def test_head_grows_preserving_old_logits():
    m = SemaViT(num_classes=4)
    before = m.head.weight.detach().clone()
    m.add_classifier(6)
    assert m.num_classes == 10
    assert torch.allclose(m.head.weight[:4].detach(), before)


def test_accuracy_metrics():
    matrix = [[0.5], [0.6, 0.7], [0.8, 0.6, 0.9]]
    assert _average_accuracy(matrix) == pytest.approx((0.8 + 0.6 + 0.9) / 3)
    assert _incremental_accuracy(matrix) == pytest.approx(((0.5) + (0.65) + (0.7666666667)) / 3)


def test_dataset_splits_are_ten_class():
    splits = class_split()
    assert len(splits) == 10 and all(len(s) == 10 for s in splits)
    assert BENCHMARKS["vtab"]["domains"] == VTAB_ADAM_DOMAINS
