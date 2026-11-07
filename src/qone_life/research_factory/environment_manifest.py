"""可执行科研环境清单：把一篇论文的基线变成可校验的环境。

清单本身不运行实验；它固定数据集、基线指标、容差、运行命令与资源上限。
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ENVIRONMENT_SCHEMA = "q-one-environment-v1"
MAX_RUNTIME_SEC = 4 * 60 * 60
MAX_DISK_GB = 50


class EnvironmentError(RuntimeError):
    """环境清单无法安全校验时抛出。"""


def _now() -> str:
    return datetime.now(timezone.utc).replace(
        microsecond=0
    ).isoformat().replace("+00:00", "Z")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _portable(path: Path) -> str:
    try:
        relative = path.resolve().relative_to(Path.home())
    except ValueError:
        return str(path)
    return f"<HOME>/{relative.as_posix()}"


def lock_environment(manifest: dict[str, Any]) -> str:
    """返回清单的规范化哈希。"""
    canonical = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return _sha256(canonical.encode("utf-8"))


def validate_environment(
    manifest: dict[str, Any],
    root: str | Path,
) -> dict[str, Any]:
    """校验清单字段、数据集哈希与资源上限。"""
    if not isinstance(manifest, dict):
        raise EnvironmentError("manifest must be an object")
    root_path = Path(root).expanduser().resolve()
    checks: list[dict[str, Any]] = []

    def check(check_id: str, passed: bool, detail: str, evidence: Any = None) -> None:
        checks.append({
            "check_id": check_id,
            "passed": passed,
            "detail": detail,
            "evidence": evidence,
        })

    check(
        "schema",
        manifest.get("schema") == ENVIRONMENT_SCHEMA,
        f"schema={manifest.get('schema')!r}",
    )
    check(
        "environment_id",
        bool(str(manifest.get("environment_id") or "").strip()),
        "environment_id is required",
    )
    paper = manifest.get("paper") or {}
    check(
        "paper_identity",
        bool(str(paper.get("title") or "").strip())
        and bool(str(paper.get("url") or paper.get("commit") or "").strip()),
        "paper title and url/commit are required",
    )
    check(
        "run_command",
        bool(str(manifest.get("run_command") or "").strip()),
        "run_command is required",
    )

    metrics = manifest.get("baseline_metrics") or {}
    check(
        "baseline_metrics",
        isinstance(metrics, dict) and bool(metrics),
        "baseline_metrics must be a non-empty object",
    )
    check(
        "tolerance",
        isinstance(manifest.get("tolerance"), (int, float))
        and float(manifest["tolerance"]) >= 0,
        "tolerance must be a non-negative number",
    )

    datasets = manifest.get("datasets") or []
    dataset_ok = True
    dataset_evidence = []
    for item in datasets:
        relative = str(item.get("path") or "")
        expected = str(item.get("sha256") or "")
        path = root_path / relative
        if not relative or not path.is_file() or not expected:
            dataset_ok = False
            dataset_evidence.append({"path": relative, "state": "missing"})
            continue
        actual = _sha256(path.read_bytes())
        match = actual == expected
        dataset_ok = dataset_ok and match
        dataset_evidence.append({
            "path": relative,
            "state": "match" if match else "mismatch",
            "sha256": actual,
        })
    checks.append({
        "check_id": "datasets",
        "passed": bool(datasets) and dataset_ok,
        "detail": f"{len(datasets)} datasets declared",
        "evidence": dataset_evidence,
    })

    runtime = manifest.get("max_runtime_sec")
    disk = manifest.get("max_disk_gb")
    check(
        "runtime_limit",
        isinstance(runtime, int) and 0 < runtime <= MAX_RUNTIME_SEC,
        f"max_runtime_sec={runtime!r}",
    )
    check(
        "disk_limit",
        isinstance(disk, (int, float)) and 0 < float(disk) <= MAX_DISK_GB,
        f"max_disk_gb={disk!r}",
    )
    outputs = manifest.get("expected_outputs") or []
    check(
        "expected_outputs",
        isinstance(outputs, list) and bool(outputs),
        "expected_outputs must be a non-empty list",
    )

    failed = [item["check_id"] for item in checks if not item["passed"]]
    return {
        "schema": "q-one-environment-validation-v1",
        "generated_at": _now(),
        "environment_id": manifest.get("environment_id"),
        "root": _portable(root_path),
        "environment_sha256": lock_environment(manifest),
        "checks": checks,
        "failed": failed,
        "status": "passed" if not failed else "failed",
    }


def write_environment_validation(
    report: dict[str, Any], output: str | Path
) -> dict[str, Any]:
    """写入环境校验回执。"""
    path = Path(output).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {"path": str(path), "sha256": _sha256(path.read_bytes())}
