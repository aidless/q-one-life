"""Multi-file project generation and verification for autonomous research.

Extends the single-function code lab with a project contract:
- The model returns a JSON object with a list of files, each {"path", "content"}.
- Paths are restricted to a safe relative allow-list.
- Each Python file must pass the same blocked-import / blocked-token gate.
- The generated project is materialised in a temporary directory and its own
  test suite is executed there. Hidden tests are supplied by the host and are
  never shown to the model.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .code_lab import ALLOWED_IMPORT_PATTERN, BLOCKED_IMPORTS, BLOCKED_TOKENS, CodeLabError

PROJECT_LAB_SCHEMA = "q-one-project-lab-v1"
ModelCall = Callable[[str], str | None]

PROJECT_PROMPT = """You are writing a small, self-contained Python research project.

Task:
{task}

Contract:
- Return a single JSON object: {{"files": [{{"path": "relative/path.py", "content": "..."}}]}}.
- Include a `src/` package, a `tests/test_project.py` file and a `run.py` entrypoint.
- The project must expose `run(data: dict) -> dict` from `src.core` and use only
  the Python standard library.
- Do not import network libraries, use files outside the project directory,
  use threads/processes, call external commands or access environment variables.
- `tests/test_project.py` may use pytest. Hidden tests are provided separately.
- Return JSON only; no markdown fences and no prose.
"""

SAFE_PATH_RE = re.compile(r"^(?:run\.py|(?:src|tests|data|results)/[A-Za-z0-9_./-]+)$")
MAX_FILES = 20
MAX_FILE_BYTES = 100_000


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _validate_project_file(path: str, content: str) -> None:
    if not SAFE_PATH_RE.match(path) or ".." in path or path.startswith("/"):
        raise CodeLabError(f"unsafe project path: {path}")
    if path.endswith(".py"):
        compile(content, path, "exec", flags=1024, dont_inherit=True)
        for match in ALLOWED_IMPORT_PATTERN.finditer(content):
            if match.group(1).split(".", 1)[0] in BLOCKED_IMPORTS:
                raise CodeLabError(f"blocked import in {path}")
        lowered = content.lower()
        for token in BLOCKED_TOKENS:
            if token in lowered:
                raise CodeLabError(f"blocked token in {path}: {token}")


def parse_project(answer: str | None) -> dict[str, str]:
    if not isinstance(answer, str) or not answer.strip():
        raise CodeLabError("model returned no project answer")
    stripped = answer.strip()
    if stripped.startswith("```"):
        stripped = "\n".join(stripped.splitlines()[1:-1])
    try:
        payload = json.loads(stripped)
    except ValueError as exc:
        raise CodeLabError("model output is not JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise CodeLabError("project JSON must contain a files list")
    files: dict[str, str] = {}
    for entry in payload["files"]:
        if not isinstance(entry, dict):
            raise CodeLabError("project file entry must be an object")
        path, content = entry.get("path"), entry.get("content")
        if not isinstance(path, str) or not isinstance(content, str):
            raise CodeLabError("project file entry needs path and content strings")
        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            raise CodeLabError(f"project file too large: {path}")
        if path in files:
            raise CodeLabError(f"duplicate project path: {path}")
        _validate_project_file(path, content)
        files[path] = content
    if len(files) > MAX_FILES:
        raise CodeLabError("too many project files")
    for required in ("src/core.py", "tests/test_project.py", "run.py"):
        if required not in files:
            raise CodeLabError(f"missing required project file: {required}")
    if "def run(data: dict) -> dict" not in files["src/core.py"].replace("'", '"'):
        # Accept either quote style; the exact signature is checked at execution.
        if "def run(data) -> dict" not in files["src/core.py"]:
            raise CodeLabError("src/core.py must define run(data) -> dict")
    return files


def generate_project(task: str, model_call: ModelCall) -> dict[str, Any]:
    if not task.strip():
        raise CodeLabError("task is empty")
    if not callable(model_call):
        raise CodeLabError("model_call must be callable")
    files = parse_project(model_call(PROJECT_PROMPT.format(task=task.strip())))
    manifest = "\n".join(f"{path}\t{_sha256_text(content)}" for path, content in sorted(files.items()))
    return {"schema": PROJECT_LAB_SCHEMA, "task": task.strip(), "files": files,
            "manifest_sha256": _sha256_text(manifest)}


def build_project(files: dict[str, str], output_dir: Path, hidden_tests: str | None = None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, content in files.items():
        target = output_dir / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (output_dir / "src/__init__.py").write_text("", encoding="utf-8")
    if hidden_tests is not None:
        (output_dir / "tests/host_hidden_tests.py").write_text(hidden_tests, encoding="utf-8")


def verify_project(
    files: dict[str, str],
    *,
    input_data: dict[str, Any],
    hidden_tests: str,
    timeout_seconds: int = 60,
) -> dict[str, Any]:
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="qone-project-lab-") as temporary:
        root = Path(temporary) / "project"
        build_project(files, root, hidden_tests)
        environment = {
            name: value for name, value in os.environ.items()
            if name in {"PATH", "LANG", "LC_ALL", "PYTHONHASHSEED", "HOME"}
        }
        environment["PYTHONHASHSEED"] = "0"
        environment["HOME"] = str(root)
        environment["PYTHONPATH"] = str(root)
        process = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "tests", "--disable-warnings"],
            cwd=root, env=environment, capture_output=True, text=True,
            timeout=timeout_seconds, check=False,
        )
        runner = subprocess.run(
            [sys.executable, "run.py"],
            cwd=root, env=environment, capture_output=True, text=True,
            timeout=timeout_seconds, check=False,
            input=json.dumps(input_data),
        )
        return {
            "schema": "q-one-project-lab-verification-v1",
            "elapsed_sec": time.monotonic() - start,
            "pytest_returncode": process.returncode,
            "pytest_stdout_sha256": _sha256_text(process.stdout),
            "pytest_stderr_sha256": _sha256_text(process.stderr),
            "pytest_stdout_preview": process.stdout[-2000:],
            "pytest_stderr_preview": process.stderr[-2000:],
            "run_returncode": runner.returncode,
            "run_stdout_preview": runner.stdout[-2000:],
            "run_stderr_preview": runner.stderr[-2000:],
            "passed": process.returncode == 0 and runner.returncode == 0,
            "sandbox": {"kind": "temporary_directory_subprocess",
                        "network": "not_granted",
                        "filesystem_scope": "temporary_directory",
                        "timeout_seconds": timeout_seconds},
        }
