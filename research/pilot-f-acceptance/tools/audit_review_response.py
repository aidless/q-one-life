#!/usr/bin/env python3
"""Audit the local response to the F-acceptance final review."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overlay-root", required=True)
    parser.add_argument("--generated-at")
    args = parser.parse_args()
    root = Path(args.overlay_root).expanduser().resolve()
    source_path = root / "source" / "main.tex"
    bib_path = root / "source" / "main.bib"
    review_path = root / "evidence" / "reviews" / "FINAL_REVIEW_2026-10-26.md"
    source = source_path.read_text(encoding="utf-8")
    bib = bib_path.read_text(encoding="utf-8")
    flat = normalized(source)
    revision_stats = json.loads(
        (
            root
            / "evidence"
            / "native"
            / "wave2-F-acceptance"
            / "revision_stats.json"
        ).read_text(encoding="utf-8")
    )
    inventory = json.loads(
        (root / "evidence" / "native" / "data" / "f02_gate_inventory.json").read_text(
            encoding="utf-8"
        )
    )
    unknown48 = json.loads(
        (
            root
            / "evidence"
            / "native"
            / "wave2-F-acceptance"
            / "unknown48_full_audit.json"
        ).read_text(encoding="utf-8")
    )
    disjointness = json.loads(
        (root / "reports" / "flip-disjointness.json").read_text(encoding="utf-8")
    )
    ledger = revision_stats["ledger_rejudgment"]
    notgate = sum(
        1
        for row in unknown48
        if row.get("verdict") == "non-gate-shape"
        or str(row.get("verdict", "")).startswith("not-a-gate")
    )
    paired = inventory["count"] - notgate
    table = source[source.find("\\begin{tabular}{lp{8.6cm}}") :]
    table = table[: table.find("\\end{tabular}")]
    midrule = table.find("\\midrule")
    scan_row = table.find("\\code{mcnemar\\_audit.py} \\code{--scan}")
    bibliography_at = source.find("\\bibliographystyle")
    appendix_at = source.find("\\appendix")
    checks = {
        "ledger_population": {
            "state": "passed"
            if ledger["entries"] == 14
            and ledger["agree"] == 14
            and ledger["promotions_recorded"] == 5
            and ledger["max_n"] == 12
            and "fourteen recorded gate decisions" in flat
            and "five promotions" in flat
            and "nine holds" in flat
            else "failed",
            "observed": {
                "entries": ledger["entries"],
                "agree": ledger["agree"],
                "promotions": ledger["promotions_recorded"],
                "max_n": ledger["max_n"],
            },
        },
        "paired_binomial_scope": {
            "state": "passed"
            if paired == 82
            and "118 name-matched function entries, 82 of them paired-binomial tests"
            in flat
            and "The remaining 36 are not p-value gates at all" in flat
            else "failed",
            "observed": {
                "inventory_count": inventory["count"],
                "not_gate": notgate,
                "paired_binomial": paired,
            },
        },
        "rerun_delta": {
            "state": "passed"
            if "re-run delta of $+3$ caused by our own artifact archive" in flat
            else "failed",
        },
        "continuity_disjoint": {
            "state": "passed"
            if "231 promotion-side flips with 9 of the opposite sign, on a disjoint set"
            in flat
            and disjointness["state"] == "passed"
            and disjointness["observed_counts"]["intersection"] == 0
            else "failed",
            "observed": disjointness["observed_counts"],
        },
        "archive_language": {
            "state": "passed"
            if "no external archive is cited, so no archive is required"
            in flat
            else "failed",
        },
        "citation_metadata": {
            "state": "passed"
            if all(
                marker in bib
                for marker in (
                    "title     = {An Empirical Analysis of Flaky Tests}",
                    "year      = {2014}",
                    "doi       = {10.1145/2635868.2635920}",
                )
            )
            else "failed",
        },
        "exit_table_order": {
            "state": "passed"
            if midrule >= 0 and scan_row > midrule
            else "failed",
            "observed": {"midrule": midrule, "scan_row": scan_row},
        },
        "bibliography_before_appendix": {
            "state": "passed"
            if 0 <= bibliography_at < appendix_at
            else "failed",
            "observed": {"bibliography_at": bibliography_at, "appendix_at": appendix_at},
        },
        "independent_re_review_current_source": {
            "state": "blocked",
            "note": "The retained 2026-10-26 final review predates the current source; no independent re-review is bound to this hash.",
        },
    }
    failed = [name for name, item in checks.items() if item["state"] == "failed"]
    candidate = [name for name, item in checks.items() if item["state"] == "candidate"]
    blocked = [name for name, item in checks.items() if item["state"] == "blocked"]
    report = {
        "schema": "q-one-review-response-audit-v1",
        "generated_at": args.generated_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {
            "path": str(source_path.relative_to(root)),
            "sha256": sha256_file(source_path),
        },
        "review_receipt": {
            "path": str(review_path.relative_to(root)),
            "sha256": sha256_file(review_path),
        },
        "state": "open" if failed or candidate or blocked else "locally_closed",
        "checks": checks,
        "failed": failed,
        "candidate": candidate,
        "blocked": blocked,
        "disposition": (
            "Local fixes are partially verified. The current source is an internal revision "
            "candidate, not an independently closed submission."
        ),
    }
    output = root / "reports" / "review-response-audit.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "state": report["state"],
                "failed": failed,
                "candidate": candidate,
                "blocked": blocked,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
