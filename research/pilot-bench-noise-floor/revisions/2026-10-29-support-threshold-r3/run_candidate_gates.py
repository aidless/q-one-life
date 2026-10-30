#!/usr/bin/env python3
"""Run R3 numeric, anchor and verdict gates without modifying the native paper."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-root", required=True)
    parser.add_argument(
        "--revision-root",
        default=str(Path(__file__).resolve().parent),
    )
    args = parser.parse_args()

    paper_root = Path(args.paper_root).expanduser().resolve()
    revision_root = Path(args.revision_root).expanduser().resolve()
    repo_root = paper_root.parent.parent
    reports = revision_root / "reports"
    paper_path = revision_root / "source" / "main.tex"
    ledger_path = revision_root / "evidence" / "paper-ledger-overlay.json"
    registry_path = revision_root / "evidence" / "verdict-claims-overlay.json"
    allowlist_path = paper_root / "evidence" / "reverse_coverage_allowlist.json"

    reverse_path = paper_root / "ledger_reverse_coverage.py"
    anchor_path = paper_root / "ledger_anchor_census.py"
    verdict_path = paper_root / "check_verdict_words.py"
    reverse_report = reports / "ledger-reverse-coverage.json"
    reverse_log = reports / "ledger-reverse-coverage.log"

    reverse = subprocess.run(
        [
            sys.executable,
            str(reverse_path),
            "--paper",
            str(paper_path),
            "--ledger",
            str(ledger_path),
            "--allowlist",
            str(allowlist_path),
            "--json-out",
            str(reverse_report),
        ],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    reverse_log.write_bytes(reverse.stdout + reverse.stderr)
    reverse_payload = json.loads(reverse_report.read_text(encoding="utf-8"))

    anchor = load_module("qone_r3_anchor", anchor_path)
    tex = paper_path.read_text(encoding="utf-8")
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    entries = ledger["entries"]
    anchor_missing, anchor_soft = anchor.census_a(anchor.norm(tex), entries)
    refusal_sentences = anchor.census_b(tex.splitlines())
    ambiguous, checked = anchor.census_c(entries, str(repo_root))
    anchor_payload = {
        "schema": "ledger-class-census/1",
        "entries": len(entries),
        "anchor_missing": anchor_missing,
        "refusal_sentences": refusal_sentences,
        "ambiguous_membership": ambiguous,
        "json_entries_checked": checked,
        "verdict": "RED" if anchor_missing else "GREEN",
    }
    write_json(reports / "ledger-anchor-census.json", anchor_payload)

    verdict = load_module("qone_r3_verdict", verdict_path)
    gate = verdict.Gate(
        reg_path=str(registry_path),
        paper_path=str(paper_path),
        root=str(paper_root),
    )
    gate.run()
    failures = [row for row in gate.rows if row["state"] == "FAIL"]
    not_assessed = [row for row in gate.rows if row["state"] == "NOT_ASSESSED"]
    verdict_payload = {
        "schema": "verdict-word-gate/1",
        "rows": gate.rows,
        "withdrawn_without_carrier": gate.blind,
        "verdict": (
            "PASS"
            if not failures and not not_assessed
            else ("FAIL" if failures else "NOT_ASSESSED")
        ),
    }
    write_json(reports / "verdict-word-gate.json", verdict_payload)

    passed = (
        reverse.returncode == 0
        and reverse_payload.get("n_unbound") == 0
        and anchor_payload["verdict"] == "GREEN"
        and verdict_payload["verdict"] == "PASS"
    )
    summary = {
        "schema": "q-one-r3-candidate-gates-v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "passed" if passed else "failed",
        "inputs": [
            {
                "path": str(path),
                "sha256": sha256_file(path),
            }
            for path in (
                paper_path,
                ledger_path,
                registry_path,
                allowlist_path,
                reverse_path,
                anchor_path,
                verdict_path,
            )
        ],
        "reverse_coverage": {
            "exit_code": reverse.returncode,
            "n_tokens": reverse_payload.get("n_tokens"),
            "n_bound": reverse_payload.get("n_bound"),
            "n_excused": reverse_payload.get("n_excused"),
            "n_unbound": reverse_payload.get("n_unbound"),
            "appendix": reverse_payload.get("appendix"),
        },
        "anchor_census": {
            "verdict": anchor_payload["verdict"],
            "anchor_missing": len(anchor_missing),
            "anchor_soft_mismatch": len(anchor_soft),
            "ambiguous_membership": len(ambiguous),
            "json_entries_checked": checked,
        },
        "verdict_word_gate": {
            "verdict": verdict_payload["verdict"],
            "checks": len(gate.rows),
            "failures": len(failures),
            "not_assessed": len(not_assessed),
        },
        "non_claims": [
            "These gates check binding and wording; they do not establish scientific readiness.",
            "The native paper tree and native ledger are read-only inputs.",
            "Passing gates do not resolve C02 or C03.",
        ],
    }
    write_json(reports / "candidate-gates-summary.json", summary)

    print(
        json.dumps(
            {
                "status": summary["status"],
                "reverse_unbound": reverse_payload.get("n_unbound"),
                "anchor": anchor_payload["verdict"],
                "verdict_words": verdict_payload["verdict"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
