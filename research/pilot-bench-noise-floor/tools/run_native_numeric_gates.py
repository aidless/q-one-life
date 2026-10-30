#!/usr/bin/env python3
"""Run the native Noise-Floor numeric gates twice and freeze a JSON receipt."""

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


def run_once(command: list[str], cwd: Path) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, cwd=cwd, capture_output=True, check=False)


def write_capture(
    output_dir: Path,
    stem: str,
    run_number: int,
    result: subprocess.CompletedProcess[bytes],
) -> dict[str, Path]:
    stdout_path = output_dir / f"{stem}-run{run_number}.log"
    stderr_path = output_dir / f"{stem}-run{run_number}.err"
    stdout_path.write_bytes(result.stdout)
    stderr_path.write_bytes(result.stderr)
    return {"stdout": stdout_path, "stderr": stderr_path}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", required=True)
    parser.add_argument("--overlay-root", required=True)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--generated-at")
    args = parser.parse_args()

    paper_root = Path(args.paper_root).expanduser().resolve()
    overlay_root = Path(args.overlay_root).expanduser().resolve()
    output_dir = overlay_root / "reports" / "native-gates"
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = paper_root / "paper" / "main.tex"
    ledger_path = paper_root / "evidence" / "paper-ledger.json"
    allowlist_path = paper_root / "evidence" / "reverse_coverage_allowlist.json"
    checks_script = paper_root / "check_manuscript_numbers.py"
    reverse_script = paper_root / "ledger_reverse_coverage.py"
    anchor_script = paper_root / "ledger_anchor_census.py"
    source_before = sha256_file(source_path)

    commands: dict[str, list[str]] = {
        "numbers": [args.python, str(checks_script)],
        "reverse": [
            args.python,
            str(reverse_script),
            "--paper",
            str(source_path),
            "--ledger",
            str(ledger_path),
            "--allowlist",
            str(allowlist_path),
        ],
        "anchor": [args.python, str(anchor_script)],
    }
    results: dict[str, list[subprocess.CompletedProcess[bytes]]] = {}
    captures: dict[str, list[dict[str, Path]]] = {}
    json_outputs: dict[str, list[Path]] = {"reverse": [], "anchor": []}

    for stem, base_command in commands.items():
        results[stem] = []
        captures[stem] = []
        for run_number in (1, 2):
            command = [*base_command]
            if stem in json_outputs:
                json_path = output_dir / f"{stem}-run{run_number}.json"
                command.extend(["--json-out", str(json_path)])
                json_outputs[stem].append(json_path)
            result = run_once(command, paper_root)
            results[stem].append(result)
            captures[stem].append(write_capture(output_dir, stem, run_number, result))

    source_after = sha256_file(source_path)
    numbers_match = re.search(
        r"(\d+)/(\d+)", results["numbers"][0].stdout.decode("utf-8", errors="replace")
    )
    numbers_passed = int(numbers_match.group(1)) if numbers_match else None
    numbers_total = int(numbers_match.group(2)) if numbers_match else None

    reverse_payloads = [
        json.loads(path.read_text(encoding="utf-8")) for path in json_outputs["reverse"]
    ]
    anchor_payloads = [
        json.loads(path.read_text(encoding="utf-8")) for path in json_outputs["anchor"]
    ]
    numbers_stdout = [result.stdout for result in results["numbers"]]
    reverse_deterministic = (
        sha256_file(json_outputs["reverse"][0])
        == sha256_file(json_outputs["reverse"][1])
    )
    anchor_deterministic = (
        sha256_file(json_outputs["anchor"][0])
        == sha256_file(json_outputs["anchor"][1])
    )
    exit_codes = {
        stem: [result.returncode for result in stem_results]
        for stem, stem_results in results.items()
    }
    checks = {
        "numbers": {
            "passed": all(code == 0 for code in exit_codes["numbers"])
            and numbers_stdout[0] == numbers_stdout[1]
            and numbers_passed == numbers_total
            and bool(numbers_total),
            "exit_codes": exit_codes["numbers"],
            "passed_checks": numbers_passed,
            "total_checks": numbers_total,
            "deterministic_stdout": numbers_stdout[0] == numbers_stdout[1],
        },
        "reverse": {
            "passed": all(code == 0 for code in exit_codes["reverse"])
            and reverse_deterministic
            and reverse_payloads[0].get("n_unbound") == 0,
            "exit_codes": exit_codes["reverse"],
            "n_tokens": reverse_payloads[0].get("n_tokens"),
            "n_bound": reverse_payloads[0].get("n_bound"),
            "n_excused": reverse_payloads[0].get("n_excused"),
            "n_unbound": reverse_payloads[0].get("n_unbound"),
            "deterministic_json": reverse_deterministic,
        },
        "anchor": {
            "passed": all(code == 0 for code in exit_codes["anchor"])
            and anchor_deterministic
            and anchor_payloads[0].get("verdict") == "GREEN"
            and not anchor_payloads[0].get("anchor_missing"),
            "exit_codes": exit_codes["anchor"],
            "verdict": anchor_payloads[0].get("verdict"),
            "entries": anchor_payloads[0].get("entries"),
            "anchor_missing": len(anchor_payloads[0].get("anchor_missing", [])),
            "ambiguous_membership": len(
                anchor_payloads[0].get("ambiguous_membership", [])
            ),
            "deterministic_json": anchor_deterministic,
        },
    }
    state = (
        "passed"
        if source_before == source_after and all(item["passed"] for item in checks.values())
        else "failed"
    )
    artifact_paths = [
        path
        for stem in captures
        for capture in captures[stem]
        for path in capture.values()
    ] + [path for paths in json_outputs.values() for path in paths]
    report = {
        "schema": "q-one-native-numeric-gate-v1",
        "gate_id": "noise-floor-native-numeric-gates",
        "generated_at": args.generated_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "state": state,
        "scope": "numbers",
        "source": {
            "path": str(source_path),
            "sha256": source_before,
            "sha256_after": source_after,
            "bytes": source_path.stat().st_size,
            "stable_during_run": source_before == source_after,
        },
        "inputs": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in (
                checks_script,
                reverse_script,
                anchor_script,
                ledger_path,
                allowlist_path,
            )
        ],
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
        "commands": commands,
        "checks": checks,
        "artifacts": [
            {
                "path": str(path.relative_to(overlay_root)),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
            for path in artifact_paths
        ],
        "notes": [
            "All three gates were executed twice against the bytes hashed above.",
            "Passing numeric gates do not resolve the separate native-manifest source mismatch.",
            "Named derivations in the native ledger are not executed by this receipt.",
        ],
    }
    report_path = overlay_root / "reports" / "native-numeric-gate.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"state": state, "checks": checks}, ensure_ascii=False, indent=2))
    return 0 if state == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
