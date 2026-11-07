"""Bounded code generation and sandbox execution for research experiments."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

CODE_LAB_SCHEMA = "q-one-code-lab-v1"
ModelCall = Callable[[str], str | None]

PROMPT = """You are writing one bounded Python research experiment.

Task:
{task}

Contract:
- Write a Python function named `run(data: dict) -> dict`.
- `data` is JSON-like and may contain datasets under `data["datasets"]`.
- Return only JSON-serializable values.
- Do not import network libraries, use files outside the temporary directory,
  use threads/processes, or call external commands.
- Use only the Python standard library and sklearn if installed.
- Do not print secrets or access environment variables.
- Return JSON only: {{"code": "<source string>"}}
"""

ALLOWED_IMPORT_PATTERN = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", re.MULTILINE)
BLOCKED_IMPORTS = {
    "socket", "ssl", "requests", "urllib", "http", "subprocess", "multiprocessing",
    "threading", "asyncio", "os.system", "pty", "ctypes", "pathlib.Path.home",
}
BLOCKED_TOKENS = (
    "os.system", "os.popen", "subprocess", "socket", "urllib", "requests",
    "__import__", "eval(", "exec(", "open('/etc", "open(\"/etc", "Path.home",
    "os.environ", "multiprocessing", "threading", "asyncio",
)


class CodeLabError(RuntimeError):
    """The generated experiment violates the execution contract."""


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def extract_code(answer: str | None) -> str:
    if not isinstance(answer, str) or not answer.strip():
        raise CodeLabError("model returned no code answer")
    stripped = answer.strip()
    if stripped.startswith("```"):
        stripped = "\n".join(stripped.splitlines()[1:-1])
    try:
        payload = json.loads(stripped)
    except ValueError as exc:
        raise CodeLabError("model output is not JSON") from exc
    code = payload.get("code") if isinstance(payload, dict) else None
    if not isinstance(code, str) or not code.strip():
        raise CodeLabError("model JSON does not contain code")
    return code.strip()


def validate_code(code: str) -> None:
    tree = compile(code, "<generated-experiment>", "exec", flags=1024, dont_inherit=True)
    del tree
    for match in ALLOWED_IMPORT_PATTERN.finditer(code):
        module = match.group(1).split(".", 1)[0]
        if module in BLOCKED_IMPORTS:
            raise CodeLabError(f"blocked import: {module}")
    lowered = code.lower()
    for token in BLOCKED_TOKENS:
        if token in lowered:
            raise CodeLabError(f"blocked token: {token}")
    if "def run(data: dict) -> dict" not in code and "def run(data)->dict" not in code.replace(" ", ""):
        raise CodeLabError("generated code must define run(data) -> dict")


def generate_code(task: str, model_call: ModelCall) -> dict[str, Any]:
    if not task.strip():
        raise CodeLabError("task is empty")
    if not callable(model_call):
        raise CodeLabError("model_call must be callable")
    code = extract_code(model_call(PROMPT.format(task=task.strip())))
    validate_code(code)
    return {"schema": CODE_LAB_SCHEMA, "task": task.strip(), "code": code,
            "code_sha256": _sha256_text(code)}


def execute_code(
    code: str,
    data: dict[str, Any],
    *,
    timeout_seconds: int = 30,
    max_output_bytes: int = 1_000_000,
) -> dict[str, Any]:
    validate_code(code)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="qone-code-lab-") as temporary:
        root = Path(temporary)
        input_path = root / "input.json"
        output_path = root / "output.json"
        runner_path = root / "runner.py"
        input_path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False))
        runner = (
            "import json\n"
            f"SOURCE = {code!r}\n"
            "namespace = {}\n"
            "exec(SOURCE, namespace)\n"
            "with open('input.json', encoding='utf-8') as handle:\n"
            "    payload = json.load(handle)\n"
            "result = namespace['run'](payload)\n"
            "encoded = json.dumps(result, ensure_ascii=False, allow_nan=False)\n"
            "if len(encoded.encode()) > 1_000_000:\n"
            "    raise RuntimeError('output exceeds 1 MiB')\n"
            "with open('output.json', 'w', encoding='utf-8') as handle:\n"
            "    handle.write(encoded)\n"
        )
        runner_path.write_text(runner)
        environment = {
            name: value for name, value in os.environ.items()
            if name in {"PATH", "LANG", "LC_ALL", "PYTHONHASHSEED", "HOME"}
        }
        environment["PYTHONHASHSEED"] = "0"
        environment["HOME"] = str(root)
        process = subprocess.run(
            ["python3", runner_path.name], cwd=root, env=environment,
            capture_output=True, text=True, timeout=timeout_seconds, check=False,
        )
        stdout = process.stdout.encode()[:max_output_bytes]
        stderr = process.stderr.encode()[:max_output_bytes]
        result = None
        if process.returncode == 0 and output_path.is_file():
            payload = output_path.read_bytes()[:max_output_bytes]
            result = json.loads(payload)
        return {
            "returncode": process.returncode,
            "elapsed_sec": time.monotonic() - start,
            "stdout_sha256": hashlib.sha256(stdout).hexdigest(),
            "stderr_sha256": hashlib.sha256(stderr).hexdigest(),
            "stdout_preview": stdout.decode(errors="replace")[:2000],
            "stderr_preview": stderr.decode(errors="replace")[:2000],
            "result": result,
            "sandbox": {
                "kind": "temporary_directory_subprocess",
                "network": "not_granted",
                "filesystem_scope": "temporary_directory",
                "timeout_seconds": timeout_seconds,
                "max_output_bytes": max_output_bytes,
            },
            "code_sha256": _sha256_text(code),
        }


def run_hidden_tests(code: str, execution: dict[str, Any], tests: list[dict[str, Any]]) -> dict[str, Any]:
    if not tests:
        raise CodeLabError("hidden tests are required")
    failures = []
    for test in tests:
        name = test.get("name") if isinstance(test, dict) else None
        check = test.get("check") if isinstance(test, dict) else None
        if not isinstance(name, str) or not callable(check):
            failures.append({"name": name, "error": "invalid_test"})
            continue
        try:
            passed = bool(check(execution))
            error = None
        except (KeyError, TypeError, ValueError) as exc:
            passed, error = False, type(exc).__name__
        failures.append({"name": name, "passed": passed, "error": error})
    return {
        "schema": "q-one-code-lab-hidden-tests-v1",
        "code_sha256": _sha256_text(code),
        "execution_sha256": _sha256_text(json.dumps(execution, sort_keys=True)),
        "tests": failures,
        "passed": all(item.get("passed") is True for item in failures),
    }
