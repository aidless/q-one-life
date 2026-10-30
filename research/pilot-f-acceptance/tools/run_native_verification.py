#!/usr/bin/env python3
"""Run the F-acceptance verifier twice against the overlay source."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay-root", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--generated-at")
    args = parser.parse_args()

    overlay_root = Path(args.overlay_root).expanduser().resolve()
    source = overlay_root / "source" / "main.tex"
    native_root = overlay_root / "evidence" / "native" / "wave2-F-acceptance"
    verifier = native_root / "verify_f_v2.py"
    output_dir = overlay_root / "reports" / "native-verification"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_before = sha256_file(source)
    results: list[subprocess.CompletedProcess[str]] = []
    artifacts: list[Path] = []
    for run_number in (1, 2):
        result = subprocess.run(
            [args.python, str(verifier), "--tex", str(source)],
            cwd=overlay_root,
            capture_output=True,
            text=True,
            check=False,
        )
        results.append(result)
        stdout_path = output_dir / f"verify-run{run_number}.log"
        stderr_path = output_dir / f"verify-run{run_number}.err"
        stdout_path.write_text(result.stdout, encoding="utf-8")
        stderr_path.write_text(result.stderr, encoding="utf-8")
        artifacts.extend([stdout_path, stderr_path])

    source_after = sha256_file(source)
    match = re.search(
        r"(\d+) checks passed, (\d+) failed",
        results[0].stdout,
    )
    passed_checks = int(match.group(1)) if match else None
    failed_checks = int(match.group(2)) if match else None
    deterministic = (
        results[0].stdout == results[1].stdout
        and results[0].stderr == results[1].stderr
    )
    state = (
        "passed"
        if source_before == source_after
        and deterministic
        and all(result.returncode == 0 for result in results)
        and passed_checks is not None
        and passed_checks > 0
        and failed_checks == 0
        else "failed"
    )
    input_paths = [
        verifier,
        native_root / "revision_stats.json",
        native_root / "dynamic_audit_frozen200.json",
        native_root / "flip_band.json",
        native_root / "unknown48_full_audit.json",
        native_root / "github_survey" / "raw" / "classification.json",
        native_root / "github_survey" / "raw" / "classification-readjudicated.json",
        overlay_root / "evidence" / "native" / "data" / "f02_gate_inventory.json",
    ]
    report = {
        "schema": "q-one-native-verification-gate-v1",
        "gate_id": "f-acceptance-native-verification",
        "generated_at": args.generated_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "state": state,
        "scope": "numbers",
        "source": {
            "path": str(source),
            "sha256": source_before,
            "sha256_after": source_after,
            "stable_during_run": source_before == source_after,
        },
        "command": [args.python, str(verifier), "--tex", str(source)],
        "runs": [
            {
                "exit_code": result.returncode,
                "stdout": str(artifacts[index * 2].relative_to(overlay_root)),
                "stderr": str(artifacts[index * 2 + 1].relative_to(overlay_root)),
            }
            for index, result in enumerate(results)
        ],
        "checks": {
            "passed": passed_checks,
            "failed": failed_checks,
            "deterministic_stdout": deterministic,
        },
        "inputs": [
            {
                "path": str(path.relative_to(overlay_root)),
                "sha256": sha256_file(path),
            }
            for path in input_paths
        ],
        "artifacts": [
            {
                "path": str(path.relative_to(overlay_root)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in artifacts
        ],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "notes": [
            "The copied verifier loaded all evidence from inside the overlay.",
            "A passing numeric verifier does not close the independent-review gate.",
        ],
    }
    report_path = overlay_root / "reports" / "native-verification-gate.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"state": state, **report["checks"]}, indent=2))
    return 0 if state == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
