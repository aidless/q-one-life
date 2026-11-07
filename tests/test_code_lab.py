import json
import math

import pytest

from qone_life.research_factory.code_lab import (
    CodeLabError,
    execute_code,
    generate_code,
    run_hidden_tests,
    validate_code,
)


def _answer(code: str) -> str:
    return json.dumps({"code": code})


def test_generate_code_rejects_missing_run() -> None:
    with pytest.raises(CodeLabError):
        validate_code("def train(data):\n    return {}\n")


def test_generate_code_rejects_network_and_processes() -> None:
    for code in (
        "import socket\n\ndef run(data: dict) -> dict:\n    return {}\n",
        "import subprocess\n\ndef run(data: dict) -> dict:\n    return {}\n",
        "def run(data: dict) -> dict:\n    return __import__('socket')\n",
    ):
        with pytest.raises(CodeLabError):
            validate_code(code)


def test_generate_code_accepts_contract() -> None:
    code = "def run(data: dict) -> dict:\n    return {'n': len(data['datasets']['x'])}\n"
    receipt = generate_code("Count rows", lambda prompt: _answer(code))
    assert receipt["code"] == code.strip()
    assert receipt["code_sha256"]


def test_execute_code_runs_isolated_and_returns_result() -> None:
    code = """
def run(data: dict) -> dict:
    values = data['datasets']['x']
    return {'mean': sum(values) / len(values)}
"""
    result = execute_code(code, {"datasets": {"x": [1, 2, 3]}})
    assert result["returncode"] == 0
    assert math.isclose(result["result"]["mean"], 2.0)
    assert result["sandbox"]["network"] == "not_granted"


def test_execute_code_failures_do_not_return_result() -> None:
    code = "def run(data: dict) -> dict:\n    raise RuntimeError('failed')\n"
    result = execute_code(code, {})
    assert result["returncode"] != 0
    assert result["result"] is None
    assert "RuntimeError" in result["stderr_preview"]


def test_hidden_tests_do_not_appear_in_prompt_or_execution() -> None:
    code = "def run(data: dict) -> dict:\n    return {'ok': True}\n"
    execution = execute_code(code, {})
    tests = [{"name": "result_is_true",
              "check": lambda result: result["result"]["ok"] is True}]
    receipt = run_hidden_tests(code, execution, tests)
    assert receipt["passed"]
    assert execution["result"] == {"ok": True}
