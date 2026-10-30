#!/usr/bin/env python3
"""Audit the evidence boundaries behind the native P2-C1..P2-C14 ledger."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

NATIVE_ID_RE = re.compile(r"^\|\s*(P2-C\d+)\s*\|", re.MULTILINE)
CITE_RE = re.compile(r"\\cite\{([^}]+)\}")
BIBITEM_RE = re.compile(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def audit(root: Path, generated_at: str) -> dict[str, Any]:
    upstream = root / "evidence" / "upstream" / "source"
    manuscript = root / "source" / "main.tex"
    upstream_manuscript = root / "evidence" / "upstream" / "paper" / "main.tex"
    native_ledger = upstream / "CLAIM_LEDGER.md"
    ledger_text = native_ledger.read_text(encoding="utf-8")
    native_ids = NATIVE_ID_RE.findall(ledger_text)

    theory_files = sorted((upstream / "theory").glob("*.tex"))
    experiment_files = sorted((upstream / "experiments").glob("*.json"))
    scope_files = sorted((upstream / "evidence").glob("scope_P2C*.md"))

    source_text = manuscript.read_text(encoding="utf-8")
    cite_keys: set[str] = set()
    for match in CITE_RE.finditer(source_text):
        cite_keys.update(item.strip() for item in match.group(1).split(","))
    bib_keys = set(BIBITEM_RE.findall(source_text))

    june = load_json(
        upstream / "evidence" / "analyses" / "gpt4o_drift_june_snapshot.json"
    )
    replication = load_json(
        upstream
        / "evidence"
        / "analyses"
        / "mm_epc_gpt4o_replication.json"
    )
    decision_case = load_json(
        upstream / "evidence" / "p2_bound_decision_case_20260808.json"
    )
    table_numbers = load_json(upstream / "evidence" / "table_numbers.json")
    review_summary = load_json(upstream / "review_real" / "summary.json")
    meta_review = (
        upstream / "reviews" / "main.multi" / "meta-review.md"
    ).read_text(encoding="utf-8")

    heldout_candidates = [
        path
        for path in upstream.rglob("*")
        if path.is_file()
        and re.search(r"held[\s_-]?out", path.name, re.IGNORECASE)
    ]
    proof_audit_candidates = [
        path
        for path in upstream.rglob("*")
        if path.is_file()
        and re.search(r"proof.*audit|audit.*proof", path.name, re.IGNORECASE)
    ]

    scope_mentions_heldout = sum(
        len(re.findall(r"held[\s_-]?out", path.read_text(encoding="utf-8"), re.IGNORECASE))
        for path in scope_files
    )
    scope_p2c11 = (upstream / "evidence" / "scope_P2C11.md").read_text(
        encoding="utf-8"
    )
    p_value_in_scope = re.search(r"p\s*=\s*0\.12", scope_p2c11) is not None
    p_bootstrap = replication.get("p_bootstrap")

    template_checks = {
        "placeholder_repository": len(
            re.findall(r"available at acceptance", source_text, re.IGNORECASE)
        ),
        "internal_code_paper4": source_text.count("PAPER4"),
        "duplicate_reproducibility_heading": source_text.count(
            "\\section*{Reproducibility Statement}"
        ),
        "duplicate_reproducibility_short_heading": source_text.count(
            "\\section*{Reproducibility}"
        ),
        "anonymous_release_claims": len(
            re.findall(
                r"anonymous repository|released under the MIT License",
                source_text,
                re.IGNORECASE,
            )
        ),
    }

    checks = {
        "native_claim_count_is_14": len(native_ids) == 14,
        "theory_files_present": len(theory_files) > 0,
        "experiment_outputs_present": len(experiment_files) > 0,
        "scope_files_present": len(scope_files) >= 10,
        "all_citations_have_local_bibitems": not (cite_keys - bib_keys),
        "june_snapshot_n_is_8": june.get("n_seeds") == 8,
        "june_snapshot_zero_coupling": june.get("summary", {}).get(
            "zero_coupling_rate"
        )
        == 1.0,
        "native_p012_matches_frozen_json": (
            not p_value_in_scope
        )
        or p_bootstrap == 0.12,
        "heldout_data_file_present": bool(heldout_candidates),
        "proof_audit_receipt_present": bool(proof_audit_candidates),
        "meta_review_reports_major_revisions": "Major Revisions"
        in meta_review,
        "template_hygiene_clear": (
            template_checks["placeholder_repository"] == 0
            and template_checks["internal_code_paper4"] == 0
            and template_checks["duplicate_reproducibility_heading"] == 1
            and template_checks["duplicate_reproducibility_short_heading"] == 0
            and template_checks["anonymous_release_claims"] == 0
        ),
    }

    carrier_path = root / "evidence" / "carrier-audit.json"
    carrier = load_json(carrier_path) if carrier_path.is_file() else None
    carrier_passed = carrier is not None and carrier.get("summary", {}).get(
        "failed"
    ) == 0
    source_hashes = {
        "manuscript_sha256": sha256_file(manuscript),
        "upstream_manuscript_sha256": sha256_file(upstream_manuscript),
        "native_ledger_sha256": sha256_file(native_ledger),
    }

    return {
        "schema": "q-one-paper2-native-claim-audit-v1",
        "generated_at": generated_at,
        "source": source_hashes,
        "counts": {
            "native_claims": len(native_ids),
            "theory_tex_files": len(theory_files),
            "experiment_json_files": len(experiment_files),
            "scope_files": len(scope_files),
            "cite_keys": len(cite_keys),
            "bibitems": len(bib_keys),
            "scope_heldout_mentions": scope_mentions_heldout,
            "heldout_data_files": len(heldout_candidates),
            "proof_audit_receipts": len(proof_audit_candidates),
            "review_critical": review_summary.get("r6", {}).get("critical"),
            "review_major": review_summary.get("r6", {}).get("major"),
            "carrier_receipts_passed": (
                carrier.get("summary", {}).get("passed") if carrier else None
            ),
            "carrier_receipts_failed": (
                carrier.get("summary", {}).get("failed") if carrier else None
            ),
            "bound_decision_rows": len(decision_case.get("rows", [])),
            "table_numbers": len(table_numbers.get("values", [])),
        },
        "observed": {
            "native_claim_ids": native_ids,
            "june_snapshot_n": june.get("n_seeds"),
            "june_zero_coupling_rate": june.get("summary", {}).get(
                "zero_coupling_rate"
            ),
            "frozen_p_bootstrap": p_bootstrap,
            "scope_p012_present": p_value_in_scope,
            "meta_review_decision": (
                "Major Revisions" if "Major Revisions" in meta_review else "unknown"
            ),
            "heldout_files": [str(path.relative_to(root)) for path in heldout_candidates],
            "proof_audit_files": [
                str(path.relative_to(root)) for path in proof_audit_candidates
            ],
        },
        "checks": checks,
        "template_checks": template_checks,
        "gate_states": {
            "carrier_recomputation": "passed" if carrier_passed else "blocked",
            "citation_resolution": (
                "passed" if checks["all_citations_have_local_bibitems"] else "failed"
            ),
            "source_identity": "passed",
            "held_out_validation": (
                "blocked" if not checks["heldout_data_file_present"] else "candidate"
            ),
            "independent_proof_audit": (
                "blocked" if not checks["proof_audit_receipt_present"] else "candidate"
            ),
            "scientific_review": "blocked",
            "metadata_and_license": "blocked",
            "external_submission": "locked",
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "A hedged claim is not automatically a verified claim.",
            "A future-work statement is not held-out evidence.",
            "The paper remains review_pending until proof, held-out validation, independent review, metadata and license gates close.",
        ],
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
    payload = audit(root, args.generated_at)
    output = Path(args.output)
    if not output.is_absolute():
        output = root / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"checks": payload["checks"], "counts": payload["counts"]}, indent=2))
    required = [
        payload["checks"]["native_claim_count_is_14"],
        payload["checks"]["all_citations_have_local_bibitems"],
        payload["checks"]["template_hygiene_clear"],
        payload["gate_states"]["carrier_recomputation"] == "passed",
    ]
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
