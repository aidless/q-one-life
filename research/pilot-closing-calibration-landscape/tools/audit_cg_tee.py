#!/usr/bin/env python3
"""Recompute the Closing the Calibration Landscape evidence surface."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_locator(data: Any, expression: str) -> Any:
    current = data
    for part in expression.split("."):
        if "[" in part:
            match = re.fullmatch(r"([^\[]+)\[(\d+)\]", part)
            if not match:
                raise ValueError(f"unsupported locator segment: {part}")
            name, index = match.groups()
            current = current[name]
            current = current[int(index)]
        else:
            current = current[part]
    return current


def mean(values: list[float]) -> float:
    return float(statistics.mean(values))


def audit(root: Path, generated_at: str) -> dict[str, Any]:
    upstream = root / "evidence" / "upstream"
    checkpoint = load_json(upstream / "paper" / "evidence" / "cg_tee_checkpoint.json")
    aggregate = load_json(upstream / "evidence" / "cg_tee_results.json")
    final = load_json(upstream / "evidence" / "cg_tee_final_results.json")
    real = load_json(upstream / "paper" / "evidence" / "cg_tee_real_results.json")
    smoke = load_json(
        upstream / "paper" / "experiments" / "results" / "cg_tee_local_smoke.json"
    )
    receipts = load_json(upstream / "source" / "evidence" / "CARRIER_RECEIPTS.json")

    simulation: dict[str, Any] = {}
    for arm in ("standard", "cg_alone", "cg_tee"):
        gamma = [
            float(checkpoint["seeds"][str(seed)][arm]["gamma"]) for seed in range(15)
        ]
        entropy = [
            float(checkpoint["seeds"][str(seed)][arm]["H"]) for seed in range(15)
        ]
        recorded_mean = float(aggregate["aggregate"][arm]["gamma_mean"])
        recorded_cv = float(aggregate["aggregate"][arm]["cv"])
        candidates = {
            "sample_cv_gamma": float(statistics.stdev(gamma) / mean(gamma)),
            "population_cv_gamma": float(statistics.pstdev(gamma) / mean(gamma)),
            "sample_cv_entropy": float(statistics.stdev(entropy) / mean(entropy)),
            "sample_sd_gamma": float(statistics.stdev(gamma)),
        }
        nearest = min(candidates, key=lambda key: abs(candidates[key] - recorded_cv))
        simulation[arm] = {
            "n": len(gamma),
            "recomputed_mean": mean(gamma),
            "recorded_mean": recorded_mean,
            "mean_abs_difference": abs(mean(gamma) - recorded_mean),
            "recorded_cv": recorded_cv,
            "cv_candidates": candidates,
            "nearest_cv_candidate": nearest,
            "nearest_cv_gap": abs(candidates[nearest] - recorded_cv),
        }

    final_means = {
        arm: mean([float(row["gTV"]) for row in final[arm]])
        for arm in ("uncalibrated", "calibrated", "cg_tee")
    }
    final_reduction_pct = (
        (final_means["uncalibrated"] - final_means["calibrated"])
        / final_means["uncalibrated"]
        * 100
    )
    real_degenerate = {}
    for arm in ("standard", "cg_alone", "cg_tee"):
        rows = [real["results"][str(seed)][arm] for seed in range(15)]
        real_degenerate[arm] = {
            "n": len(rows),
            "gamma_tv_zero": sum(float(row["gamma_TV"]) == 0.0 for row in rows),
            "gamma_vt_zero": sum(float(row["gamma_VT"]) == 0.0 for row in rows),
            "entropy_t_one": sum(float(row["H_T"]) == 1.0 for row in rows),
            "entropy_v_one": sum(float(row["H_V"]) == 1.0 for row in rows),
        }
    standard_matches = all(
        float(real["results"][str(seed)]["standard"]["gamma_TV"])
        == float(final["uncalibrated"][seed]["gTV"])
        for seed in range(15)
    )

    carrier_results = []
    canonical = upstream / "paper" / "main.tex"
    canonical_lines = canonical.read_text(encoding="utf-8").splitlines()
    for receipt in receipts:
        artifact = upstream / str(receipt["artifact"])
        value = resolve_locator(load_json(artifact), str(receipt["locator"]))
        expected = float(receipt["value"])
        digits = int(receipt.get("dp", 3))
        tolerance = 0.5 * 10**-digits + 1e-12
        value_match = isinstance(value, (int, float)) and abs(float(value) - expected) <= tolerance
        line_match = False
        source_line = None
        if ":" in str(receipt.get("line", "")):
            source_name, line_number = str(receipt["line"]).rsplit(":", 1)
            if source_name == "paper/main.tex":
                index = int(line_number) - 1
                if 0 <= index < len(canonical_lines):
                    source_line = canonical_lines[index]
                    line_match = any(
                        abs(float(token) - expected) <= tolerance
                        for token in re.findall(r"[-+]?\d+(?:\.\d+)?", source_line)
                    )
        carrier_results.append(
            {
                "locator": receipt["locator"],
                "artifact": str(receipt["artifact"]),
                "artifact_sha256": sha256_file(artifact),
                "expected": expected,
                "resolved": value,
                "value_match": value_match,
                "line_match": line_match,
                "line_preview": source_line,
            }
        )

    model_named_files = []
    for path in sorted(upstream.rglob("*.json")):
        try:
            payload = load_json(path)
        except (OSError, ValueError):
            continue
        serialized = json.dumps(payload)
        if any(
            token in serialized
            for token in ("DeepSeek-V4-Pro", "GLM5.2", "deepseek-v4-pro", "glm-5.2")
        ):
            model_named_files.append(str(path.relative_to(upstream)))

    source = root / "source" / "main.tex"
    source_text = source.read_text(encoding="utf-8")
    bibitems = re.findall(r"\\bibitem(?:\[[^\]]*\])?\{([^}]+)\}", source_text)
    citation_keys: list[str] = []
    for match in re.finditer(
        r"\\cite(?:t|p|alp)?\*?(?:\[[^\]]*\])?\{([^}]+)\}", source_text
    ):
        citation_keys.extend(key.strip() for key in match.group(1).split(","))

    checks = {
        "simulation_gamma_means_recompute": all(
            item["mean_abs_difference"] <= 1e-12 for item in simulation.values()
        ),
        "simulation_cv_recompute": all(
            item["nearest_cv_gap"] <= 0.5e-3 for item in simulation.values()
        ),
        "real_confidence_arms_degenerate": all(
            real_degenerate[arm]["gamma_tv_zero"] == 15
            and real_degenerate[arm]["gamma_vt_zero"] == 15
            and real_degenerate[arm]["entropy_t_one"] == 15
            and real_degenerate[arm]["entropy_v_one"] == 15
            for arm in ("cg_alone", "cg_tee")
        ),
        "real_standard_matches_final": standard_matches,
        "carrier_receipts_pass": all(
            item["value_match"] and item["line_match"] for item in carrier_results
        ),
        "n15_model_identity_present": bool(model_named_files),
        "citations_resolve": not (set(citation_keys) - set(bibitems)),
        "source_has_no_content_after_end_document": bool(
            source_text.rstrip().endswith("\\end{document}")
        ),
        "design_sentence_not_duplicated": source_text.count(
            "Each seed nominally runs three conditions"
        )
        == 1,
        "local_smoke_parser_clean": float(
            smoke["parse_failures"]["confidence_parse_fail_rate"]
        )
        == 0.0
        and not any(smoke["degenerate_check"].values()),
    }
    return {
        "schema": "q-one-closing-landscape-audit-v1",
        "generated_at": generated_at,
        "marker": "agent-proposed, not human publication approval",
        "source": {
            "canonical_sha256": sha256_file(canonical),
            "overlay_sha256": sha256_file(source),
            "canonical_bytes": canonical.stat().st_size,
            "overlay_bytes": source.stat().st_size,
        },
        "simulation": simulation,
        "final_results": {
            "means": final_means,
            "uncalibrated_to_calibrated_reduction_pct": final_reduction_pct,
            "cg_tee_minus_calibrated": final_means["cg_tee"]
            - final_means["calibrated"],
        },
        "real_api": {
            "completed_seeds": len(real["completed_seeds"]),
            "arms": real_degenerate,
            "model_identity_present": bool(model_named_files),
        },
        "model_named_result_files": model_named_files,
        "local_smoke": {
            "n_seeds": smoke["config"]["n_seeds"],
            "rounds": smoke["config"]["rounds"],
            "parse_failures": smoke["parse_failures"],
            "degenerate_check": smoke["degenerate_check"],
        },
        "carrier_audit": {
            "receipts": len(carrier_results),
            "passed": sum(
                item["value_match"] and item["line_match"]
                for item in carrier_results
            ),
            "failed": sum(
                not (item["value_match"] and item["line_match"])
                for item in carrier_results
            ),
            "rows": carrier_results,
        },
        "citations": {
            "bibitems": len(bibitems),
            "unique_bibitems": len(set(bibitems)),
            "citation_keys": len(set(citation_keys)),
            "missing": sorted(set(citation_keys) - set(bibitems)),
            "uncited": sorted(set(bibitems) - set(citation_keys)),
        },
        "checks": checks,
        "gate_states": {
            "source_identity": "passed",
            "variant_reconciliation": "passed",
            "simulation_gamma": "passed"
            if checks["simulation_gamma_means_recompute"]
            else "failed",
            "simulation_cv": "blocked"
            if not checks["simulation_cv_recompute"]
            else "passed",
            "real_api": "blocked"
            if checks["real_confidence_arms_degenerate"]
            else "candidate",
            "model_identity": "blocked"
            if not checks["n15_model_identity_present"]
            else "passed",
            "carrier_transcription": "passed"
            if checks["carrier_receipts_pass"]
            else "failed",
            "citations": "passed"
            if checks["citations_resolve"]
            else "failed",
            "scientific_review": "blocked",
            "metadata_and_license": "blocked",
            "external_submission": "locked",
        },
        "scientific_ready": False,
        "external_submission": False,
        "notes": [
            "Gamma means are recomputable from the simulation checkpoint.",
            "CV values are not recomputable from any tested per-seed definition.",
            "The real-API confidence-gated arms are degenerate on all 15 seeds.",
            "The 39.249 percent scalar is an uncalibrated-versus-calibrated contrast, not a CG+TEE result.",
            "Carrier transcription is not scientific support.",
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
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"checks": payload["checks"], "gate_states": payload["gate_states"]}, indent=2))
    required = [
        payload["checks"]["simulation_gamma_means_recompute"],
        payload["checks"]["real_confidence_arms_degenerate"],
        payload["checks"]["real_standard_matches_final"],
        payload["checks"]["carrier_receipts_pass"],
        payload["checks"]["citations_resolve"],
        payload["checks"]["source_has_no_content_after_end_document"],
        payload["checks"]["design_sentence_not_duplicated"],
        payload["checks"]["local_smoke_parser_clean"],
    ]
    return 0 if all(required) else 1


if __name__ == "__main__":
    raise SystemExit(main())
