#!/usr/bin/env python3
"""Record canonical and superseded Paper 2 source identities without rewriting them."""

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


def version_record(path: Path, canonical: Path) -> dict[str, object]:
    data = path.read_bytes()
    canonical_data = canonical.read_bytes()
    current_lines = data.decode("utf-8").splitlines()
    canonical_lines = canonical_data.decode("utf-8").splitlines()
    change_count = 0
    for tag, old_start, old_end, new_start, new_end in difflib.SequenceMatcher(
        None, current_lines, canonical_lines
    ).get_opcodes():
        if tag != "equal":
            change_count += max(old_end - old_start, new_end - new_start)
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "bytes": len(data),
        "lines": len(current_lines),
        "byte_identical_to_canonical": data == canonical_data,
        "changed_lines_vs_canonical": change_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--generated-at",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    canonical = root / "evidence" / "upstream" / "paper" / "main.tex"
    variants = {
        "arxiv": root / "evidence" / "variants" / "arxiv" / "main.tex",
        "source_old": root / "evidence" / "upstream" / "source" / "main.tex",
        "ingest_drift": root
        / "evidence"
        / "variants"
        / "ingest-drift"
        / "main.tex",
        "legacy": root / "evidence" / "variants" / "legacy" / "main.tex",
    }
    payload = {
        "schema": "q-one-paper2-variant-reconciliation-v1",
        "generated_at": args.generated_at,
        "family_id": "qf-a-conditional-coupling-diversity-precisi-7336590fb7",
        "portfolio_project_id": "qp-tmlr-paper2-consolidated-a737471ea703",
        "canonical": {
            "role": "canonical",
            "origin": (
                "<WORKSPACE_ROOT>/Projects/agi-paper-pipeline/runs/"
                "tmlr-paper2-consolidated/paper/main.tex"
            ),
            **version_record(canonical, canonical),
        },
        "variants": [
            {
                "role": role,
                **version_record(path, canonical),
            }
            for role, path in variants.items()
        ],
        "decision": {
            "canonical_source": canonical.name,
            "basis": [
                "The paper/main.tex file is the portfolio project's primary source.",
                "arxiv/main.tex is byte-identical to the canonical source.",
                "source/main.tex and the legacy/drift copies are older or noncanonical.",
            ],
            "superseded_copies_remain_immutable": True,
            "final_disposition": "unreviewed",
        },
        "notes": [
            "This reconciliation records identity; it does not claim scientific validity.",
            "Variant line deltas are descriptive and do not imply that all changes are improvements.",
        ],
    }
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "canonical_sha256": payload["canonical"]["sha256"],
                "variants": len(payload["variants"]),
                "output": str(output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
