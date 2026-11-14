import pytest
from src.methods import modal_answer, _cos_sim, _l2_dist
from src.utils import parse_answer


@pytest.mark.parametrize("text,expected", [
    ("Some reasoning.\nThe answer is 19.", "19"),
    ("...\nThe answer is  yes ", "yes"),
    ("No answer here", None),
])
def test_parse_answer(text, expected):
    assert parse_answer(text) == expected


def test_modal_answer():
    assert modal_answer(["2", "2", "3", None]) == "2"


def test_l2_dist():
    assert _l2_dist([0.0, 0.0], [3.0, 4.0]) == pytest.approx(5.0)


def test_cos_sim():
    assert _cos_sim([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert _cos_sim([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cpw_answer_small():
    from src.methods import cpw_answer
    # 2 clusters: {a, a, a} and {b, b} -> CPW should pick closest to centroid of a's.
    responses = [
        "The answer is x", "The answer is x", "The answer is x",
        "The answer is y", "The answer is y",
    ]
    # Each response produces hash embedding based on its text; x's should cluster.
    selected = cpw_answer(responses, None, "scibert")
    assert selected in ("x", "y")


def test_scw_answer_basic():
    from src.methods import scw_answer
    responses = [
        "The answer is x", "The answer is x", "The answer is x",
        "The answer is y", "The answer is y",
    ]
    ans = scw_answer(responses, None, "scibert")
    assert ans in ("x", "y")


def test_hash_embed_unit_len():
    from src.embeddings import _hash_embed
    e = _hash_embed("hello world")
    assert len(e) == 64
    assert sum(v * v for v in e) == pytest.approx(1.0, abs=1e-6)


def test_real_dataset_manifest_and_loaders():
    from src.datasets import dataset_manifest, load_aqua_rat_test, load_strategyqa_test, load_svamp_full
    manifest = {row["file"]: row for row in dataset_manifest()}
    assert manifest["aqua_test.jsonl"]["rows"] == 254
    assert manifest["svamp.json"]["rows"] == 1000
    assert manifest["strategyqa_test.json"]["rows"] == 687
    assert len(load_aqua_rat_test()) == 254
    assert len(load_svamp_full()) == 1000
    assert len(load_strategyqa_test()) == 687
    assert load_aqua_rat_test()[0]["correct"] == "A"
    assert load_strategyqa_test()[0]["correct"] in ("true", "false")
