"""Submit and monitor research jobs on the remote AMD compute node.

Local execution is limited to orchestration. Every job runs on the configured
SSH host; nothing is executed on this workstation.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_HOST = "root@36.150.116.206"
DEFAULT_PORT = 34677
DEFAULT_KEY = "~/.ssh/id_rsa"
DEFAULT_REMOTE_ROOT = "/workspace/qone-jobs"

MAX_RUNTIME_SEC = 4 * 60 * 60
MAX_DISK_GB = 50
MAX_CONCURRENT = 2

STATUS_VALUES = {"queued", "running", "succeeded", "failed"}

# Remote wrapper: writes status transitions and an exit code file.
# The run script placeholder is substituted literally, so no str.format is used.
REMOTE_RUNNER_TEMPLATE = """#!/bin/bash
set -u
cd "$(dirname "$0")"
python3 -c "import json,pathlib;pathlib.Path('status.json').write_text(json.dumps({'state':'running'}))"
bash __RUN_SCRIPT__ > stdout.log 2> stderr.log
ec=$?
printf '%s' "$ec" > exit_code.txt
if [ "$ec" -eq 0 ]; then state=succeeded; else state=failed; fi
python3 - "$state" "$ec" <<'PY'
import json, pathlib, sys
pathlib.Path('status.json').write_text(json.dumps({'state': sys.argv[1], 'exit_code': int(sys.argv[2])}))
PY
"""


class CloudExecutionError(RuntimeError):
    """Raised when a cloud job cannot be submitted, monitored or fetched."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class CloudExecutor:
    """Drive a job directory on the remote host over SSH."""

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        key_path: str | Path = DEFAULT_KEY,
        remote_root: str = DEFAULT_REMOTE_ROOT,
        *,
        timeout: int = 30,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.key_path = Path(key_path).expanduser()
        self.remote_root = remote_root.rstrip("/")
        self.timeout = timeout

    def _ssh(self, command: str, *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        argv = [
            "ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={min(self.timeout, 15)}",
            "-p", str(self.port), "-i", str(self.key_path), self.host, command,
        ]
        try:
            return subprocess.run(argv, capture_output=True, text=True, check=False,
                                  timeout=timeout or self.timeout)
        except subprocess.TimeoutExpired as exc:
            raise CloudExecutionError(f"ssh timeout running: {command}") from exc

    def _scp(self, source: str, target: str, *, recursive: bool = False) -> None:
        argv = [
            "scp", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={min(self.timeout, 15)}",
            "-P", str(self.port), "-i", str(self.key_path),
        ]
        if recursive:
            argv.append("-r")
        argv.extend([source, target])
        try:
            result = subprocess.run(argv, capture_output=True, text=True, check=False,
                                    timeout=self.timeout)
        except subprocess.TimeoutExpired as exc:
            raise CloudExecutionError(f"scp timeout: {source} -> {target}") from exc
        if result.returncode != 0:
            raise CloudExecutionError(f"scp failed: {result.stderr.strip()}")

    def _require_ok(self, result: subprocess.CompletedProcess[str], action: str) -> str:
        if result.returncode != 0:
            raise CloudExecutionError(f"{action} failed ({result.returncode}): {result.stderr.strip()}")
        return result.stdout

    def _remote_job_dir(self, job_id: str) -> str:
        return f"{self.remote_root}/{job_id}"

    def _validate_job(self, job_dir: Path) -> dict[str, Any]:
        job_path = job_dir / "job.json"
        if not job_path.is_file():
            raise CloudExecutionError(f"job.json is missing in {job_dir}")
        job = json.loads(job_path.read_text(encoding="utf-8"))
        for key in ("job_id", "run_script"):
            if not str(job.get(key) or "").strip():
                raise CloudExecutionError(f"job.json missing required key: {key}")
        run_script = job_dir / job["run_script"]
        if not run_script.is_file():
            raise CloudExecutionError(f"run script is missing: {run_script}")
        runtime = int(job.get("max_runtime_sec", 0))
        if runtime <= 0 or runtime > MAX_RUNTIME_SEC:
            raise CloudExecutionError(f"max_runtime_sec must be 1..{MAX_RUNTIME_SEC}, got {runtime}")
        disk = float(job.get("max_disk_gb", 0))
        if disk <= 0 or disk > MAX_DISK_GB:
            raise CloudExecutionError(f"max_disk_gb must be 1..{MAX_DISK_GB}, got {disk}")
        for entry in job.get("inputs", []) or []:
            rel = Path(str(entry))
            if rel.is_absolute() or ".." in rel.parts:
                raise CloudExecutionError(f"input path must be relative: {entry}")
            if not (job_dir / rel).is_file():
                raise CloudExecutionError(f"input is missing: {entry}")
        return job

    def _running_jobs(self) -> int:
        listing = self._ssh(f"ls -1 {shlex.quote(self.remote_root)} 2>/dev/null || true")
        count = 0
        for name in listing.stdout.split():
            if not name:
                continue
            raw = self._ssh(
                f"cat {shlex.quote(self._remote_job_dir(name))}/status.json 2>/dev/null || true"
            ).stdout.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if payload.get("state") in {"queued", "running"}:
                count += 1
        return count

    def submit(self, job_dir: str | Path) -> dict[str, Any]:
        job_dir = Path(job_dir).expanduser().resolve()
        job = self._validate_job(job_dir)
        if self._running_jobs() >= MAX_CONCURRENT:
            raise CloudExecutionError(f"concurrent job limit reached ({MAX_CONCURRENT}); wait for a slot")

        job_id = job["job_id"]
        remote = self._remote_job_dir(job_id)
        self._require_ok(self._ssh(f"mkdir -p {shlex.quote(remote)}"), "mkdir remote job dir")
        # Copy the *contents* of the job directory into the remote job dir.
        for item in sorted(job_dir.iterdir()):
            if item.name.startswith(".qone-runner"):
                continue
            self._scp(str(item), f"{self.host}:{remote}/", recursive=item.is_dir())

        # Ensure the remote runner exists and is executable.
        runner = job_dir / ".qone-runner.sh"
        local_runner = REMOTE_RUNNER_TEMPLATE.replace(
            "__RUN_SCRIPT__", shlex.quote(job["run_script"])
        )
        runner.write_text(local_runner, encoding="utf-8")
        self._scp(str(runner), f"{self.host}:{remote}/.qone-runner.sh")
        runner.unlink()
        self._require_ok(self._ssh(f"chmod +x {shlex.quote(remote)}/.qone-runner.sh"), "chmod runner")

        inputs = [
            {"path": Path(str(e)).as_posix(), "sha256": sha256_file(job_dir / str(e))}
            for e in (job.get("inputs", []) or [])
        ]

        launch = (
            f"cd {shlex.quote(remote)} && "
            f"nohup bash .qone-runner.sh >/dev/null 2>&1 & echo $!"
        )
        result = self._ssh(launch)
        return {
            "job_id": job_id,
            "remote_dir": remote,
            "pid": result.stdout.strip(),
            "submitted_at": _now(),
            "max_runtime_sec": job["max_runtime_sec"],
            "max_disk_gb": job["max_disk_gb"],
            "inputs": inputs,
        }

    def poll(self, job_id: str) -> dict[str, Any]:
        remote = self._remote_job_dir(job_id)
        raw = self._ssh(f"cat {shlex.quote(remote)}/status.json 2>/dev/null || true").stdout.strip()
        if not raw:
            return {"job_id": job_id, "state": "queued", "raw": {}}
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise CloudExecutionError(f"status.json is not valid JSON for {job_id}") from exc
        state = payload.get("state")
        if state not in STATUS_VALUES:
            raise CloudExecutionError(f"unknown job state {state!r} for {job_id}")
        return {"job_id": job_id, "state": state, "raw": payload}

    def wait(self, job_id: str, *, max_runtime_sec: int, poll_interval: int = 10) -> dict[str, Any]:
        started = time.monotonic()
        while True:
            current = self.poll(job_id)
            if current["state"] in {"succeeded", "failed"}:
                return current
            if time.monotonic() - started > max_runtime_sec:
                self._ssh(
                    f"cd {shlex.quote(self._remote_job_dir(job_id))} && "
                    f"printf '%s' '{{\"state\":\"failed\",\"reason\":\"local timeout\"}}' > status.json"
                )
                raise CloudExecutionError(f"job {job_id} exceeded max_runtime_sec")
            time.sleep(poll_interval)

    def fetch(self, job_id: str, target_dir: str | Path) -> dict[str, Any]:
        remote = self._remote_job_dir(job_id)
        target = Path(target_dir).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        self._scp(f"{self.host}:{remote}/outputs", str(target), recursive=True)
        out_root = target / "outputs"
        files = []
        if out_root.is_dir():
            for path in sorted(out_root.rglob("*")):
                if path.is_file():
                    files.append({
                        "path": path.relative_to(target).as_posix(),
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    })
        logs = {}
        for name in ("stdout.log", "stderr.log", "exit_code.txt", "status.json"):
            result = self._ssh(f"cat {shlex.quote(remote)}/{name} 2>/dev/null || true")
            if result.stdout:
                dest = target / name
                dest.write_text(result.stdout, encoding="utf-8")
                logs[name] = sha256_file(dest)
        return {"job_id": job_id, "target": str(target), "files": files, "logs": logs, "fetched_at": _now()}
