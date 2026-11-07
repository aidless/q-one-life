import json

from qone_life.cli import main

CODE = json.dumps({
    "code": "def run(data: dict) -> dict:\n    return {'sum': sum(data['x'])}\n"
})


def test_research_code_execute_and_test(tmp_path):
    code = tmp_path / "code.json"
    data = tmp_path / "data.json"
    execution = tmp_path / "execution.json"
    tests_module = tmp_path / "hidden_tests.py"
    result = tmp_path / "result.json"
    code.write_text(CODE)
    data.write_text(json.dumps({"x": [1, 2, 3]}))
    execution.write_text("{}")
    tests_module.write_text(
        "TESTS = [{'name': 'sum', 'check': lambda result: result['result']['sum'] == 6}]\n"
    )
    execute_code = main([
        "research-code", "execute", "--code", str(code),
        "--data", str(data), "--output", str(execution),
    ])
    assert execute_code == 0
    test_code = main([
        "research-code", "test", "--code", str(code),
        "--execution", str(execution), "--tests", f"{tests_module}::TESTS",
        "--output", str(result),
    ])
    assert test_code == 0
    payload = json.loads(result.read_text())
    assert payload["passed"] is True
