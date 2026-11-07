"""Tests for the research-validation aggregation script."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "aggregate_research_validation.py"
SPEC = importlib.util.spec_from_file_location("aggregate_research_validation", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _run(task: str, seed: int, variant: str, delta: float, status: str = "completed") -> dict:
    return {
        "task_id": task,
        "kind": "extension",
        "seed": seed,
        "variant": variant,
        "status": status,
        "metric_name": "balanced_accuracy",
        "test_delta": delta if status == "completed" else None,
    }


def test_paired_requires_all_three_variants() -> None:
    runs = [
        _run("t", 1, "single_agent", 0.1),
        _run("t", 1, "multi_agent", 0.2),
        _run("t", 1, "no_rebuttal", 0.0),
        _run("t", 2, "single_agent", 0.1),
        _run("t", 2, "multi_agent", 0.2),
    ]
    pairs = MODULE.paired(runs)
    assert len(pairs) == 1
    assert pairs[0]["seed"] == 1
    assert abs(pairs[0]["multi_minus_single"] - 0.1) < 1e-12
    assert abs(pairs[0]["multi_minus_no_rebuttal"] - 0.2) < 1e-12


def test_sign_test_handles_ties_and_empty_input() -> None:
    assert MODULE.sign_test([0.1, 0.2, -0.1]) == {
        "positive": 2, "negative": 1, "ties": 0, "p_two_sided": 1.0,
    }
    assert MODULE.sign_test([0.0, 0.0])["p_two_sided"] is None


def test_load_run_flags_hash_failures(tmp_path: Path) -> None:
    directory = tmp_path / "t-1-single_agent"
    directory.mkdir()
    payload = directory / "metrics.json"
    payload.write_text("{}\n")
    receipt = {
        "task_id": "t", "seed": 1, "variant": "single_agent", "status": "completed",
        "metrics": {"metric_name": "balanced_accuracy", "test": 0.5, "baseline_test": 0.4,
                    "test_delta": 0.1, "validation": 0.5},
        "replay_matches": True, "test_used_for_selection": False, "model_calls": 4,
        "outputs": [{"path": "metrics.json", "sha256": "0" * 64}],
    }
    (directory / "receipt.json").write_text(json.dumps(receipt))
    run = MODULE.load_run(directory, {"t": "extension"})
    assert run["kind"] == "extension"
    assert run["hash_failures"] == ["metrics.json"]
