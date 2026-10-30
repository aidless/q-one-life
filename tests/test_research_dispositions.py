from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "research_dispositions", ROOT / "scripts" / "research_dispositions.py"
)
assert SPEC is not None and SPEC.loader is not None
research_dispositions = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research_dispositions)


def _record(family_id: str, title: str) -> dict:
    return {
        "family_id": family_id,
        "project_id": f"project-{family_id}",
        "title": title,
        "priority_band": "P1",
        "production_priority": 100,
        "primary_source": f"/tmp/{family_id}/main.tex",
        "suggested_disposition": "repair",
        "suggestion_reason": "Generic triage suggestion.",
    }


def _packet(family_id: str, *, status: str | None = None, variants: int = 0) -> dict:
    return {
        "family_id": family_id,
        "source_state": {"exists": True, "sha256": "a" * 64, "matches_catalog": True},
        "signals": {
            "claim_ledger": True,
            "bibliography": True,
            "evidence_directory": True,
            "variants_to_reconcile": variants,
        },
        "overlay": (
            {
                "path": f"/tmp/{family_id}/project.json",
                "status": status,
                "package_state": "compiled" if status == "review_pending" else "not-started",
            }
            if status
            else None
        ),
        "machine_recommendation": {"reason": "Machine recommendation."},
    }


def test_agent_dispositions_do_not_change_final_human_disposition():
    triage = {
        "projects": [
            _record("archive-family", "Archived family"),
            _record("blocked-family", "Blocked family"),
        ]
    }
    packets = {
        "archive-family": _packet("archive-family", status="archived"),
        "blocked-family": _packet("blocked-family", status="blocked"),
    }

    payload = research_dispositions.build_agent_dispositions(
        triage, packets, generated_at="2026-10-28T00:00:00Z"
    )

    assert payload["summary"]["families"] == 2
    assert payload["summary"]["agent_proposed_dispositions"] == {
        "archive": 1,
        "blocked": 1,
    }
    assert payload["summary"]["final_human_dispositions"] == {"unreviewed": 2}
    assert all(
        entry["final_human_disposition"] == "unreviewed"
        and entry["publication_ready"] is False
        and entry["upload_authorized"] is False
        for entry in payload["entries"]
    )


def test_unmatched_variant_family_requires_merge():
    triage = {"projects": [_record("merge-family", "Merge family")]}
    triage["projects"][0]["suggested_disposition"] = "merge"
    packets = {"merge-family": _packet("merge-family", variants=3)}
    packets["merge-family"]["machine_recommendation"] = {
        "reason": "Multiple source versions require reconciliation."
    }

    payload = research_dispositions.build_agent_dispositions(triage, packets)

    entry = payload["entries"][0]
    assert entry["agent_proposed_disposition"] == "merge"
    assert entry["agent_next_action"] == "select_canonical_source_and_reconcile_variants"
    assert entry["final_human_disposition"] == "unreviewed"
