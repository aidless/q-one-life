import json
import math

import pytest

from qone_life.research_factory.project_lab import (
    CodeLabError,
    build_project,
    generate_project,
    parse_project,
    verify_project,
)

FILES = {
    "src/core.py": (
        "import json\n"
        "import sys\n\n"
        "def run(data: dict) -> dict:\n"
        "    values = data['datasets']['x']\n"
        "    return {'mean': sum(values) / len(values)}\n\n"
        "if __name__ == '__main__':\n"
        "    data = json.load(sys.stdin)\n"
        "    print(json.dumps(run(data)))\n"
    ),
    "tests/test_project.py": (
        "from src.core import run\n\n"
        "def test_mean():\n"
        "    assert run({'datasets': {'x': [1, 2, 3]}})['mean'] == 2.0\n"
    ),
    "run.py": (
        "import json\nimport sys\n"
        "from src.core import run\n"
        "print(json.dumps(run(json.load(sys.stdin))))\n"
    ),
}


def _answer(files: dict[str, str]) -> str:
    return json.dumps({"files": [{"path": p, "content": c} for p, c in files.items()]})


def test_parse_project_accepts_valid_manifest() -> None:
    parsed = parse_project(_answer(FILES))
    assert parsed == FILES


def test_parse_project_rejects_unsafe_path() -> None:
    bad = dict(FILES)
    bad["../escape.py"] = "print('x')\n"
    with pytest.raises(CodeLabError):
        parse_project(_answer(bad))


def test_parse_project_rejects_blocked_import() -> None:
    bad = dict(FILES)
    bad["src/core.py"] = "import socket\n" + FILES["src/core.py"]
    with pytest.raises(CodeLabError):
        parse_project(_answer(bad))


def test_parse_project_requires_required_files() -> None:
    with pytest.raises(CodeLabError):
        parse_project(_answer({"src/core.py": FILES["src/core.py"]}))


def test_generate_project_receipt_has_manifest_hash() -> None:
    receipt = generate_project("Compute a mean", lambda prompt: _answer(FILES))
    assert receipt["schema"] == "q-one-project-lab-v1"
    assert receipt["manifest_sha256"]


def test_build_and_verify_project_passes() -> None:
    hidden = (
        "def test_host_hidden_mean():\n"
        "    from src.core import run\n"
        "    assert run({'datasets': {'x': [2, 4]}})['mean'] == 3.0\n"
    )
    receipt = verify_project(FILES, input_data={"datasets": {"x": [1, 2, 3]}}, hidden_tests=hidden)
    assert receipt["passed"]
    assert receipt["pytest_returncode"] == 0
    assert receipt["run_returncode"] == 0
