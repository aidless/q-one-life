#!/usr/bin/env python3
"""A4: test the threshold and interface semantics of the native ruler.

Independent review finding A4 names three concrete interface questions:

* whether the declared margin is a CLI parameter or a hard-coded constant;
* how the implementation treats a point margin exactly equal to that constant;
* whether the printed margin confidence interval participates in the verdict.

The runner constructs deterministic CSV fixtures, invokes the pinned, unmodified
native ``audit.py`` as a subprocess, and records both the point-estimate branch
and any fail-closed refusal.  It does not import or modify the native decision
chain, so the verdict and its printed explanation come from the shipped tool.

No timestamps or temporary paths are written to the accepted output, allowing
two runs to be compared byte for byte.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

PINNED_AUDIT_SHA256 = (
    "2fbb95fc6601c855e8df09df4bbd712883411d901209d5ee497cd73d7e23876b"
)
AUDIT_RELATIVE = Path("tools") / "bench-noise-floor" / "audit.py"
N_BOOT = 2000
DELTA = 2.0
POINT_TOL = 1e-12
HEADER = [
    "item_id",
    "slice",
    "case_id",
    "role",
    "actor",
    "answer",
    "answer_prob",
]


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _row(
    item: str,
    case: str,
    role: str,
    actor: str,
    answer: str,
) -> list[str]:
    return [item, "all", case, role, actor, answer, "0.90"]


def balanced_tri_fixture(
    *,
    n_items: int,
    n_disagree: int,
    leader_correct: int,
    leader_name: str = "sys-top",
) -> tuple[list[list[str]], dict[str, Any]]:
    """Build four generators with exact LOO floor and a controlled leader.

    The first ``n_items - n_disagree`` items have unanimous gold ``A``.  On the
    remaining items, three generators vote ``B`` and a rotating generator votes
    ``A``.  Each generator is therefore the lone dissenter on exactly a quarter
    of the disagreement items, giving every generator the same LOO accuracy:

        floor = (n_items - n_disagree / 4) / n_items.

    The leader follows the full plurality gold on exactly ``leader_correct``
    items and the alternative label elsewhere.  A second system supplies a
    non-vacuous lower row; the first row remains the leader by construction.
    """
    if n_items <= 0 or n_disagree < 0 or n_disagree > n_items:
        raise ValueError("invalid fixture dimensions")
    if n_disagree % 4:
        raise ValueError("n_disagree must be divisible by four")
    if not 0 <= leader_correct <= n_items:
        raise ValueError("leader_correct outside item domain")

    n_agree = n_items - n_disagree
    rows: list[list[str]] = []
    for index in range(n_items):
        item = f"i{index:05d}"
        case = f"case-{index:05d}"
        if index < n_agree:
            votes = ["A", "A", "A", "A"]
            gold = "A"
        else:
            votes = ["B", "B", "B", "B"]
            votes[(index - n_agree) % 4] = "A"
            gold = "B"
        for generator_index, answer in enumerate(votes, start=1):
            rows.append(
                _row(
                    item,
                    case,
                    "judge",
                    f"generator-{generator_index}",
                    answer,
                )
            )

        leader_answer = gold if index < leader_correct else ("B" if gold == "A" else "A")
        rows.append(_row(item, case, "system", leader_name, leader_answer))
        rows.append(_row(item, case, "system", "sys-low", "C"))

    floor_correct = n_items - n_disagree // 4
    raw_margin = 100.0 * (leader_correct / n_items - floor_correct / n_items)
    spec = {
        "kind": "balanced_four_generator",
        "n_items": n_items,
        "n_disagree": n_disagree,
        "leader_correct": leader_correct,
        "leader_name": leader_name,
        "expected_floor_points": 100.0 * floor_correct / n_items,
        "expected_leader_points": 100.0 * leader_correct / n_items,
        "expected_point_margin": raw_margin,
    }
    return rows, spec


def ci_crossing_fixture() -> tuple[list[list[str]], dict[str, Any]]:
    """Point margin > delta, but a case bootstrap interval lower bound < 0.

    One large case contributes 500 items with a balanced LOO floor of 75% and a
    leader at 100%.  Fifty singleton cases contribute perfect generator
    agreement but a leader score of 0%.  The aggregate point margin is positive
    (+13.6364 points).  A case bootstrap that omits the large case draws only
    from the singleton cases and returns a negative margin, so the paired
    interval crosses zero.
    """
    rows: list[list[str]] = []
    positive_items = 500
    negative_cases = 50

    for index in range(positive_items):
        item = f"a{index:05d}"
        votes = ["A", "A", "A", "A"]
        votes[index % 4] = "B"
        for generator_index, answer in enumerate(votes, start=1):
            rows.append(
                _row(
                    item,
                    "case-positive",
                    "judge",
                    f"generator-{generator_index}",
                    answer,
                )
            )
        rows.append(_row(item, "case-positive", "system", "sys-top", "A"))
        rows.append(_row(item, "case-positive", "system", "sys-low", "B"))

    for index in range(negative_cases):
        item = f"b{index:05d}"
        case = f"case-negative-{index:05d}"
        for generator_index in range(1, 5):
            rows.append(
                _row(
                    item,
                    case,
                    "judge",
                    f"generator-{generator_index}",
                    "A",
                )
            )
        rows.append(_row(item, case, "system", "sys-top", "B"))
        rows.append(_row(item, case, "system", "sys-low", "A"))

    n_items = positive_items + negative_cases
    floor_correct = (positive_items * 3) + negative_cases
    leader_correct = positive_items
    spec = {
        "kind": "ci_crossing_case_cluster",
        "positive_case_items": positive_items,
        "negative_singleton_cases": negative_cases,
        "n_items": n_items,
        "expected_floor_points": 100.0 * floor_correct / n_items,
        "expected_leader_points": 100.0 * leader_correct / n_items,
        "expected_point_margin": 100.0
        * (leader_correct - floor_correct)
        / n_items,
        "expected_ci_lower_below_zero": -100.0,
    }
    return rows, spec


def domain_mismatch_fixture() -> tuple[list[list[str]], dict[str, Any]]:
    rows: list[list[str]] = []
    for index in range(10):
        item = f"d{index:02d}"
        case = f"d-case-{index:02d}"
        for generator_index in range(1, 5):
            rows.append(
                _row(
                    item,
                    case,
                    "judge",
                    f"generator-{generator_index}",
                    "A",
                )
            )
        rows.append(_row(item, case, "system", "sys-top", "A"))
        if index < 5:
            rows.append(_row(item, case, "system", "sys-sparse", "A"))
    return rows, {
        "kind": "domain_membership_mismatch",
        "n_items": 10,
        "full_system_items": 10,
        "sparse_system_items": 5,
        "expected_verdict": "UNDECIDABLE_DOMAIN_MISMATCH",
    }


def floor_degenerate_fixture() -> tuple[list[list[str]], dict[str, Any]]:
    rows: list[list[str]] = []
    for index in range(10):
        item = f"m{index:02d}"
        case = f"m-case-{index:02d}"
        for generator_index in range(1, 3):
            rows.append(
                _row(
                    item,
                    case,
                    "judge",
                    f"generator-{generator_index}",
                    "A",
                )
            )
        rows.append(_row(item, case, "system", "sys-top", "A"))
        rows.append(_row(item, case, "system", "sys-low", "B"))
    return rows, {
        "kind": "two_generator_floor",
        "n_items": 10,
        "n_generators": 2,
        "expected_verdict": "UNDECIDABLE_FLOOR_DEGENERATE",
    }


def no_reading_fixture() -> tuple[list[list[str]], dict[str, Any]]:
    rows: list[list[str]] = []
    for answer in ("X", "X", "Y", "Y", "Z"):
        rows.append(_row("z00", "z-case", "judge", f"generator-{len(rows) + 1}", answer))
    rows.append(_row("z00", "z-case", "system", "sys-top", "X"))
    rows.append(_row("z00", "z-case", "system", "sys-low", "Y"))
    return rows, {
        "kind": "unresolved_gold_no_reading",
        "n_items": 1,
        "votes": {"X": 2, "Y": 2, "Z": 1},
        "expected_verdict": "UNDECIDABLE_NO_READING",
    }


def fixture_cases() -> dict[str, dict[str, Any]]:
    below_rows, below_spec = balanced_tri_fixture(
        n_items=400,
        n_disagree=24,
        leader_correct=399,
    )
    equality_rows, equality_spec = balanced_tri_fixture(
        n_items=50,
        n_disagree=4,
        leader_correct=50,
    )
    above_rows, above_spec = balanced_tri_fixture(
        n_items=10,
        n_disagree=8,
        leader_correct=10,
    )
    ci_rows, ci_spec = ci_crossing_fixture()
    domain_rows, domain_spec = domain_mismatch_fixture()
    degenerate_rows, degenerate_spec = floor_degenerate_fixture()
    no_reading_rows, no_reading_spec = no_reading_fixture()
    return {
        "below_delta": {
            "rows": below_rows,
            "spec": {**below_spec, "expected_implementation_verdict": "MARGINAL"},
        },
        "equality_delta": {
            "rows": equality_rows,
            "spec": {
                **equality_spec,
                "expected_formula_verdict": "MARGINAL",
                "expected_implementation_verdict": "READABLE",
            },
        },
        "above_delta": {
            "rows": above_rows,
            "spec": {**above_spec, "expected_implementation_verdict": "READABLE"},
        },
        "ci_crossing_zero": {
            "rows": ci_rows,
            "spec": {
                **ci_spec,
                "expected_implementation_verdict": "READABLE",
                "expected_margin_ci_crosses_zero": True,
            },
        },
        "domain_mismatch_control": {
            "rows": domain_rows,
            "spec": domain_spec,
        },
        "floor_degenerate_control": {
            "rows": degenerate_rows,
            "spec": degenerate_spec,
        },
        "no_reading_control": {
            "rows": no_reading_rows,
            "spec": no_reading_spec,
        },
    }


def write_fixture(path: Path, rows: list[list[str]]) -> None:
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(HEADER)
        writer.writerows(rows)


def normalise_stdout(text: str, output_path: Path) -> str:
    return text.replace(f"[JSON] -> {output_path}", "[JSON] -> <OUTPUT>")


def run_fixture(
    *,
    python: str,
    audit_path: Path,
    name: str,
    rows: list[list[str]],
    spec: dict[str, Any],
    directory: Path,
) -> dict[str, Any]:
    fixture_path = directory / f"{name}.csv"
    output_path = directory / f"{name}.json"
    write_fixture(fixture_path, rows)
    command = [
        python,
        str(audit_path),
        str(fixture_path),
        "--n-boot",
        str(N_BOOT),
        "--json",
        str(output_path),
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"{name}: audit.py exited {completed.returncode}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    return {
        "fixture_sha256": sha256_file(fixture_path),
        "fixture_rows": len(rows),
        "spec": spec,
        "exit_code": completed.returncode,
        "stdout": normalise_stdout(completed.stdout, output_path),
        "stderr": completed.stderr,
        "result": {
            "verdict": payload.get("verdict"),
            "n_items": payload.get("n_items"),
            "ceiling_loo_macro": payload.get("ceiling_loo_macro"),
            "margin_vs_floor": payload.get("margin_vs_floor"),
            "margin_ci": payload.get("margin_ci"),
            "delta_threshold_points": payload.get("delta_threshold_points"),
            "same_domain_as_floor": payload.get("same_domain_as_floor"),
            "loo_measure": payload.get("loo_measure"),
        },
    }


def cli_contract(
    *,
    python: str,
    audit_path: Path,
    fixture_path: Path,
) -> dict[str, Any]:
    source_text = audit_path.read_text(encoding="utf-8")
    hardcoded_decision_branch = 'elif top["macro"] - ceiling < 2.0:' in source_text
    hardcoded_threshold_metadata = '"delta_threshold_points": 2.0,' in source_text
    help_run = subprocess.run(
        [python, str(audit_path), "--help"],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    rejected = subprocess.run(
        [
            python,
            str(audit_path),
            str(fixture_path),
            "--delta",
            "2.0",
            "--n-boot",
            "10",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    return {
        "help_exit_code": help_run.returncode,
        "help_has_delta_option": "--delta" in help_run.stdout,
        "help_has_tie_rule_option": "--tie-rule" in help_run.stdout,
        "hardcoded_decision_branch_present": hardcoded_decision_branch,
        "hardcoded_threshold_metadata_present": hardcoded_threshold_metadata,
        "delta_invocation_exit_code": rejected.returncode,
        "delta_invocation_rejected": (
            rejected.returncode == 2
            and "unrecognized arguments" in rejected.stderr
            and "--delta" in rejected.stderr
        ),
        "delta_invocation_stderr": rejected.stderr.strip(),
    }


def close_points(left: float, right: float, tolerance: float = POINT_TOL) -> bool:
    return abs(float(left) - float(right)) <= tolerance


def evaluate(cases: dict[str, dict[str, Any]], cli: dict[str, Any]) -> dict[str, Any]:
    below = cases["below_delta"]
    equality = cases["equality_delta"]
    above = cases["above_delta"]
    ci = cases["ci_crossing_zero"]
    domain = cases["domain_mismatch_control"]
    degenerate = cases["floor_degenerate_control"]
    no_reading = cases["no_reading_control"]

    equality_raw = equality["spec"]["expected_point_margin"]
    ci_result = ci["result"]
    ci_margin = ci_result["margin_ci"] or {}

    gates = {
        "F1_threshold_is_not_a_cli_parameter": {
            "passed": (
                cli["help_exit_code"] == 0
                and not cli["help_has_delta_option"]
                and cli["help_has_tie_rule_option"]
                and cli["hardcoded_decision_branch_present"]
                and cli["hardcoded_threshold_metadata_present"]
                and cli["delta_invocation_rejected"]
            ),
            "evidence": cli,
        },
        "F2_equality_branch_mismatch_reproduced": {
            "passed": (
                close_points(equality_raw, DELTA)
                and equality_raw > DELTA
                and equality["result"]["margin_vs_floor"] == DELTA
                and equality["result"]["verdict"] == "READABLE"
            ),
            "derived_raw_margin_points": equality_raw,
            "json_margin_points": equality["result"]["margin_vs_floor"],
            "implementation_verdict": equality["result"]["verdict"],
            "manuscript_equality_instruction": "MARGINAL",
        },
        "F3_graded_branch_controls": {
            "passed": (
                close_points(below["result"]["margin_vs_floor"], 1.25)
                and below["result"]["verdict"] == "MARGINAL"
                and close_points(above["result"]["margin_vs_floor"], 20.0)
                and above["result"]["verdict"] == "READABLE"
            ),
            "below_delta": {
                "margin_points": below["result"]["margin_vs_floor"],
                "verdict": below["result"]["verdict"],
            },
            "above_delta": {
                "margin_points": above["result"]["margin_vs_floor"],
                "verdict": above["result"]["verdict"],
            },
        },
        "F4_confidence_interval_is_not_gating": {
            "passed": (
                ci_result["verdict"] == "READABLE"
                and float(ci_result["margin_vs_floor"]) > DELTA
                and ci_margin.get("crosses_zero") is True
                and ci_margin.get("lo95") is not None
                and float(ci_margin["lo95"]) < 0.0
            ),
            "margin_points": ci_result["margin_vs_floor"],
            "margin_ci": ci_margin,
            "verdict": ci_result["verdict"],
        },
        "F5_fail_closed_controls": {
            "passed": (
                domain["result"]["verdict"] == "UNDECIDABLE_DOMAIN_MISMATCH"
                and domain["result"]["same_domain_as_floor"] is False
                and degenerate["result"]["verdict"]
                == "UNDECIDABLE_FLOOR_DEGENERATE"
                and no_reading["result"]["verdict"] == "UNDECIDABLE_NO_READING"
            ),
            "domain_mismatch": domain["result"]["verdict"],
            "floor_degenerate": degenerate["result"]["verdict"],
            "no_reading": no_reading["result"]["verdict"],
        },
    }
    return {
        "gates": gates,
        "status": "passed" if all(gate["passed"] for gate in gates.values()) else "failed",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--external-root", required=True)
    parser.add_argument("--preregistration", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--python", default=sys.executable)
    args = parser.parse_args()

    external_root = Path(args.external_root).expanduser().resolve()
    prereg_path = Path(args.preregistration).expanduser().resolve()
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if prereg.get("status") != "frozen_before_execution":
        raise SystemExit("preregistration is not frozen_before_execution")
    if prereg.get("implementation", {}).get("sha256") != sha256_file(__file__):
        raise SystemExit("runner hash does not match the preregistration")

    audit_path = external_root / AUDIT_RELATIVE
    audit_sha = sha256_file(audit_path)
    if audit_sha != PINNED_AUDIT_SHA256:
        raise SystemExit(
            f"native audit.py hash mismatch: {audit_sha} != {PINNED_AUDIT_SHA256}"
        )

    temporary = Path(tempfile.mkdtemp(prefix="qone-a4-"))
    try:
        cases: dict[str, dict[str, Any]] = {}
        for name, fixture in fixture_cases().items():
            cases[name] = run_fixture(
                python=args.python,
                audit_path=audit_path,
                name=name,
                rows=fixture["rows"],
                spec=fixture["spec"],
                directory=temporary,
            )
        equality_csv = temporary / "equality_delta.csv"
        validation = evaluate(
            cases,
            cli_contract(
                python=args.python,
                audit_path=audit_path,
                fixture_path=equality_csv,
            ),
        )
    finally:
        shutil.rmtree(temporary, ignore_errors=True)

    native_head = subprocess.check_output(
        ["git", "-C", str(external_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    output = {
        "schema": "q-one-a4-threshold-interface-v1",
        "experiment_id": "noise-floor-threshold-interface-a4",
        "preregistration": {
            "path": prereg_path.name,
            "sha256": sha256_file(prereg_path),
            "version": prereg.get("version"),
        },
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha256_file(__file__),
        },
        "native": {
            "external_root_name": external_root.name,
            "head": native_head,
            "audit_path": AUDIT_RELATIVE.as_posix(),
            "audit_sha256": audit_sha,
        },
        "bootstrap": {
            "n_boot": N_BOOT,
            "seed": 20261001,
            "cluster": "case",
        },
        "cases": cases,
        "gates": validation["gates"],
        "decision": {
            "status": validation["status"],
            "hypothesis": "H1_interface_semantics_mismatch"
            if validation["status"] == "passed"
            else "H0_not_reproduced",
            "narrow_conclusion": (
                "The pinned native CLI has no delta parameter and hard-codes "
                "2.0 points. A synthetic fixture with a derived point margin of "
                "exactly 2.0 is classified READABLE, while the manuscript's "
                "explicit equality instruction is MARGINAL. A separate fixture "
                "has point margin >2.0 and a case-bootstrap interval crossing "
                "zero and is still classified READABLE. Fail-closed domain, "
                "floor-degeneracy and no-reading fixtures remain refusals."
            ),
            "non_claims": [
                "These are deterministic synthetic interface fixtures, not external leaderboard measurements.",
                "The experiment identifies interface semantics; it does not measure ranking validity.",
                "The experiment does not establish that a different threshold would improve scientific validity.",
                "No manuscript, author, licence, account, or upload state is changed.",
            ],
        },
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"STATUS={output['decision']['status']}")
    print(f"OUTPUT={output_path}")
    print(f"SHA256={sha256_file(output_path)}")
    return 0 if output["decision"]["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
