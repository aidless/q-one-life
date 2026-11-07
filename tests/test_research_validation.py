import hashlib
import json
from pathlib import Path

import pytest

from qone_life.research_factory.research_validation import (
    ValidationError,
    check_run_receipt,
    enforce_candidate,
    fault_battery,
    parse_proposal,
    verify_inputs,
)


def test_model_cannot_inject_command_or_test_selection():
    for payload in (
        {"family": "logistic", "scale": True, "strength": 1, "command": "curl x"},
        {"family": "logistic", "scale": True, "strength": 1, "select_on": "test"},
        {"family": "logistic", "scale": True, "strength": float("nan")},
    ):
        with pytest.raises(ValidationError):
            enforce_candidate(payload, "classification")


def test_candidate_validation_uses_exact_types_and_task_family():
    assert enforce_candidate(
        {"family": "ridge", "scale": False, "strength": 0.1}, "regression"
    )["family"] == "ridge"
    with pytest.raises(ValidationError):
        enforce_candidate({"family": "ridge", "scale": "false", "strength": 1}, "regression")
    with pytest.raises(ValidationError):
        enforce_candidate({"family": "ridge", "scale": True, "strength": True}, "regression")
    with pytest.raises(ValidationError):
        enforce_candidate({"family": "ridge", "scale": True, "strength": 1}, "classification")


def test_missing_model_response_is_not_a_fallback_success():
    with pytest.raises(ValidationError):
        parse_proposal(None, "classification")
    with pytest.raises(ValidationError):
        parse_proposal('{"candidates":[]}', "classification")


def test_model_proposal_requires_three_valid_candidates():
    candidate = {"family": "logistic", "scale": True, "strength": 1}
    assert len(parse_proposal(json.dumps({"candidates": [candidate] * 3}), "classification")) == 3


def test_input_hash_and_path_escape(tmp_path):
    raw = tmp_path / "data.json"
    raw.write_text('{"X": [[1]], "y": [0]}')
    entry = {"path": raw.name, "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()}
    verify_inputs(tmp_path, [entry])
    raw.write_text("tampered")
    with pytest.raises(ValidationError):
        verify_inputs(tmp_path, [entry])
    with pytest.raises(ValidationError):
        verify_inputs(tmp_path, [{"path": "../elsewhere", "sha256": "0" * 64}])


def test_run_receipt_requires_actual_replay_and_current_bytes(tmp_path):
    output = tmp_path / "metrics.json"
    output.write_text('{"score": 0.5}')
    receipt = {
        "status": "completed",
        "execution_kind": "real_cloud_training",
        "replay_matches": True,
        "metrics": {"validation": 0.5, "test": 0.5},
        "outputs": [{"path": output.name, "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}],
    }
    assert check_run_receipt(receipt, tmp_path)["passed"]
    output.write_text("tampered")
    assert not check_run_receipt(receipt, tmp_path)["passed"]


def test_fault_battery_has_positive_controls_and_scope_binding():
    report = fault_battery()
    assert report["passed"]
    assert report["positive_controls"] >= 1
    assert report["detected"] == report["injected"]
    names = {item["case"] for item in report["cases"]}
    assert {"forged_closure", "evaluator_changed", "missing_output", "timeout", "network_failure"} <= names
