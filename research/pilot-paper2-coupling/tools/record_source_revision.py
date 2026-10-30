#!/usr/bin/env python3
"""Record the immutable upstream source and the reviewed overlay revision."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
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
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    upstream = root / "evidence" / "upstream" / "paper" / "main.tex"
    overlay = root / "source" / "main.tex"
    upstream_text = upstream.read_text(encoding="utf-8")
    overlay_text = overlay.read_text(encoding="utf-8")
    upstream_lines = upstream_text.splitlines(keepends=True)
    overlay_lines = overlay_text.splitlines(keepends=True)
    diff = "".join(
        difflib.unified_diff(
            upstream_lines,
            overlay_lines,
            fromfile="evidence/upstream/paper/main.tex",
            tofile="source/main.tex",
            n=3,
        )
    )
    changed = sum(
        1
        for line in diff.splitlines()
        if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))
    )

    source_record = {
        "schema": "q-one-source-record-v1",
        "generated_at": args.generated_at,
        "family_id": "qf-a-conditional-coupling-diversity-precisi-7336590fb7",
        "portfolio_project_id": "qp-tmlr-paper2-consolidated-a737471ea703",
        "canonical_source": {
            "path": str(upstream),
            "sha256": sha256_file(upstream),
            "bytes": upstream.stat().st_size,
            "authority": "paper/main.tex from the portfolio record",
        },
        "overlay_source": {
            "path": str(overlay),
            "sha256": sha256_file(overlay),
            "bytes": overlay.stat().st_size,
        },
        "published_source_sha256": None,
        "matches_published_source": None,
        "variant_reconciliation": "evidence/variant-reconciliation.json",
        "notes": [
            "The upstream source is retained byte-for-byte.",
            "The overlay source is a packaging and scope revision, not a claim upgrade.",
            "Published source identity is unknown until an external publication receipt exists.",
        ],
    }
    source_path = root / "evidence" / "source_record.json"
    source_path.write_text(
        json.dumps(source_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    diff_path = root / "reports" / "source-revision.diff"
    diff_path.parent.mkdir(parents=True, exist_ok=True)
    diff_path.write_text(diff, encoding="utf-8")
    revision = {
        "schema": "q-one-paper2-source-revision-v1",
        "generated_at": args.generated_at,
        "upstream": {
            "path": "evidence/upstream/paper/main.tex",
            "sha256": sha256_file(upstream),
        },
        "overlay": {
            "path": "source/main.tex",
            "sha256": sha256_file(overlay),
            "changed_diff_lines": changed,
        },
        "diff_receipt": {
            "path": "reports/source-revision.diff",
            "sha256": sha256_file(diff_path),
        },
        "change_scope": [
            "Removed stale TMLR anonymity comments and a superseded title comment.",
            "Replaced unverified release, raw-log and public-repository claims with qualified evidence metadata.",
            "Removed a duplicate Reproducibility Statement section.",
            "Replaced off-topic calibration-fatigue ethics text with text specific to evaluator coupling.",
            "Replaced internal manuscript codes and impossibility-triangle wording with scoped terminology.",
        ],
        "claim_impact": "none",
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "This revision does not close proof, held-out validation, independent review, metadata or license gates.",
            "The upstream bytes remain available for exact reversion and comparison.",
        ],
    }
    revision_path = root / "reports" / "source-revision.json"
    revision_path.write_text(
        json.dumps(revision, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "upstream_sha256": revision["upstream"]["sha256"],
                "overlay_sha256": revision["overlay"]["sha256"],
                "changed_diff_lines": changed,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
