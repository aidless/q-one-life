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
import tarfile
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .code_lab import ALLOWED_IMPORT_PATTERN, BLOCKED_IMPORTS, BLOCKED_TOKENS, CodeLabError

PROJECT_LAB_SCHEMA = "q-one-project-lab-v1"
PACKAGE_LAB_SCHEMA = "q-one-paperbench-package-v1"
ModelCall = Callable[[str], str | None]

MINIMAL_PROJECT_PROMPT = """You are writing a small, self-contained Python research project.

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

FULL_PACKAGE_PROMPT = """You are writing a complete PaperBench-style reproduction submission package.

Task:
{task}

Return one JSON object only: {{"files": [{{"path": "...", "content": "..."}}]}}.

Required files:
- `README.md`: describe the task, the implemented methods and the evidence boundary.
- `requirements.txt`: list only the runtime dependencies actually used.
- `reproduce.sh`: a shell script that runs `python3 run.py < data/sample.json` and `python3 -m pytest -q tests`.
- `run.py`: reads JSON from stdin and prints one JSON object to stdout.
- `src/core.py`: exposes `parse_answer`, `modal_answer`, `cpw_answer`, `scw_answer`
  and `run(data: dict) -> dict`.
- `src/datasets.py`: loads `data/sample.json`.
- `src/embeddings.py`: deterministic standard-library-only text vectors.
- `src/methods.py`: CPW and SCW aggregation helpers.
- `tests/test_project.py`: at least five unit tests.
- `data/sample.json`: JSON with `datasets.answers` and `datasets.responses`.

Contract:
- Use only the Python standard library. No network, no subprocess, no threads,
  no environment variables and no files outside the project directory.
- `run(data)` must read `data["datasets"]["answers"]`, call `modal_answer`, and
  return a JSON-serializable dict containing at least `chosen`, `parsed`, `cpw`
  and `scw`.
- `parse_answer(text)` extracts the text after "The answer is", strips whitespace,
  trailing periods and surrounding parentheses, and returns None when absent.
- `cpw_answer(responses)` and `scw_answer(responses)` return a string answer or None.
- Host-side hidden tests are provided separately and are never shown to you.
- Return JSON only; no markdown fences and no prose.
"""

MINIMAL_REQUIRED = ("src/core.py", "tests/test_project.py", "run.py")
FULL_PACKAGE_REQUIRED = (
    "README.md", "requirements.txt", "reproduce.sh", "run.py",
    "src/core.py", "src/datasets.py", "src/embeddings.py", "src/methods.py",
    "tests/test_project.py", "data/sample.json",
)
PROFILE_REQUIRED = {"minimal": MINIMAL_REQUIRED, "paperbench": FULL_PACKAGE_REQUIRED}

SAFE_PATH_RE = re.compile(
    r"^(?:README\.md|requirements\.txt|reproduce\.sh|run\.py|MANIFEST\.json"
    r"|(?:src|tests|data|results)/[A-Za-z0-9_./-]+)$"
)
MAX_FILES = 20
MAX_FILE_BYTES = 100_000


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_json_object(answer: str | None) -> dict[str, Any]:
    """Return the first complete JSON object embedded in a model answer."""
    if not isinstance(answer, str) or not answer.strip():
        raise CodeLabError("model returned no project answer")
    decoder = json.JSONDecoder()
    for index, char in enumerate(answer):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(answer[index:])
        except ValueError:
            continue
        if isinstance(payload, dict):
            return payload
    raise CodeLabError("model output is not a JSON object")


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


def parse_project(
    answer: str | None,
    required_files: tuple[str, ...] = MINIMAL_REQUIRED,
) -> dict[str, str]:
    payload = _extract_json_object(answer)
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
    for required in required_files:
        if required not in files:
            raise CodeLabError(f"missing required project file: {required}")
    if "def run(data: dict) -> dict" not in files["src/core.py"].replace("'", '"'):
        # Accept either quote style; the exact signature is checked at execution.
        if "def run(data) -> dict" not in files["src/core.py"]:
            raise CodeLabError("src/core.py must define run(data) -> dict")
    return files


def generate_project(
    task: str,
    model_call: ModelCall,
    *,
    profile: str = "minimal",
    attempts: int = 3,
) -> dict[str, Any]:
    if not task.strip():
        raise CodeLabError("task is empty")
    if not callable(model_call):
        raise CodeLabError("model_call must be callable")
    if profile not in PROFILE_REQUIRED:
        raise CodeLabError(f"unknown project profile: {profile}")
    if attempts < 1:
        raise CodeLabError("attempts must be >= 1")
    prompt = (FULL_PACKAGE_PROMPT if profile == "paperbench" else MINIMAL_PROJECT_PROMPT).format(
        task=task.strip()
    )
    required_files = PROFILE_REQUIRED[profile]
    last_error: CodeLabError | None = None
    for attempt in range(1, attempts + 1):
        try:
            files = parse_project(model_call(prompt), required_files=required_files)
            break
        except CodeLabError as exc:
            last_error = exc
            if attempt == attempts:
                raise last_error
    manifest = "\n".join(f"{path}\t{_sha256_text(content)}" for path, content in sorted(files.items()))
    return {"schema": PROJECT_LAB_SCHEMA, "task": task.strip(), "profile": profile,
            "required_files": list(required_files), "attempts_used": attempt,
            "files": files, "manifest_sha256": _sha256_text(manifest)}


def package_project(
    files: dict[str, str],
    *,
    output_dir: Path,
    paper_id: str,
    task: str = "",
    manifest_sha256: str = "",
    hidden_tests_sha256: str = "",
    verification_sha256: str = "",
) -> dict[str, Any]:
    """Materialise a PaperBench DirectSubmission tree and a local tar archive."""
    if not re.fullmatch(r"[a-z0-9-]+", paper_id):
        raise CodeLabError(f"unsafe paper_id: {paper_id}")
    paper_root = output_dir / paper_id
    submission_dir = paper_root / "submission"
    if submission_dir.exists() and any(submission_dir.iterdir()):
        raise CodeLabError(f"submission directory is not empty: {submission_dir}")
    packaged_files = dict(files)
    packaged_files.setdefault("src/__init__.py", "")
    for path, content in packaged_files.items():
        if not isinstance(path, str) or not isinstance(content, str):
            raise CodeLabError("project files must be string pairs")
        _validate_project_file(path, content)
    build_project(packaged_files, submission_dir)
    file_hashes = {path: _sha256_text(content) for path, content in sorted(packaged_files.items())}
    manifest = {
        "schema": PACKAGE_LAB_SCHEMA,
        "paper_id": paper_id,
        "task": task,
        "manifest_sha256": manifest_sha256 or _sha256_text(
            "\n".join(f"{path}\t{digest}" for path, digest in file_hashes.items())
        ),
        "hidden_tests_sha256": hidden_tests_sha256,
        "verification_sha256": verification_sha256,
        "file_hashes": file_hashes,
    }
    (submission_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    archive_path = paper_root.parent / f"{paper_id}-submission.tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(submission_dir, arcname="submission")
    return {
        "schema": PACKAGE_LAB_SCHEMA,
        "paper_id": paper_id,
        "submission_dir": str(submission_dir),
        "archive_path": str(archive_path),
        "file_count": len(packaged_files) + 1,
        "manifest_sha256": manifest["manifest_sha256"],
        "hidden_tests_sha256": hidden_tests_sha256,
        "verification_sha256": verification_sha256,
    }


def generate_project_receipt_hash(receipt: dict[str, Any]) -> str:
    return _sha256_text(json.dumps(receipt, sort_keys=True, ensure_ascii=False))


def _project_manifest(files: dict[str, str]) -> str:
    manifest = "\n".join(f"{path}\t{_sha256_text(content)}" for path, content in sorted(files.items()))
    return _sha256_text(manifest)


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
